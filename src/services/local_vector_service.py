"""
Local vector service (SQLite + sqlite-vec, offline).

Same public surface as SupabaseService so DocumentProcessor and the deletion
CLI work unchanged regardless of VECTOR_BACKEND. Vectors are expected
L2-normalized (LocalEmbeddingService guarantees this); cosine similarity is
derived from sqlite-vec L2 distance as ``1 - d^2 / 2``.
"""

# Trace: Now sprint - classify_stage splitter, env centralization, wait helpers, threshold docs

import json
import logging
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, cast

import sqlite_vec

from config import get_config
from services.local_embedding_service import LocalEmbeddingService
from services.supabase_service import CardRow, ReceptionRow
from utils.audit_logger import AuditResource, get_audit_logger
from utils.error_handler import handle_supabase_error
from utils.monitoring_hooks import get_monitoring_hooks
from utils.performance_logger import log_execution_time, timer

logger = logging.getLogger(__name__)

RECEPTION_TABLE = "reception_mappings"
CARD_TABLE = "task_card_mappings"
RECEPTION_VEC_TABLE = "vec_receptions"
CARD_VEC_TABLE = "vec_cards"
META_TABLE = "vector_meta"
META_DIM_KEY = "embedding_dimension"

# SQL templates. Only module-level table constants are interpolated ({t});
# every value stays a bound parameter, never string-interpolated.
_SQL_RECEPTION_DDL = """CREATE TABLE IF NOT EXISTS {t} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT UNIQUE NOT NULL,
    handler TEXT NOT NULL,
    share_target TEXT NOT NULL,
    embedding BLOB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)"""
_SQL_CARD_DDL = """CREATE TABLE IF NOT EXISTS {t} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT UNIQUE NOT NULL,
    task_title TEXT NOT NULL,
    embedding BLOB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)"""
_SQL_VEC_DDL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS {t} USING vec0(embedding float[{dim}])"
)
_SQL_META_DDL = """CREATE TABLE IF NOT EXISTS vector_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)"""
_SQL_META_GET = "SELECT value FROM vector_meta WHERE key = ?"
_SQL_META_PUT = "INSERT INTO vector_meta(key, value) VALUES (?, ?)"
_SQL_KNN = (
    "SELECT rowid, distance FROM {t} "
    "WHERE embedding MATCH ? ORDER BY distance LIMIT ?"
)
_SQL_HANDLER_BY_TITLE = "SELECT handler, share_target FROM {t} WHERE title = ?"
_SQL_TASK_TITLE_BY_TITLE = "SELECT task_title FROM {t} WHERE title = ?"
_SQL_ID_BY_TITLE = "SELECT id FROM {t} WHERE title = ?"
_SQL_EXISTS_BY_TITLE = "SELECT 1 FROM {t} WHERE title = ? LIMIT 1"
_SQL_COUNT = "SELECT COUNT(*) FROM {t}"
_SQL_DELETE_VEC_BY_ID = "DELETE FROM {t} WHERE rowid = ?"
_SQL_DELETE_BY_ID = "DELETE FROM {t} WHERE id = ?"
_SQL_DELETE_ALL = "DELETE FROM {t}"
_SQL_LIST_CARDS = (
    "SELECT title, task_title, created_at FROM {t} ORDER BY id LIMIT ? OFFSET ?"
)
_SQL_LIST_RECEPTIONS = (
    "SELECT title, handler, share_target, created_at FROM {t} "
    "ORDER BY id LIMIT ? OFFSET ?"
)
_SQL_CANDIDATES_CARDS = "SELECT id, title, task_title FROM {t} WHERE id IN ({ids})"
_SQL_CANDIDATES_RECEPTIONS = (
    "SELECT id, title, handler, share_target FROM {t} WHERE id IN ({ids})"
)
_SQL_UPSERT_RECEPTION = """INSERT INTO {t}
    (title, handler, share_target, embedding, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(title) DO UPDATE SET
      handler=excluded.handler,
      share_target=excluded.share_target,
      embedding=excluded.embedding,
      updated_at=excluded.updated_at"""
_SQL_UPSERT_CARD = """INSERT INTO {t}
    (title, task_title, embedding, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(title) DO UPDATE SET
      task_title=excluded.task_title,
      embedding=excluded.embedding,
      updated_at=excluded.updated_at"""
_SQL_VEC_INSERT = "INSERT INTO {t}(rowid, embedding) VALUES (?, ?)"


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    """Clamp a float into [low, high] to absorb float rounding noise."""
    return max(low, min(high, value))


def _distance_to_similarity(distance: float) -> float:
    """Convert L2 distance between unit vectors to cosine similarity."""
    return _clamp(1.0 - (distance * distance) / 2.0)


class LocalVectorService:
    """SQLite-backed document store with sqlite-vec similarity search."""

    def __init__(
        self, embedding_service: LocalEmbeddingService, db_path: Optional[Path] = None
    ) -> None:
        """Open (or create) the local vector database.

        Args:
            embedding_service: Local embedding service instance (injected).
            db_path: SQLite file path (defaults to config data dir).

        Raises:
            ValueError: Stored vectors were built with another dimension.
        """
        self.config = get_config()
        self.db_path = (
            Path(db_path) if db_path else self.config.get_local_vector_db_path()
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.embedding_service = embedding_service
        self.similarity_threshold = self.config.get_local_vector_similarity_threshold()
        self._dimension = embedding_service.get_embedding_dimension()

        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.enable_load_extension(True)
        self._conn.load_extension(sqlite_vec.loadable_path())
        self._init_schema()
        self._check_dimension()

        logger.info("Local 벡터 DB 초기화 완료: %s", self.db_path)

    # ------------------------------------------------------------------ #
    # Schema
    # ------------------------------------------------------------------ #

    def _init_schema(self) -> None:
        """Create base tables, vec0 index tables and the meta table."""
        self._conn.execute(_SQL_RECEPTION_DDL.format(t=RECEPTION_TABLE))
        self._conn.execute(_SQL_CARD_DDL.format(t=CARD_TABLE))
        self._conn.execute(
            _SQL_VEC_DDL.format(t=RECEPTION_VEC_TABLE, dim=self._dimension)
        )
        self._conn.execute(_SQL_VEC_DDL.format(t=CARD_VEC_TABLE, dim=self._dimension))
        self._conn.execute(_SQL_META_DDL)
        self._conn.commit()

    def _check_dimension(self) -> None:
        """Pin the DB to one embedding dimension; refuse mixed spaces."""
        row = self._conn.execute(_SQL_META_GET, (META_DIM_KEY,)).fetchone()
        if row is None:
            self._conn.execute(_SQL_META_PUT, (META_DIM_KEY, str(self._dimension)))
            self._conn.commit()
            return
        if int(row[0]) != self._dimension:
            raise ValueError(
                f"Local vector DB dimension mismatch: stored={row[0]}, "
                f"model={self._dimension}. Delete {self.db_path} "
                "or reindex with a single model."
            )

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _normalize_query(self, query_embedding: List[float]) -> List[float]:
        """Validate dimension and L2-normalize the query vector."""
        if len(query_embedding) != self._dimension:
            raise ValueError(
                f"Query dimension {len(query_embedding)} "
                f"does not match DB dimension {self._dimension}"
            )
        return LocalEmbeddingService.normalize_vector(query_embedding)

    def _knn(
        self, vec_table: str, query_embedding: List[float], count: int
    ) -> List[Tuple[int, float]]:
        """Return [(rowid, cosine similarity)] ordered by similarity desc."""
        query = self._normalize_query(query_embedding)
        query_json = json.dumps(query, separators=(",", ":"))
        statement = _SQL_KNN.format(t=vec_table)
        with timer(logger, "Local sqlite-vec 검색"):
            rows = self._conn.execute(statement, (query_json, count)).fetchall()
        return [
            (int(rowid), _distance_to_similarity(float(distance)))
            for rowid, distance in rows
        ]

    @staticmethod
    def _to_blob(vector: List[float]) -> bytes:
        """Pack a vector as float32 bytes for the BLOB column."""
        return struct.pack(f"<{len(vector)}f", *vector)

    # ------------------------------------------------------------------ #
    # Reception lookups
    # ------------------------------------------------------------------ #

    @log_execution_time(logger)
    @handle_supabase_error("접수 문서 제목 조회", logger, default_return=(None, None))
    def retrieve_reception_by_title(
        self, title: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Look up a reception mapping by exact title."""
        statement = _SQL_HANDLER_BY_TITLE.format(t=RECEPTION_TABLE)
        row = self._conn.execute(statement, (title,)).fetchone()
        if row:
            return str(row[0]), str(row[1])
        return None, None

    def _process_reception_results(
        self, result_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Deduplicate (handler, share) combos keeping max similarity."""
        seen_combinations: Dict[str, Dict[str, Any]] = {}
        if result_data:
            for item in result_data:
                approval = item["handler"]
                share = item["share_target"] or "공람없음"
                similarity = item.get("similarity", 0)
                combo_key = f"{approval}|{share}"
                if (
                    combo_key not in seen_combinations
                    or seen_combinations[combo_key]["similarity"] < similarity
                ):
                    seen_combinations[combo_key] = {
                        "approval": approval,
                        "share": share,
                        "similarity": similarity,
                        "title": item["title"],
                    }
            return sorted(
                seen_combinations.values(),
                key=lambda x: x["similarity"],
                reverse=True,
            )
        return []

    def _fetch_reception_candidates(
        self, query_embedding: List[float], count: int
    ) -> List[Dict[str, Any]]:
        """Fetch top-count candidates above the similarity threshold."""
        hits = self._knn(RECEPTION_VEC_TABLE, query_embedding, count)
        if not hits:
            return []
        ids = [rowid for rowid, _ in hits]
        similarity_by_id = dict(hits)
        placeholders = ",".join("?" for _ in ids)
        statement = _SQL_CANDIDATES_RECEPTIONS.format(
            t=RECEPTION_TABLE, ids=placeholders
        )
        rows = self._conn.execute(statement, ids).fetchall()
        candidates = [
            {
                "title": title,
                "handler": handler,
                "share_target": share_target,
                "similarity": similarity_by_id[row_id],
            }
            for row_id, title, handler, share_target in rows
            if similarity_by_id[row_id] >= self.similarity_threshold
        ]
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates

    @log_execution_time(logger)
    def recommend_reception(self, title: str, count: int = 3) -> List[Dict[str, Any]]:
        """Recommend handlers by vector similarity (embeds the query)."""
        try:
            embedding_response = self.embedding_service.create_embedding(
                title, f"query_{title}"
            )
            if not embedding_response:
                logger.warning("임베딩 생성 실패: %s", title)
                return []
            return self._process_reception_results(
                self._fetch_reception_candidates(embedding_response.embedding, count)
            )
        except Exception as error:  # pylint: disable=broad-except
            logger.error("접수 문서 추천 실패: %s", error)
            return []

    @handle_supabase_error("담당자 추천 (임베딩 재사용)", logger, default_factory=list)
    def recommend_reception_with_embedding(
        self, query_embedding: List[float], count: int = 3
    ) -> List[Dict[str, Any]]:
        """Recommend handlers reusing a precomputed embedding."""
        with timer(logger, "Local sqlite-vec 검색 (접수 - 재사용)"):
            candidates = self._fetch_reception_candidates(query_embedding, count)
        return self._process_reception_results(candidates)

    # ------------------------------------------------------------------ #
    # Card lookups
    # ------------------------------------------------------------------ #

    def _process_card_results(
        self, result_data: List[Dict[str, Any]], count: int
    ) -> List[Dict[str, Any]]:
        """Deduplicate task titles keeping max similarity, truncated to count."""
        seen_cards: Dict[str, float] = {}
        if result_data:
            for item in result_data:
                task_title = item["task_title"]
                similarity = item.get("similarity", 0)
                if task_title not in seen_cards or seen_cards[task_title] < similarity:
                    seen_cards[task_title] = similarity
            return [
                {"task_title": card, "similarity": seen_cards[card]}
                for card in sorted(
                    seen_cards.keys(), key=lambda x: seen_cards[x], reverse=True
                )[:count]
            ]
        return []

    @log_execution_time(logger)
    @handle_supabase_error("업무카드 제목 조회", logger, default_return=None)
    def retrieve_card_by_title(self, title: str) -> Optional[str]:
        """Look up a task card mapping by exact title."""
        statement = _SQL_TASK_TITLE_BY_TITLE.format(t=CARD_TABLE)
        row = self._conn.execute(statement, (title,)).fetchone()
        if row:
            return str(row[0])
        return None

    def _fetch_card_candidates(
        self, query_embedding: List[float], count: int
    ) -> List[Dict[str, Any]]:
        """Fetch top-count card candidates above the similarity threshold."""
        hits = self._knn(CARD_VEC_TABLE, query_embedding, count)
        if not hits:
            return []
        ids = [rowid for rowid, _ in hits]
        similarity_by_id = dict(hits)
        placeholders = ",".join("?" for _ in ids)
        statement = _SQL_CANDIDATES_CARDS.format(t=CARD_TABLE, ids=placeholders)
        rows = self._conn.execute(statement, ids).fetchall()
        candidates = [
            {
                "title": title,
                "task_title": task_title,
                "similarity": similarity_by_id[row_id],
            }
            for row_id, title, task_title in rows
            if similarity_by_id[row_id] >= self.similarity_threshold
        ]
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates

    @log_execution_time(logger)
    def recommend_cards(self, title: str, count: int = 5) -> List[Dict[str, Any]]:
        """Recommend task cards by vector similarity (embeds the query)."""
        try:
            embedding_response = self.embedding_service.create_embedding(
                title, f"query_{title}"
            )
            if not embedding_response:
                logger.warning("임베딩 생성 실패: %s", title)
                return []
            with timer(logger, "Local sqlite-vec 검색 (카드)"):
                candidates = self._fetch_card_candidates(
                    embedding_response.embedding, count
                )
            result = self._process_card_results(candidates, count)
            logger.info("업무카드 추천 완료 (중복 제거 후): %d개", len(result))
            return result
        except Exception as error:  # pylint: disable=broad-except
            logger.error("업무카드 추천 실패: %s", error)
            return []

    @handle_supabase_error(
        "업무카드 추천 (임베딩 재사용)", logger, default_factory=list
    )
    def recommend_cards_with_embedding(
        self, query_embedding: List[float], count: int = 5
    ) -> List[Dict[str, Any]]:
        """Recommend task cards reusing a precomputed embedding."""
        with timer(logger, "Local sqlite-vec 검색 (카드 - 재사용)"):
            candidates = self._fetch_card_candidates(query_embedding, count)
        result = self._process_card_results(candidates, count)
        logger.info("업무카드 추천 완료 (재사용, 중복 제거 후): %d개", len(result))
        return result

    # ------------------------------------------------------------------ #
    # Upserts
    # ------------------------------------------------------------------ #

    def _resolve_embedding(
        self, title: str, prefix: str, embedding: Optional[List[float]]
    ) -> Tuple[Optional[List[float]], bool]:
        """Return (normalized vector, reused?) generating via service if needed."""
        if embedding is not None:
            return self._normalize_query(list(embedding)), True
        response = self.embedding_service.create_embedding(title, f"{prefix}_{title}")
        if response is None:
            return None, False
        return self._normalize_query(response.embedding), False

    def _replace_vector(self, vec_table: str, row_id: int, vector: List[float]) -> None:
        """Replace the vec0 index entry for a base row."""
        delete_statement = _SQL_DELETE_VEC_BY_ID.format(t=vec_table)
        insert_statement = _SQL_VEC_INSERT.format(t=vec_table)
        self._conn.execute(delete_statement, (row_id,))
        self._conn.execute(
            insert_statement, (row_id, json.dumps(vector, separators=(",", ":")))
        )

    def _row_id_by_title(self, base_table: str, title: str) -> int:
        """Return the base row id for a title (row must exist)."""
        statement = _SQL_ID_BY_TITLE.format(t=base_table)
        row = self._conn.execute(statement, (title,)).fetchone()
        return int(row[0])

    @log_execution_time(logger)
    def upsert_reception_embedding(
        self,
        title: str,
        handler: str,
        share_target: str,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """Upsert a reception mapping, generating the embedding if omitted."""
        audit = get_audit_logger()
        monitoring = get_monitoring_hooks()
        start_time = datetime.now()
        try:
            vector, embedding_reused = self._resolve_embedding(
                title, "reception", embedding
            )
            if vector is None:
                raise ValueError("임베딩을 생성할 수 없습니다")
            now = datetime.now(timezone.utc).isoformat()

            statement = _SQL_UPSERT_RECEPTION.format(t=RECEPTION_TABLE)
            self._conn.execute(
                statement,
                (title, handler, share_target, self._to_blob(vector), now, now),
            )
            row_id = self._row_id_by_title(RECEPTION_TABLE, title)
            self._replace_vector(RECEPTION_VEC_TABLE, row_id, vector)
            self._conn.commit()

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_suffix = " (재사용)" if embedding_reused else ""
            logger.info(
                "접수 문서 정규 매핑%s: %s -> %s/%s",
                log_suffix,
                title,
                handler,
                share_target,
            )
            audit.log_update(
                resource=AuditResource.RECEPTION_DOCUMENT,
                resource_id=title,
                status="success",
                details={
                    "handler": handler,
                    "share_target": share_target,
                    "has_embedding": True,
                    "embedding_reused": embedding_reused,
                },
                duration_ms=duration_ms,
            )
            monitoring.record_api_call(
                service="local-vector", success=True, response_time_ms=duration_ms
            )
            return True
        except Exception as error:  # pylint: disable=broad-except
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error("접수 문서 정규 매핑 실패: %s", error)
            audit.log_update(
                resource=AuditResource.RECEPTION_DOCUMENT,
                resource_id=title,
                status="failure",
                error_message=str(error),
                details={"handler": handler, "share_target": share_target},
                duration_ms=duration_ms,
            )
            monitoring.record_database_error(
                operation="upsert_reception_embedding",
                error_message=str(error),
                details={"title": title},
            )
            return False

    def upsert_reception_with_embedding(
        self,
        title: str,
        handler: str,
        share_target: str,
        embedding: Optional[List[float]] = None,
    ) -> bool:
        """Upsert a reception mapping (legacy alias)."""
        return cast(
            bool,
            self.upsert_reception_embedding(title, handler, share_target, embedding),
        )

    @log_execution_time(logger)
    def upsert_card_embedding(
        self, title: str, task_title: str, embedding: Optional[List[float]] = None
    ) -> bool:
        """Upsert a task card mapping, generating the embedding if omitted."""
        audit = get_audit_logger()
        monitoring = get_monitoring_hooks()
        start_time = datetime.now()
        embedding_reused = embedding is not None
        try:
            vector, embedding_reused = self._resolve_embedding(
                title, "task_card", embedding
            )
            if vector is None:
                raise ValueError("임베딩을 생성할 수 없습니다")
            now = datetime.now(timezone.utc).isoformat()

            statement = _SQL_UPSERT_CARD.format(t=CARD_TABLE)
            self._conn.execute(
                statement, (title, task_title, self._to_blob(vector), now, now)
            )
            row_id = self._row_id_by_title(CARD_TABLE, title)
            self._replace_vector(CARD_VEC_TABLE, row_id, vector)
            self._conn.commit()

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_suffix = " (재사용)" if embedding_reused else ""
            logger.info("업무카드 정규 매핑%s: %s -> %s", log_suffix, title, task_title)
            audit.log_update(
                resource=AuditResource.TASK_CARD,
                resource_id=title,
                status="success",
                details={
                    "task_title": task_title,
                    "has_embedding": True,
                    "embedding_reused": embedding_reused,
                },
                duration_ms=duration_ms,
            )
            monitoring.record_api_call(
                service="local-vector", success=True, response_time_ms=duration_ms
            )
            return True
        except Exception as error:  # pylint: disable=broad-except
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            log_suffix = " (재사용)" if embedding_reused else ""
            logger.error("업무카드 정규 매핑 실패%s: %s", log_suffix, error)
            audit.log_update(
                resource=AuditResource.TASK_CARD,
                resource_id=title,
                status="failure",
                error_message=str(error),
                details={"task_title": task_title},
                duration_ms=duration_ms,
            )
            monitoring.record_database_error(
                operation="upsert_card_embedding",
                error_message=str(error),
                details={"title": title},
            )
            return False

    def upsert_card_with_embedding(
        self, title: str, task_title: str, embedding: Optional[List[float]] = None
    ) -> bool:
        """Upsert a task card mapping (legacy alias)."""
        return cast(bool, self.upsert_card_embedding(title, task_title, embedding))

    # ------------------------------------------------------------------ #
    # Counts / status / wipe
    # ------------------------------------------------------------------ #

    @log_execution_time(logger)
    @handle_supabase_error("문서 개수 조회", logger, default_return=0)
    def get_document_count(self, table_type: str = "task_card") -> int:
        """Return the row count for a mapping table."""
        table_name = CARD_TABLE if table_type == "task_card" else RECEPTION_TABLE
        statement = _SQL_COUNT.format(t=table_name)
        row = self._conn.execute(statement).fetchone()
        return int(row[0]) if row else 0

    def get_connection_status(self) -> Dict[str, Any]:
        """Check local database readability."""
        try:
            statement = _SQL_COUNT.format(t=CARD_TABLE)
            self._conn.execute(statement).fetchone()
            return {
                "connected": True,
                "db_path": str(self.db_path),
                "tables": [CARD_TABLE, RECEPTION_TABLE],
            }
        except Exception as error:  # pylint: disable=broad-except
            return {"connected": False, "error": str(error)}

    def clear_all_data(self) -> bool:
        """Delete every row (dev/test only; blocked in production)."""
        audit = get_audit_logger()
        start_time = datetime.now()
        if self.config.get_environment() == "production":
            logger.error("프로덕션 환경에서는 데이터 삭제를 수행할 수 없습니다")
            audit.log_delete(
                resource=AuditResource.LOCAL_VECTOR,
                resource_id="all_data",
                status="failure",
                error_message="Production environment deletion blocked",
            )
            return False
        try:
            self._conn.execute(_SQL_DELETE_ALL.format(t=RECEPTION_VEC_TABLE))
            self._conn.execute(_SQL_DELETE_ALL.format(t=CARD_VEC_TABLE))
            self._conn.execute(_SQL_DELETE_ALL.format(t=RECEPTION_TABLE))
            self._conn.execute(_SQL_DELETE_ALL.format(t=CARD_TABLE))
            self._conn.commit()
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.warning("모든 데이터 삭제 완료")
            audit.log_delete(
                resource=AuditResource.LOCAL_VECTOR,
                resource_id="all_data",
                status="success",
                details={
                    "tables": [CARD_TABLE, RECEPTION_TABLE],
                    "environment": self.config.get_environment(),
                },
                duration_ms=duration_ms,
            )
            return True
        except Exception as error:  # pylint: disable=broad-except
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error("데이터 삭제 실패: %s", error)
            audit.log_delete(
                resource=AuditResource.LOCAL_VECTOR,
                resource_id="all_data",
                status="failure",
                error_message=str(error),
                duration_ms=duration_ms,
            )
            return False

    # ------------------------------------------------------------------ #
    # Listing / iteration (deletion CLI)
    # ------------------------------------------------------------------ #

    @handle_supabase_error("업무카드 목록 조회", logger, default_factory=list)
    def list_all_cards(self, limit: int = 1000, offset: int = 0) -> List[CardRow]:
        """List task card mappings ordered by id."""
        statement = _SQL_LIST_CARDS.format(t=CARD_TABLE)
        rows = self._conn.execute(statement, (limit, offset)).fetchall()
        return [
            CardRow(str(title), str(task_title), str(created_at))
            for title, task_title, created_at in rows
        ]

    @handle_supabase_error("접수 문서 목록 조회", logger, default_factory=list)
    def list_all_receptions(
        self, limit: int = 1000, offset: int = 0
    ) -> List[ReceptionRow]:
        """List reception mappings ordered by id."""
        statement = _SQL_LIST_RECEPTIONS.format(t=RECEPTION_TABLE)
        rows = self._conn.execute(statement, (limit, offset)).fetchall()
        return [
            ReceptionRow(str(title), str(handler), str(share), str(created_at))
            for title, handler, share, created_at in rows
        ]

    def _iter_table(
        self,
        fetch: Callable[[int, int], list],
        batch_size: int,
    ) -> Iterator:
        """Shared pagination loop; fetch(limit, offset) errors propagate."""
        offset = 0
        while True:
            batch = fetch(batch_size, offset)
            if not batch:
                break
            yield from batch
            offset += len(batch)
            if len(batch) < batch_size:
                break

    def iter_all_cards(self, batch_size: int = 500) -> Iterator[CardRow]:
        """Yield all task cards in batch_size pages."""

        def _fetch(limit: int, offset: int) -> List[CardRow]:
            statement = _SQL_LIST_CARDS.format(t=CARD_TABLE)
            rows = self._conn.execute(statement, (limit, offset)).fetchall()
            return [
                CardRow(str(title), str(task_title), str(created_at))
                for title, task_title, created_at in rows
            ]

        yield from self._iter_table(_fetch, batch_size)

    def iter_all_receptions(self, batch_size: int = 500) -> Iterator[ReceptionRow]:
        """Yield all receptions in batch_size pages."""

        def _fetch(limit: int, offset: int) -> List[ReceptionRow]:
            statement = _SQL_LIST_RECEPTIONS.format(t=RECEPTION_TABLE)
            rows = self._conn.execute(statement, (limit, offset)).fetchall()
            return [
                ReceptionRow(str(title), str(handler), str(share), str(created_at))
                for title, handler, share, created_at in rows
            ]

        yield from self._iter_table(_fetch, batch_size)

    # ------------------------------------------------------------------ #
    # Deletion helpers
    # ------------------------------------------------------------------ #

    def _delete_by_title(self, base_table: str, vec_table: str, title: str) -> bool:
        """Delete one row (base + vector index); True when a row existed."""
        select_statement = _SQL_ID_BY_TITLE.format(t=base_table)
        row = self._conn.execute(select_statement, (title,)).fetchone()
        if row is None:
            return False
        delete_vec_statement = _SQL_DELETE_VEC_BY_ID.format(t=vec_table)
        delete_base_statement = _SQL_DELETE_BY_ID.format(t=base_table)
        self._conn.execute(delete_vec_statement, (row[0],))
        self._conn.execute(delete_base_statement, (row[0],))
        self._conn.commit()
        return True

    def _bulk_delete(self, base_table: str, vec_table: str, titles: List[str]) -> int:
        """Delete rows by title list; returns deleted count."""
        deleted_count = 0
        for title in titles:
            if self._delete_by_title(base_table, vec_table, title):
                deleted_count += 1
        return deleted_count

    @handle_supabase_error("업무카드 일괄 삭제", logger, default_return=0)
    def bulk_delete_cards(self, titles: List[str]) -> int:
        """Bulk delete task cards by title."""
        deleted_count = self._bulk_delete(CARD_TABLE, CARD_VEC_TABLE, titles)
        logger.info("업무카드 일괄 삭제 완료: %d개", deleted_count)
        return deleted_count

    @handle_supabase_error("접수 문서 일괄 삭제", logger, default_return=0)
    def bulk_delete_receptions(self, titles: List[str]) -> int:
        """Bulk delete receptions by title."""
        deleted_count = self._bulk_delete(RECEPTION_TABLE, RECEPTION_VEC_TABLE, titles)
        logger.info("접수 문서 일괄 삭제 완료: %d개", deleted_count)
        return deleted_count

    @handle_supabase_error("업무카드 존재 확인", logger, default_return=False)
    def card_exists(self, title: str) -> bool:
        """Check whether a task card title exists."""
        statement = _SQL_EXISTS_BY_TITLE.format(t=CARD_TABLE)
        row = self._conn.execute(statement, (title,)).fetchone()
        return row is not None

    @handle_supabase_error("접수 문서 존재 확인", logger, default_return=False)
    def reception_exists(self, title: str) -> bool:
        """Check whether a reception title exists."""
        statement = _SQL_EXISTS_BY_TITLE.format(t=RECEPTION_TABLE)
        row = self._conn.execute(statement, (title,)).fetchone()
        return row is not None

    @handle_supabase_error("업무카드 삭제", logger, default_return=False)
    def delete_card_by_title(self, title: str) -> bool:
        """Delete a task card by title."""
        success = self._delete_by_title(CARD_TABLE, CARD_VEC_TABLE, title)
        if success:
            logger.info("업무카드 삭제 완료: %s", title)
        return success

    @handle_supabase_error("접수 문서 삭제", logger, default_return=False)
    def delete_reception_by_title(self, title: str) -> bool:
        """Delete a reception by title."""
        success = self._delete_by_title(RECEPTION_TABLE, RECEPTION_VEC_TABLE, title)
        if success:
            logger.info("접수 문서 삭제 완료: %s", title)
        return success

    def _delete_all(self, base_table: str, vec_table: str) -> int:
        """Delete every row in a mapping table; returns deleted count."""
        if not self.config.allow_destructive_operations():
            logger.error(
                "Destructive operations are not allowed in this environment. "
                "Set ALLOW_DESTRUCTIVE_OPERATIONS=true to enable."
            )
            return 0
        try:
            count = int(
                self.get_document_count(
                    "task_card" if base_table == CARD_TABLE else "reception"
                )
            )
            self._conn.execute(_SQL_DELETE_ALL.format(t=vec_table))
            self._conn.execute(_SQL_DELETE_ALL.format(t=base_table))
            self._conn.commit()
            logger.warning("모든 데이터 삭제 완료: %d개", count)
            return count
        except Exception as error:  # pylint: disable=broad-except
            logger.error("전체 삭제 실패: %s", error)
            return 0

    def delete_all_cards(self) -> int:
        """Delete every task card."""
        return self._delete_all(CARD_TABLE, CARD_VEC_TABLE)

    def delete_all_receptions(self) -> int:
        """Delete every reception."""
        return self._delete_all(RECEPTION_TABLE, RECEPTION_VEC_TABLE)
