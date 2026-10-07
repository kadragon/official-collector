"""
Local embedding service (FastEmbed, offline).

Drop-in alternative to OpenAIEmbeddingService for the local vector backend.
Vectors are L2-normalized on the way out so cosine-similarity math holds
for every downstream consumer (sqlite-vec distance conversion included).
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastembed import TextEmbedding

from config import get_config
from services.openai_embedding_service import EmbeddingRequest, EmbeddingResponse
from utils.audit_logger import AuditResource, get_audit_logger
from utils.embedding_cache import EmbeddingCache
from utils.monitoring_hooks import get_monitoring_hooks
from utils.performance_logger import log_execution_time

logger = logging.getLogger(__name__)


class LocalEmbeddingService:
    """FastEmbed-backed embedding service (no network, no API cost)."""

    # Model name -> output dimension. Only verified models are listed so a
    # typo fails fast instead of triggering a surprise model download.
    SUPPORTED_DIMENSIONS: Dict[str, int] = {
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
    }

    def __init__(
        self, model: Optional[str] = None, cache_dir: Optional[Path] = None
    ) -> None:
        """Initialize the local embedding service (model loads lazily)."""
        config = get_config()
        self.model_name = model or config.get_local_embedding_model()
        if self.model_name not in self.SUPPORTED_DIMENSIONS:
            raise ValueError(
                f"Unsupported local embedding model: {self.model_name} "
                f"(supported: {sorted(self.SUPPORTED_DIMENSIONS)})"
            )
        self._dimension = self.SUPPORTED_DIMENSIONS[self.model_name]
        self._cache_dir = (
            Path(cache_dir) if cache_dir else config.cache_dir / "fastembed"
        )
        self._model: Optional[TextEmbedding] = None
        self._cache = EmbeddingCache()
        logger.info("Local 임베딩 서비스 초기화 - 모델: %s", self.model_name)

    def get_embedding_dimension(self) -> int:
        """Return the output dimension of the configured model."""
        return self._dimension

    def _get_model(self) -> TextEmbedding:
        """Load the ONNX model on first use (downloads once into cache_dir)."""
        if self._model is None:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._model = TextEmbedding(
                model_name=self.model_name, cache_dir=str(self._cache_dir)
            )
            logger.info("FastEmbed 모델 로드 완료: %s", self.model_name)
        return self._model

    @staticmethod
    def normalize_vector(vector: List[float]) -> List[float]:
        """L2-normalize a vector; zero vectors pass through unchanged."""
        arr = np.asarray(vector, dtype=np.float64)
        norm = float(np.linalg.norm(arr))
        if norm == 0.0:
            return [float(v) for v in vector]
        return [float(v) for v in (arr / norm)]

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed texts and return normalized vectors in input order."""
        raw_vectors = list(self._get_model().embed(texts))
        return [self.normalize_vector([float(v) for v in vec]) for vec in raw_vectors]

    @log_execution_time(logger, "Local 임베딩 생성")
    def create_embedding(
        self,
        text: str,
        identifier: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[EmbeddingResponse]:
        """Create an embedding for a single text (offline)."""
        if not text or not text.strip():
            logger.warning("빈 텍스트에 대한 임베딩 요청")
            return None

        cached = self._cache.get(text)
        if cached is not None:
            logger.info("임베딩 캐시 적중: %s", identifier or text[:50])
            return EmbeddingResponse(
                identifier=identifier or f"embed_{int(time.time())}",
                embedding=cached,
                text=text,
                token_count=0,
                metadata=metadata or {},
            )

        monitoring = get_monitoring_hooks()
        audit = get_audit_logger()
        start_time = time.time()
        try:
            embedding = self._embed_texts([text.strip()])[0]
            response_time_ms = (time.time() - start_time) * 1000

            monitoring.record_api_call(
                service="local-embedding",
                success=True,
                response_time_ms=response_time_ms,
            )
            audit.log_api_call(
                resource=AuditResource.LOCAL_EMBEDDING,
                endpoint="local.embed",
                status="success",
                details={
                    "model": self.model_name,
                    "text_length": len(text),
                    "identifier": identifier,
                },
                duration_ms=response_time_ms,
            )

            result = EmbeddingResponse(
                identifier=identifier or f"embed_{int(time.time())}",
                embedding=embedding,
                text=text,
                token_count=0,
                metadata=metadata or {},
            )
            self._cache.put(text, embedding, identifier or text[:50])
            logger.debug("Local 임베딩 생성 완료: %s", identifier)
            return result
        except Exception as error:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error("Local 임베딩 생성 실패: %s", error)
            monitoring.record_api_call(
                service="local-embedding",
                success=False,
                response_time_ms=response_time_ms,
                error_message=str(error),
            )
            audit.log_api_call(
                resource=AuditResource.LOCAL_EMBEDDING,
                endpoint="local.embed",
                status="error",
                error_message=str(error),
                duration_ms=response_time_ms,
            )
            return None

    def create_embeddings_batch(
        self, requests: List[EmbeddingRequest], batch_size: int = 100
    ) -> List[EmbeddingResponse]:
        """Create embeddings in batches (single process, no rate limits)."""
        results: List[EmbeddingResponse] = []
        if not requests:
            return results

        total_batches = (len(requests) + batch_size - 1) // batch_size
        logger.info(
            "Local batch embedding start: %d requests across %d batches",
            len(requests),
            total_batches,
        )

        index = 0
        while index < len(requests):
            batch = requests[index : index + batch_size]
            valid_items = [
                (req, req.text.strip())
                for req in batch
                if req.text and req.text.strip()
            ]
            if not valid_items:
                logger.warning("Batch had no valid text inputs, skipping")
                index += len(batch)
                continue
            try:
                vectors = self._embed_texts([text for _, text in valid_items])
            except Exception as error:
                logger.error("Local 배치 임베딩 실패: %s", error)
                index += len(batch)
                continue
            for (req, _), vector in zip(valid_items, vectors):
                results.append(
                    EmbeddingResponse(
                        identifier=req.identifier,
                        embedding=vector,
                        text=req.text,
                        token_count=0,
                        metadata=req.metadata,
                    )
                )
                self._cache.put(req.text, vector, req.identifier)
            index += len(batch)
        return results
