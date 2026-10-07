"""
Unit tests for LocalEmbeddingService (FastEmbed, offline).

FastEmbed's TextEmbedding is stubbed so no model download occurs.
"""

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Add src to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.local_embedding_service import (  # pylint: disable=wrong-import-position  # noqa: E402
    LocalEmbeddingService,
)
from services.openai_embedding_service import (  # pylint: disable=wrong-import-position  # noqa: E402
    EmbeddingRequest,
)


class StubTextEmbedding:
    """Stub TextEmbedding returning fixed unnormalized vectors."""

    instances: List[Dict[str, Any]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        StubTextEmbedding.instances.append({"args": args, "kwargs": kwargs})

    def embed(self, texts: List[str]) -> Any:
        for _ in texts:
            yield [3.0, 4.0, 0.0, 0.0]


class FailingTextEmbedding:
    """Stub TextEmbedding that always fails."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def embed(self, texts: List[str]) -> Any:
        raise RuntimeError("model exploded")
        yield  # pragma: no cover - make this a generator


@pytest.fixture(name="stub_model")
def fixture_stub_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch TextEmbedding and register a 4-dim test model."""
    StubTextEmbedding.instances.clear()
    monkeypatch.setattr(
        "services.local_embedding_service.TextEmbedding", StubTextEmbedding
    )
    monkeypatch.setitem(LocalEmbeddingService.SUPPORTED_DIMENSIONS, "test-model", 4)


def test_create_embedding_returns_normalized_vector(
    stub_model: None, tmp_path: Path
) -> None:
    """Vectors are L2-normalized so cosine math holds downstream."""
    service = LocalEmbeddingService(
        model="test-model", cache_dir=tmp_path / "fastembed"
    )
    assert service.get_embedding_dimension() == 4

    response = service.create_embedding("hello", "doc-1")
    assert response is not None
    assert response.identifier == "doc-1"
    assert response.token_count == 0
    assert len(response.embedding) == 4
    assert math.isclose(sum(v * v for v in response.embedding), 1.0, rel_tol=1e-6)
    assert response.embedding[0] == pytest.approx(0.6)
    assert response.embedding[1] == pytest.approx(0.8)


def test_create_embedding_rejects_blank_text(stub_model: None, tmp_path: Path) -> None:
    """Blank input returns None without touching the model."""
    service = LocalEmbeddingService(
        model="test-model", cache_dir=tmp_path / "fastembed"
    )
    assert service.create_embedding("   ") is None
    assert StubTextEmbedding.instances == []


def test_create_embedding_caches_result(stub_model: None, tmp_path: Path) -> None:
    """Second call for the same text is served from cache."""
    service = LocalEmbeddingService(
        model="test-model", cache_dir=tmp_path / "fastembed"
    )
    first = service.create_embedding("cached text", "a")
    second = service.create_embedding("cached text", "b")
    assert first is not None and second is not None
    assert first.embedding == second.embedding


def test_create_embedding_returns_none_on_model_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Model errors are logged and surfaced as None, never raised."""
    monkeypatch.setattr(
        "services.local_embedding_service.TextEmbedding", FailingTextEmbedding
    )
    monkeypatch.setitem(LocalEmbeddingService.SUPPORTED_DIMENSIONS, "test-model", 4)
    service = LocalEmbeddingService(
        model="test-model", cache_dir=tmp_path / "fastembed"
    )
    assert service.create_embedding("hello", "doc-1") is None


def test_unknown_model_raises(tmp_path: Path) -> None:
    """Unknown models fail fast instead of triggering a surprise download."""
    with pytest.raises(ValueError, match="Unsupported local embedding model"):
        LocalEmbeddingService(model="no-such-model", cache_dir=tmp_path / "fastembed")


def test_create_embeddings_batch(stub_model: None, tmp_path: Path) -> None:
    """Batch path embeds valid texts and skips blanks."""
    service = LocalEmbeddingService(
        model="test-model", cache_dir=tmp_path / "fastembed"
    )
    requests = [
        EmbeddingRequest(text="first", identifier="1"),
        EmbeddingRequest(text="   ", identifier="blank"),
        EmbeddingRequest(text="second", identifier="2"),
    ]
    responses = service.create_embeddings_batch(requests, batch_size=2)
    assert [r.identifier for r in responses] == ["1", "2"]
    assert all(len(r.embedding) == 4 for r in responses)
