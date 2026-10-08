# Trace: backlog.md - Final handler task-card completion
"""Final task-card learning follows verified client selection and completion."""

from unittest.mock import Mock
from types import SimpleNamespace
import pytest
import main
from services.official_service import OfficialCollector
from services.task_card_handler import TaskCardHandler
from config import UIConfig
from ui.console_interface import SelectionResult
from services.document_processor import DocumentProcessor


def make_processor():
    store = Mock()
    store.retrieve_card_by_title.return_value = None
    store.embedding_service.create_embedding.return_value = None
    return DocumentProcessor(store, [], [], [])


def test_no_recommendation_uses_live_selection_and_queues_actual_card():
    processor = make_processor()
    capture = Mock(return_value="Actual unit card")
    assert (
        processor.process_task_card_matching("final", manual_selection=capture)
        == "Actual unit card"
    )
    capture.assert_called_once_with(None)
    assert processor.pending_card_updates[0]["card_name"] == "Actual unit card"


def test_exact_recommendation_can_be_corrected_in_client():
    processor = make_processor()
    processor.supabase_service.retrieve_card_by_title.return_value = "Old card"
    capture = Mock(return_value="Corrected card")
    assert (
        processor.process_task_card_matching("final", manual_selection=capture)
        == "Corrected card"
    )
    capture.assert_called_once_with("Old card")
    assert processor.pending_card_updates[0]["card_name"] == "Corrected card"


def test_cancelled_client_selection_never_learns():
    processor = make_processor()
    assert (
        processor.process_task_card_matching("final", manual_selection=lambda _: None)
        is None
    )
    assert processor.pending_card_updates == []


def test_failed_completion_discards_only_current_card():
    processor = make_processor()
    processor._queue_card_update("other", "Keep")
    processor._queue_card_update("final", "Discard")
    processor.discard_card_update("final")
    assert [r["title"] for r in processor.pending_card_updates] == ["other"]


def test_recommendation_is_presented_before_live_selection(monkeypatch):
    processor = make_processor()
    processor.supabase_service.embedding_service.create_embedding.return_value = (
        SimpleNamespace(embedding=[1.0])
    )
    processor.supabase_service.recommend_cards_with_embedding.return_value = [
        {"similarity": 0.99, "task_title": "Suggested"}
    ]
    monkeypatch.setattr(
        "services.document_processor.get_user_choice_from_recommendations",
        lambda title, options: (SelectionResult.SELECTED, options[0]),
    )
    capture = Mock(return_value="Actual")
    assert (
        processor.process_task_card_matching("final", manual_selection=capture)
        == "Actual"
    )
    capture.assert_called_once_with("Suggested")


@pytest.mark.parametrize("completed", [True, False])
def test_final_document_learning_requires_verified_completion(completed):
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.collector.get_official_title.return_value = "전자결재: 2026 final"
    app.collector.approve_reviewed_document.return_value = completed
    app.task_card_handler = Mock()
    app.task_card_handler.capture.return_value = "Actual"
    app.document_processor = make_processor()
    assert app._process_approval_document("2026 final") is completed
    app.collector.approve_reviewed_document.assert_called_once_with(
        "전자결재: 2026 final"
    )
    assert bool(app.document_processor.pending_card_updates) is completed
    app.collector.document_sort.assert_not_called()


def test_raw_title_preserves_year_for_document_identity():
    collector = OfficialCollector.__new__(OfficialCollector)
    collector.dlg = Mock()
    collector.dlg.texts.return_value = ["전자결재: [ 붙임 : 5 ]2026년 10주기"]
    assert collector.get_official_title() == "전자결재: [ 붙임 : 5 ]2026년 10주기"


@pytest.mark.parametrize(
    "chooser_open, field, saved",
    [
        (False, "Chosen", True),
        (True, "Chosen", True),
        (False, "", True),
        (False, "Chosen", False),
    ],
)
def test_client_capture_reads_field_and_verifies_save(
    monkeypatch, chooser_open, field, saved
):
    collector = Mock()
    collector.app.process = 123
    collector.dlg.window_text.return_value = "전자결재: final"
    collector._wait_for_condition.return_value = saved
    info = Mock()
    combo = Mock()
    combo.window_text.return_value = field
    confirm = Mock()
    select_button = Mock()
    info.child_window.side_effect = lambda **kw: {
        UIConfig.TASK_CARD_FIELD_ID: combo,
        UIConfig.TASK_CARD_SELECT_ID: select_button,
        1: confirm,
    }[kw["control_id"]]
    chooser = Mock()
    chooser.exists.side_effect = [False, chooser_open]
    desktop = Mock()
    desktop.window.side_effect = [chooser, info]
    monkeypatch.setattr(
        "services.task_card_handler.Desktop", Mock(return_value=desktop)
    )
    monkeypatch.setattr(
        "services.task_card_handler.get_timed_input", lambda *args, **kw: ""
    )
    result = TaskCardHandler().capture(collector, "Suggested")
    assert result == (field if not chooser_open and field and saved else None)
    assert confirm.click.call_count == (1 if not chooser_open and field else 0)
