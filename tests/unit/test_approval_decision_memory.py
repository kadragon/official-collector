# Trace: backlog.md - Approval decision memory / Reception fallback / Assigned reuse
"""Decision reuse uses local embeddings and learns only verified approval lines."""

from types import SimpleNamespace

import pytest

from services.document_processor import DocumentProcessor
from services.local_vector_service import LocalVectorService
from tests.unit.test_approval_line_store import StubEmbeddingService


@pytest.fixture
def processor(tmp_path):
    vectors = {
        "budget": [1.0, 0.0, 0.0, 0.0],
        "budget revised": [0.9, 0.1, 0.0, 0.0],
        "related": [0.7, 0.7, 0.0, 0.0],
    }
    store = LocalVectorService(StubEmbeddingService(vectors), tmp_path / "memory.db")
    result = DocumentProcessor(store, ["Kim"], ["공람없음"], [], approval_store=store)
    yield result
    store.close()


def test_exact_line_reuses_order_without_capture(processor):
    processor.approval_store.upsert_approval_line_embedding("budget", ["Lee", "Kim"])
    applied = []
    assert processor.process_assigned_document(
        "budget",
        lambda names: applied.append(names) or True,
        lambda: pytest.fail("unexpected manual capture"),
    )
    assert applied == [["Lee", "Kim"]]


def test_high_similarity_reuse_saves_verified_new_title(processor):
    processor.approval_store.upsert_approval_line_embedding("budget", ["Kim"])
    assert processor.process_assigned_document(
        "budget revised",
        lambda names: names == ["Kim"],
        lambda: pytest.fail("unexpected capture"),
    )
    assert processor.approval_store.retrieve_approval_line_by_title(
        "budget revised"
    ) == ["Kim"]


def test_failed_application_does_not_learn_new_title(processor):
    processor.approval_store.upsert_approval_line_embedding("budget", ["Kim"])
    assert not processor.process_assigned_document(
        "budget revised", lambda names: False, lambda: None
    )
    assert not processor.approval_store.approval_line_exists("budget revised")


def test_manual_capture_saved_and_timeout_not_saved(processor):
    assert processor.process_assigned_document(
        "budget",
        lambda names: pytest.fail("manual already applied"),
        lambda: ["Lee", "Kim"],
    )
    assert processor.approval_store.retrieve_approval_line_by_title("budget") == [
        "Lee",
        "Kim",
    ]
    assert not processor.process_assigned_document(
        "related", lambda names: False, lambda: None
    )
    assert not processor.approval_store.approval_line_exists("related")


def test_low_similarity_requires_selection(processor, monkeypatch):
    processor.approval_store.upsert_approval_line_embedding("budget", ["Kim"])
    prompts = []
    monkeypatch.setattr(
        "services.document_processor.choose_timed_option",
        lambda title, options, **kwargs: prompts.append(options) or options[0],
    )
    assert processor.process_assigned_document(
        "related",
        lambda names: names == ["Kim"],
        lambda: pytest.fail("unexpected capture"),
    )
    assert len(prompts) == 1


def test_supabase_embedding_is_never_used_for_local_lines(processor):
    def remote_embedding(*args):
        pytest.fail("cloud embedding must not enter local approval database")

    processor.supabase_service = SimpleNamespace(
        embedding_service=SimpleNamespace(create_embedding=remote_embedding)
    )
    assert processor.process_assigned_document(
        "budget", lambda names: True, lambda: ["Kim"]
    )
    assert processor.approval_store.approval_line_exists("budget")


def test_reception_embedding_failure_still_reaches_org_fallback(processor, monkeypatch):
    processor.reception_member_provider = lambda: ["Lee Staff"]
    picks = iter(["Lee Staff", "공람없음"])
    monkeypatch.setattr(
        "services.document_processor.choose_timed_option",
        lambda *args, **kwargs: next(picks),
    )
    assert processor.process_reception_document("missing embedding") == (
        "Lee",
        "공람없음",
    )


def test_empty_manual_line_never_saved(processor):
    assert not processor.process_assigned_document(
        "budget", lambda names: True, lambda: []
    )
    assert not processor.approval_store.approval_line_exists("budget")


def test_empty_approval_memory_goes_directly_to_registration(processor, monkeypatch):
    monkeypatch.setattr(
        "services.document_processor.choose_timed_option",
        lambda *args, **kwargs: pytest.fail("empty memory must not show a list menu"),
    )
    captured = []
    assert processor.process_assigned_document(
        "budget",
        lambda names: pytest.fail("no stored line to apply"),
        lambda: captured.append(True) or ["Me", "Superior"],
    )
    assert captured == [True]
    assert processor.approval_store.retrieve_approval_line_by_title("budget") == [
        "Me",
        "Superior",
    ]


def test_failed_reception_application_discards_pending_learning(processor, monkeypatch):
    picks = iter(["Kim", "공람없음"])
    monkeypatch.setattr(
        "services.document_processor.choose_timed_option",
        lambda *args, **kwargs: next(picks),
    )
    assert processor.process_reception_document("budget") == ("Kim", "공람없음")
    assert processor.get_pending_updates_count() == (1, 0)
    processor.discard_reception_update("budget")
    assert processor.get_pending_updates_count() == (0, 0)


def test_recommendation_timeout_never_opens_manual_capture(processor, monkeypatch):
    processor.approval_store.upsert_approval_line_embedding("budget", ["Kim"])
    monkeypatch.setattr(
        "services.document_processor.choose_timed_option", lambda *args, **kwargs: None
    )
    assert not processor.process_assigned_document(
        "related",
        lambda names: pytest.fail("unexpected application"),
        lambda: pytest.fail("unexpected capture"),
    )
    assert not processor.approval_store.approval_line_exists("related")


def test_whitespace_manual_selection_rejected_without_crash(processor, monkeypatch):
    processor.reception_member_provider = lambda: ["   "]
    monkeypatch.setattr(
        "services.document_processor.choose_timed_option",
        lambda *args, **kwargs: "   ",
    )
    assert processor.process_reception_document("blank pick") == (None, None)
