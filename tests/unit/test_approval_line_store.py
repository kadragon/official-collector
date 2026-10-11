# Trace: backlog.md Review Backlog - approval-decision-memory assigned reuse
"""Unit tests for the local-only approval_lines store (SQLite + sqlite-vec).

Mirrors the reception/card store contract: ordered approvers JSON, KNN
reuse, dedup/upsert, dimension pinning. Supabase approval-line methods stay
legacy no-ops (log + None/[]/False).
"""

import sys
import types
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# Add src to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.local_vector_service import (  # pylint: disable=wrong-import-position  # noqa: E402
    LocalVectorService,
)


class StubEmbeddingService:
    """Deterministic stub: text -> fixed vector mapping."""

    def __init__(self, mapping: Dict[str, List[float]], dim: int = 4) -> None:
        self.mapping = mapping
        self.dim = dim

    def get_embedding_dimension(self) -> int:
        return self.dim

    def create_embedding(
        self,
        text: str,
        identifier: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[types.SimpleNamespace]:
        vector = self.mapping.get(text)
        if vector is None:
            return None
        return types.SimpleNamespace(embedding=list(vector))


VECTORS: Dict[str, List[float]] = {
    "budget plan": [1.0, 0.0, 0.0, 0.0],
    "budget plan revised": [0.9, 0.1, 0.0, 0.0],
    "unrelated memo": [0.0, 1.0, 0.0, 0.0],
}


@pytest.fixture(name="service")
def fixture_service(tmp_path: Path) -> LocalVectorService:
    """Fresh file-backed service per test."""
    svc = LocalVectorService(
        StubEmbeddingService(VECTORS), db_path=tmp_path / "vectors.db"
    )
    yield svc
    svc.close()


def test_upsert_and_retrieve_preserves_order(
    service: LocalVectorService,
) -> None:
    """Exact title lookup returns approvers in stored order."""
    assert service.upsert_approval_line_embedding(
        "budget plan", ["Kim", "Lee", "Park"], VECTORS["budget plan"]
    )
    assert service.retrieve_approval_line_by_title("budget plan") == [
        "Kim",
        "Lee",
        "Park",
    ]
    assert service.retrieve_approval_line_by_title("missing") is None


def test_recommend_returns_line_with_similarity(
    service: LocalVectorService,
) -> None:
    """Identical vector ranks first with similarity ~1.0."""
    assert service.upsert_approval_line_embedding(
        "budget plan", ["Kim", "Lee"], VECTORS["budget plan"]
    )
    assert service.upsert_approval_line_embedding(
        "unrelated memo", ["Choi"], VECTORS["unrelated memo"]
    )
    recs = service.recommend_approval_lines_with_embedding(VECTORS["budget plan"])
    assert recs[0]["approvers"] == ["Kim", "Lee"]
    assert recs[0]["similarity"] == pytest.approx(1.0)
    assert all(r["approvers"] != ["Choi"] for r in recs)


def test_recommend_dedupes_identical_lines(
    service: LocalVectorService,
) -> None:
    """Two titles sharing one line collapse to a single recommendation."""
    assert service.upsert_approval_line_embedding(
        "budget plan", ["Kim", "Lee"], VECTORS["budget plan"]
    )
    assert service.upsert_approval_line_embedding(
        "budget plan revised", ["Kim", "Lee"], VECTORS["budget plan revised"]
    )
    recs = service.recommend_approval_lines_with_embedding(VECTORS["budget plan"])
    assert len(recs) == 1
    assert recs[0]["approvers"] == ["Kim", "Lee"]


def test_upsert_rejects_empty_approvers(service: LocalVectorService) -> None:
    """Empty or blank approver lists are refused, never stored."""
    assert service.upsert_approval_line_embedding("t1", []) is False
    assert service.upsert_approval_line_embedding("t1", ["", "  "]) is False
    assert service.retrieve_approval_line_by_title("t1") is None


def test_upsert_generates_embedding_when_missing(
    tmp_path: Path,
) -> None:
    """Upsert without a vector falls back to the embedding service."""
    svc = LocalVectorService(
        StubEmbeddingService(VECTORS), db_path=tmp_path / "vectors.db"
    )
    try:
        assert svc.upsert_approval_line_embedding("budget plan", ["Kim", "Lee"])
        assert svc.retrieve_approval_line_by_title("budget plan") == ["Kim", "Lee"]
    finally:
        svc.close()


def test_dimension_mismatch_raises(tmp_path: Path) -> None:
    """A DB file is pinned to one dimension; another model fails fast."""
    db_path = tmp_path / "vectors.db"
    first = LocalVectorService(StubEmbeddingService(VECTORS, dim=4), db_path=db_path)
    first.close()
    with pytest.raises(ValueError, match="dimension mismatch"):
        LocalVectorService(StubEmbeddingService(VECTORS, dim=8), db_path=db_path)


def test_exists_delete_list_iter_roundtrip(service: LocalVectorService) -> None:
    """Exists/delete/list/iter mirror the card-store contract."""
    assert service.upsert_approval_line_embedding(
        "budget plan", ["Kim"], VECTORS["budget plan"]
    )
    assert service.approval_line_exists("budget plan") is True
    assert service.approval_line_exists("missing") is False
    assert len(service.list_all_approval_lines()) == 1
    assert len(list(service.iter_all_approval_lines())) == 1
    assert service.delete_approval_line_by_title("budget plan") is True
    assert service.delete_approval_line_by_title("budget plan") is False
    assert service.approval_line_exists("budget plan") is False


def test_supabase_approval_line_methods_are_legacy_noops(monkeypatch) -> None:
    """Supabase backend has no approval_lines table: log + None/[]/False."""
    import services.supabase_service as supabase_module
    from services.supabase_service import SupabaseService

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "service-key")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")
    monkeypatch.setattr(supabase_module, "create_client", lambda url, key: object())

    service = SupabaseService(types.SimpleNamespace())
    assert service.retrieve_approval_line_by_title("anything") is None
    assert service.recommend_approval_lines_with_embedding([0.1, 0.2]) == []
    assert service.upsert_approval_line_embedding("t", ["Kim"]) is False


def test_overwrite_replaces_vector_and_survives_reopen(service):
    assert service.upsert_approval_line_embedding(
        "budget plan", ["Kim"], VECTORS["budget plan"]
    )
    assert service.upsert_approval_line_embedding(
        "budget plan", ["Lee"], VECTORS["unrelated memo"]
    )
    assert len(service.list_all_approval_lines()) == 1
    assert service.recommend_approval_lines_with_embedding(VECTORS["budget plan"]) == []
    reopened = LocalVectorService(
        StubEmbeddingService(VECTORS), db_path=service.db_path
    )
    try:
        assert reopened.retrieve_approval_line_by_title("budget plan") == ["Lee"]
    finally:
        reopened.close()


def test_bad_vector_does_not_overwrite_previous_line(service):
    assert service.upsert_approval_line_embedding(
        "budget plan", ["Kim"], VECTORS["budget plan"]
    )
    assert not service.upsert_approval_line_embedding("budget plan", ["Lee"], [1.0])
    assert service.retrieve_approval_line_by_title("budget plan") == ["Kim"]


def test_index_failure_rolls_back_base_row(service, monkeypatch):
    import sqlite3

    def fail_index(*args):
        raise sqlite3.OperationalError("index unavailable")

    monkeypatch.setattr(service, "_replace_vector", fail_index)
    assert not service.upsert_approval_line_embedding(
        "budget plan", ["Kim"], VECTORS["budget plan"]
    )
    assert not service.approval_line_exists("budget plan")


def test_pagination_and_order_sensitive_dedup(service):
    assert service.upsert_approval_line_embedding(
        "budget plan", ["Kim", "Lee"], VECTORS["budget plan"]
    )
    assert service.upsert_approval_line_embedding(
        "budget plan revised", ["Lee", "Kim"], VECTORS["budget plan revised"]
    )
    assert len(list(service.iter_all_approval_lines(batch_size=1))) == 2
    assert len(service.list_all_approval_lines(limit=1, offset=1)) == 1
    assert (
        len(service.recommend_approval_lines_with_embedding(VECTORS["budget plan"]))
        == 2
    )
    with pytest.raises(ValueError):
        list(service.iter_all_approval_lines(batch_size=0))


def test_clear_all_data_includes_approval_lines(service, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert service.upsert_approval_line_embedding(
        "budget plan", ["Kim"], VECTORS["budget plan"]
    )
    assert service.get_document_count("approval_line") == 1
    assert service.clear_all_data()
    assert service.list_all_approval_lines() == []
    assert service.recommend_approval_lines_with_embedding(VECTORS["budget plan"]) == []


def test_wrong_dimension_does_not_add_tables_to_existing_db(tmp_path):
    import sqlite3

    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE vector_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO vector_meta VALUES ('embedding_dimension', '8')"
        )
    with pytest.raises(ValueError, match="dimension mismatch"):
        LocalVectorService(StubEmbeddingService(VECTORS), db_path=db_path)
    with sqlite3.connect(db_path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    assert tables == [("vector_meta",)]
