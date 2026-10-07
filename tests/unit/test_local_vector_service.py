"""
Unit tests for LocalVectorService (SQLite + sqlite-vec, offline).

Uses a stub embedding service with 4-dim vectors; no model download.
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
    "apple notice": [1.0, 0.0, 0.0, 0.0],
    "apple notice revised": [0.9, 0.1, 0.0, 0.0],
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


def _seed_receptions(svc: LocalVectorService) -> None:
    assert svc.upsert_reception_embedding(
        "apple notice", "Kim", "Lee", VECTORS["apple notice"]
    )
    assert svc.upsert_reception_embedding(
        "apple notice revised", "Kim", "Lee", VECTORS["apple notice revised"]
    )
    assert svc.upsert_reception_embedding(
        "unrelated memo", "Park", "Choi", VECTORS["unrelated memo"]
    )


def test_retrieve_reception_by_title(service: LocalVectorService) -> None:
    """Exact title lookup returns handler/share pair."""
    _seed_receptions(service)
    assert service.retrieve_reception_by_title("apple notice") == ("Kim", "Lee")
    assert service.retrieve_reception_by_title("missing") == (None, None)


def test_recommend_reception_orders_and_filters(
    service: LocalVectorService,
) -> None:
    """Identical vector ranks first; below-threshold rows are filtered."""
    _seed_receptions(service)
    recs = service.recommend_reception_with_embedding(VECTORS["apple notice"])
    assert recs[0]["similarity"] == pytest.approx(1.0)
    # Same (handler, share) combo dedupes to a single recommendation.
    combos = {(r["approval"], r["share"]) for r in recs}
    assert ("Kim", "Lee") in combos
    assert all(r["similarity"] >= 0.0 for r in recs)
    # Orthogonal vector scores ~0 and must not pass the default 0.3 threshold.
    assert all(r["approval"] != "Park" for r in recs)


def test_recommend_cards_dedupes_and_truncates(
    service: LocalVectorService,
) -> None:
    """Card results dedupe by task_title and respect count."""
    for title in ("apple notice", "apple notice revised", "unrelated memo"):
        assert service.upsert_card_embedding(title, "Task-A", VECTORS[title])
    recs = service.recommend_cards_with_embedding(VECTORS["apple notice"], count=1)
    assert len(recs) == 1
    assert recs[0]["task_title"] == "Task-A"
    assert recs[0]["similarity"] == pytest.approx(1.0)


def test_upsert_generates_embedding_when_missing(
    tmp_path: Path,
) -> None:
    """Upsert without a vector falls back to the embedding service."""
    svc = LocalVectorService(
        StubEmbeddingService(VECTORS), db_path=tmp_path / "vectors.db"
    )
    try:
        assert svc.upsert_card_embedding("apple notice", "Task-A")
        assert svc.retrieve_card_by_title("apple notice") == "Task-A"
    finally:
        svc.close()


def test_exists_delete_bulk_and_counts(service: LocalVectorService) -> None:
    """CRUD helpers behave like the Supabase counterparts."""
    _seed_receptions(service)
    assert service.reception_exists("apple notice") is True
    assert service.reception_exists("missing") is False
    assert service.get_document_count("reception") == 3

    assert service.bulk_delete_receptions(["unrelated memo"]) == 1
    assert service.get_document_count("reception") == 2

    assert service.delete_reception_by_title("apple notice") is True
    assert service.retrieve_reception_by_title("apple notice") == (None, None)

    rows = service.list_all_receptions()
    assert len(rows) == 1
    assert list(service.iter_all_receptions()) == rows


def test_cards_list_iter_and_delete_all(service: LocalVectorService) -> None:
    """Card listing, iteration and destructive delete work."""
    assert service.upsert_card_embedding(
        "apple notice", "Task-A", VECTORS["apple notice"]
    )
    assert service.card_exists("apple notice") is True
    assert service.get_document_count("task_card") == 1
    assert len(service.list_all_cards()) == 1
    assert len(list(service.iter_all_cards())) == 1
    assert service.delete_all_cards() == 1
    assert service.get_document_count("task_card") == 0


def test_connection_status_and_clear(service: LocalVectorService) -> None:
    """Status reports connectivity; clear wipes both tables."""
    _seed_receptions(service)
    status = service.get_connection_status()
    assert status["connected"] is True
    assert service.clear_all_data() is True
    assert service.get_document_count("reception") == 0
    assert service.get_document_count("task_card") == 0


def test_dimension_mismatch_raises(tmp_path: Path) -> None:
    """A DB built with another model dimension refuses to open."""
    db_path = tmp_path / "vectors.db"
    svc = LocalVectorService(StubEmbeddingService(VECTORS, dim=4), db_path=db_path)
    svc.close()
    with pytest.raises(ValueError, match="dimension"):
        LocalVectorService(StubEmbeddingService(VECTORS, dim=8), db_path=db_path)
