# Trace: Split remaining oversized RPA modules on next touch
"""Characterize dialog readers at the existing public handler boundary."""

from unittest.mock import Mock

import pytest

from dialogs.dialog_classifier import DialogClassifier
from services.dialog_handler import DialogHandler, DocumentFlowState


def make_handler():
    window = Mock()
    window.exists.return_value = True
    dlg = Mock()
    dlg.child_window.return_value = window
    return DialogHandler(dlg, DialogClassifier()), window


def test_dialog_reader_is_usable_without_a_workflow_classifier():
    from services.confirm_dialog_reader import ConfirmDialogReader

    dlg = Mock()
    window = dlg.child_window.return_value
    window.exists.return_value = True
    window.texts.return_value = ["확인", "body"]
    window.children.return_value = []
    reader = ConfirmDialogReader(dlg)
    assert reader.find_confirm_dialog() is window
    assert reader.get_confirm_dialog_text() == "확인 body"


def test_discovery_returns_the_main_window_confirmation_without_desktop_lookup():
    handler, window = make_handler()
    assert handler.find_confirm_dialog() is window
    handler.dlg.child_window.assert_called_once_with(
        title="확인", control_type="Window"
    )


def test_confirm_text_keeps_wrapper_text_and_unique_text_and_edit_bodies():
    handler, window = make_handler()
    window.texts.return_value = ["확인", "body"]
    window.children.side_effect = [
        [
            Mock(window_text=Mock(return_value="body")),
            Mock(window_text=Mock(return_value="text field")),
        ],
        [Mock(window_text=Mock(return_value="edit field"))],
    ]
    assert handler.get_confirm_dialog_text() == "확인 body text field edit field"


def test_detailed_text_skips_caption_blanks_duplicates_and_failed_children():
    handler, window = make_handler()
    values = ["확인", " ", "result", "result", RuntimeError("stale")]
    window.children.return_value = [
        (
            Mock(window_text=Mock(side_effect=value))
            if isinstance(value, Exception)
            else Mock(window_text=Mock(return_value=value))
        )
        for value in values
    ]
    assert handler.get_detailed_dialog_text() == "result"


def test_detailed_debug_capture_restores_stdout_on_failure():
    import sys

    handler, window = make_handler()
    window.children.return_value = []
    window.print_control_identifiers.side_effect = RuntimeError("stale")
    original_stdout = sys.stdout
    assert handler.get_detailed_dialog_text() == ""
    assert sys.stdout is original_stdout


def test_quick_text_preserves_caption_first_short_circuit():
    handler, window = make_handler()
    window.window_text.return_value = " 確認 "
    assert handler.get_quick_dialog_text(window) == "確認"
    window.children.assert_not_called()


def test_quick_text_reads_only_first_three_static_controls_when_caption_empty():
    handler, window = make_handler()
    window.window_text.return_value = ""
    controls = [Mock(window_text=Mock(return_value="tiny")) for _ in range(4)]
    controls[2].window_text.return_value = "known body"
    window.children.return_value = controls
    assert handler.get_quick_dialog_text(window) == "known body"
    controls[3].window_text.assert_not_called()


def test_analysis_keeps_static_body_and_caption_order():
    handler, window = make_handler()
    window.window_text.return_value = "확인"
    window.children.return_value = [Mock(window_text=Mock(return_value="body"))]
    assert handler.analyze_dialog_content(window) == "body | 확인"


@pytest.mark.parametrize(
    "reader", ["get_confirm_dialog_text", "get_detailed_dialog_text"]
)
def test_readers_return_empty_when_confirmation_absent(reader):
    handler, window = make_handler()
    window.exists.return_value = False
    assert getattr(handler, reader)() == ""
    window.children.assert_not_called()


def test_flow_falls_back_to_detailed_body_and_preserves_unknown_state():
    handler, window = make_handler()
    window.texts.return_value = ["확인"]
    window.children.return_value = []
    assert handler.check_document_flow_state() == DocumentFlowState.UNKNOWN
    window.children.return_value = [
        Mock(window_text=Mock(return_value="종료하시겠습니까?"))
    ]
    assert handler.check_document_flow_state() == DocumentFlowState.EXIT
