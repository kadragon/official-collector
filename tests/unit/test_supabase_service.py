"""
Unit tests for SupabaseService behaviours tied to new mapping tables.
"""

import sys
import types
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import services.supabase_service as supabase_module  # pylint: disable=wrong-import-position
from services.supabase_service import (
    SupabaseService,
)  # pylint: disable=wrong-import-position


class FakeEmbeddingService:
    """Provides deterministic embeddings for testing."""

    def create_embedding(self, text, identifier):  # pylint: disable=unused-argument
        return types.SimpleNamespace(embedding=[0.1, 0.2, 0.3])


class FakeTable:
    """Captures interactions for assertions."""

    def __init__(self):
        self.select_called = False
        self.update_called = False
        self.insert_called = False
        self.upsert_calls = []

    def select(self, *_args, **_kwargs):
        self.select_called = True
        return self

    def update(self, _data):
        self.update_called = True
        return self

    def insert(self, _data):
        self.insert_called = True
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def upsert(self, data, on_conflict):
        self.upsert_calls.append({"data": data, "on_conflict": on_conflict})
        return self

    def execute(self):
        return types.SimpleNamespace(data=[])


class FakeClient:
    """Supabase client stub."""

    def __init__(self):
        self.tables = {}

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = FakeTable()
        return self.tables[name]


@pytest.fixture(name="supabase_service")
def fixture_supabase_service(monkeypatch):
    """Create a SupabaseService instance with fakes."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "service-key")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")

    fake_client = FakeClient()
    fake_embedding_service = FakeEmbeddingService()

    monkeypatch.setattr(supabase_module, "create_client", lambda url, key: fake_client)

    # 의존성 주입: embedding_service를 생성자에 전달
    service = SupabaseService(fake_embedding_service)
    service.client = fake_client
    return service


class SequencedFakeTable:
    """Returns pre-set page responses in order, then empty pages."""

    def __init__(self, pages):
        self._pages = list(pages)
        self._idx = 0

    def select(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self._idx < len(self._pages):
            data = self._pages[self._idx]
            self._idx += 1
        else:
            data = []
        return types.SimpleNamespace(data=data)


def test_iter_all_cards_multi_page(supabase_service, monkeypatch):
    """iter_all_cards yields all records across multiple pages."""
    pages = [
        [
            {"title": "t1", "task_title": "task1", "created_at": "d1"},
            {"title": "t2", "task_title": "task2", "created_at": "d2"},
        ],
        [{"title": "t3", "task_title": "task3", "created_at": "d3"}],
    ]
    fake_table = SequencedFakeTable(pages)
    monkeypatch.setattr(supabase_service.client, "table", lambda _name: fake_table)

    result = list(supabase_service.iter_all_cards(batch_size=2))

    assert result == [
        ("t1", "task1", "d1"),
        ("t2", "task2", "d2"),
        ("t3", "task3", "d3"),
    ]


def test_iter_all_cards_exact_multiple_of_batch(supabase_service, monkeypatch):
    """iter_all_cards terminates cleanly when count is exact multiple of batch_size."""
    full_batch = [{"title": "t", "task_title": "t", "created_at": "d"}] * 2
    fake_table = SequencedFakeTable([full_batch, full_batch, []])
    monkeypatch.setattr(supabase_service.client, "table", lambda _name: fake_table)

    result = list(supabase_service.iter_all_cards(batch_size=2))

    assert len(result) == 4


def test_iter_all_cards_error_propagates(supabase_service, monkeypatch):
    """iter_all_cards must propagate exceptions instead of silently truncating."""

    class ErrorFakeTable:
        def select(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def range(self, *_args, **_kwargs):
            return self

        def execute(self):
            raise RuntimeError("connection timeout")

    monkeypatch.setattr(supabase_service.client, "table", lambda _name: ErrorFakeTable())

    with pytest.raises(RuntimeError, match="connection timeout"):
        list(supabase_service.iter_all_cards())


def test_iter_all_receptions_multi_page(supabase_service, monkeypatch):
    """iter_all_receptions yields all records across multiple pages."""
    pages = [
        [
            {"title": "r1", "handler": "h1", "share_target": "s1", "created_at": "d1"},
            {"title": "r2", "handler": "h2", "share_target": "s2", "created_at": "d2"},
        ],
        [{"title": "r3", "handler": "h3", "share_target": "s3", "created_at": "d3"}],
    ]
    fake_table = SequencedFakeTable(pages)
    monkeypatch.setattr(supabase_service.client, "table", lambda _name: fake_table)

    result = list(supabase_service.iter_all_receptions(batch_size=2))

    assert result == [
        ("r1", "h1", "s1", "d1"),
        ("r2", "h2", "s2", "d2"),
        ("r3", "h3", "s3", "d3"),
    ]


def test_upsert_card_embedding_uses_single_upsert(supabase_service):
    """Verify card embeddings rely on a single upsert call."""
    supabase_service.upsert_card_embedding("업무 지시", "카드 제목")

    table = supabase_service.client.table("task_card_mappings")
    assert table.upsert_calls, "Upsert should be called at least once"
    assert table.upsert_calls[0]["on_conflict"] == "title"
    assert not table.select_called
    assert not table.update_called
    assert not table.insert_called
