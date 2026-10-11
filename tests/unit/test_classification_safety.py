# Trace: backlog.md - Classification safety and learning retries
"""Regressions for document identity, reception evidence and failed learning."""

from unittest.mock import MagicMock, Mock

import pytest
import main
from dialogs.dialog_classifier import DialogAction
from services.dialog_handler import DialogHandler
from services.document_processor import DocumentProcessor
from services.official_service import OfficialCollector


def test_final_consent_cannot_approve_a_changed_document(monkeypatch):
    app = main.Main.__new__(main.Main)
    app.auto_continue = True
    app.collector = Mock()
    app.document_processor = Mock()
    app.document_processor.get_pending_updates_count.return_value = (0, 0)
    app.collector.check_document_flow_state.return_value = (
        main.DocumentFlowState.CONTINUE
    )
    app.collector.get_official_title.side_effect = ["old", "NEW"]
    app._classify_document = Mock(return_value=3)
    app._process_approval_document = Mock(return_value=False)
    monkeypatch.setattr(main, "clear_screen", lambda: None)
    app.run()
    app._process_approval_document.assert_not_called()


@pytest.mark.parametrize("changed_during_match", [False, True])
def test_final_matching_keeps_original_document_identity(changed_during_match):
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.collector.get_official_title.side_effect = (
        ["old", "NEW"] if changed_during_match else ["NEW"]
    )
    app.task_card_handler = Mock()
    app.document_processor = Mock()
    app.document_processor.process_task_card_matching.side_effect = (
        lambda title, manual_selection: manual_selection("Suggested")
    )
    assert not app._process_approval_document("old", "old")
    app.task_card_handler.capture.assert_not_called()
    app.collector.approve_reviewed_document.assert_not_called()


@pytest.mark.parametrize("waits", [[False], [True, False]])
def test_reception_without_success_evidence_discards_learning(waits):
    collector = OfficialCollector.__new__(OfficialCollector)
    collector.dlg = MagicMock()
    collector.dialog_handler = DialogHandler(collector.dlg, Mock())
    collector._wait_for_condition = Mock(side_effect=waits)
    collector.button_controller = Mock()
    collector.apply_approval_names = Mock(return_value=True)
    app = main.Main.__new__(main.Main)
    app.collector = collector
    app.document_processor = Mock()
    app.document_processor.process_reception_document.return_value = ("Kim", None)
    assert not app._handle_reception_document("budget")
    app.document_processor.discard_reception_update.assert_called_once_with("budget")


@pytest.mark.parametrize("action", [DialogAction.UNKNOWN, DialogAction.APPROVE])
def test_unknown_reception_result_is_never_confirmed(action):
    handler = DialogHandler(Mock(), Mock())
    handler.get_confirm_dialog_text = Mock(return_value="unverified")
    handler.dialog_classifier.classify_dialog_action.return_value = action
    assert handler.handle_reception_result(Mock(return_value=True)) is False
    handler.dlg.child_window.return_value.child_window.return_value.click.assert_not_called()


@pytest.mark.parametrize("action", [DialogAction.CONTINUE, DialogAction.EXIT])
def test_reception_success_leaves_known_prompt_for_main_loop(action):
    collector = OfficialCollector.__new__(OfficialCollector)
    collector.dlg = MagicMock()
    collector.dialog_handler = DialogHandler(collector.dlg, Mock())
    collector.dialog_handler.get_confirm_dialog_text = Mock(return_value="known")
    collector.dialog_handler.dialog_classifier.classify_dialog_action.return_value = (
        action
    )
    collector._wait_for_condition = Mock(return_value=True)
    assert collector.reception(None) is True
    # Reception confirmation is clicked once; next/exit stays for load verification.
    assert (
        collector.dlg.child_window.return_value.child_window.return_value.click.call_count
        == 1
    )


def test_missing_circulation_acknowledgment_stops_before_result():
    collector = OfficialCollector.__new__(OfficialCollector)
    collector.dlg = MagicMock()
    collector.dialog_handler = Mock()
    collector.dialog_handler.handle_reception_confirmation.return_value = True
    collector.dialog_handler.handle_circulation_completion.return_value = False
    collector._wait_for_condition = Mock()
    assert collector.reception("Shared") is False
    collector.dialog_handler.handle_reception_result.assert_not_called()


@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize("failure", [False, RuntimeError("offline")])
def test_failed_learning_retains_latest_mapping_for_retry(embedded, failure):
    store = Mock()
    processor = DocumentProcessor(store, [], [], [])
    embedding = [1.0] if embedded else None
    processor._queue_reception_update("retry", "Old", "none", embedding)
    processor._queue_reception_update("retry", "Latest", "none", embedding)
    processor._queue_card_update("retry", "Latest", embedding)
    processor._queue_card_update("saved", "Saved", embedding)
    reception = getattr(
        store,
        "upsert_reception_with_embedding" if embedded else "upsert_reception_embedding",
    )
    card = getattr(
        store, "upsert_card_with_embedding" if embedded else "upsert_card_embedding"
    )
    reception.side_effect = [failure, True]
    card.side_effect = [failure, True, True]
    processor.flush_pending_updates()
    assert processor.get_pending_updates_count() == (1, 1)
    assert processor.pending_reception_updates[0]["approval"] == "Latest"
    assert processor.pending_card_updates[0]["title"] == "retry"
    processor.flush_pending_updates()
    assert processor.get_pending_updates_count() == (0, 0)


@pytest.mark.parametrize("remaining", [(0, 0), (1, 0), (0, 1)])
def test_flush_reports_success_only_when_no_failed_mappings_remain(
    monkeypatch, remaining
):
    app = main.Main.__new__(main.Main)
    app.document_processor = Mock()
    app.document_processor.get_pending_updates_count.side_effect = [(1, 1), remaining]
    success = Mock()
    warning = Mock()
    monkeypatch.setattr(main, "print_success", success)
    monkeypatch.setattr(main, "print_warning", warning)
    app._flush_all_pending_updates()
    app.document_processor.flush_pending_updates.assert_called_once_with()
    assert success.call_count == (0 if any(remaining) else 1)
    assert warning.call_count == (1 if any(remaining) else 0)
