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
    monkeypatch.setattr(supabase_module, "create_client", lambda url, key: fake_client)
    monkeypatch.setattr(
        supabase_module, "OpenAIEmbeddingService", lambda: FakeEmbeddingService()
    )

    service = SupabaseService()
    service.client = fake_client
    service.embedding_service = FakeEmbeddingService()
    return service


def test_upsert_card_embedding_uses_single_upsert(supabase_service):
    """Verify card embeddings rely on a single upsert call."""
    supabase_service.upsert_card_embedding("업무 지시", "카드 제목")

    table = supabase_service.client.table("task_card_mappings")
    assert table.upsert_calls, "Upsert should be called at least once"
    assert table.upsert_calls[0]["on_conflict"] == "title"
    assert not table.select_called
    assert not table.update_called
    assert not table.insert_called
