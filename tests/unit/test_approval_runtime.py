# Trace: backlog.md - Approval decision memory / Assigned reuse
"""RPA boundaries use disposable dialog doubles; no live document mutations."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from config import TimeoutConfig
from config import UIConfig
from services.button_controller import ButtonController
from services.official_service import OfficialCollector
from services.dialog_handler import DocumentFlowState
from services.dialog_handler import DialogHandler
from services.approval_line_handler import ApprovalLineHandler
from services.window_manager import WindowManager
from dialogs.dialog_classifier import DialogClassifier


def make_collector():
    collector = OfficialCollector.__new__(OfficialCollector)
    collector.approval_line_handler = Mock()
    collector._wait_for_condition = lambda predicate, **kwargs: bool(predicate())
    collector.open_approval_dialog = Mock(return_value=SimpleNamespace())
    collector.cancel_approval_dialog = Mock(return_value=True)
    return collector


class ExactOnlyWindow:
    """Reject best-match lookup because it reads/expands unrelated combo boxes."""

    def __init__(self):
        self.lookups = []
        self.button = Mock()
        self.info = Mock()
        self.info.exists.return_value = False

    def __getitem__(self, key):
        raise AssertionError("best-match lookup expands toolbar combo boxes")

    def child_window(self, **criteria):
        self.lookups.append(criteria)
        return self.info if criteria.get("control_type") == "Window" else self.button


def test_approval_button_uses_exact_lookup_without_toolbar_scan():
    window = ExactOnlyWindow()
    assert ButtonController(window).click_approval_button()
    assert window.lookups == [{"title": "결재", "control_type": "Button"}]


def test_payment_info_button_uses_exact_lookup_without_toolbar_scan():
    manager = WindowManager(Mock())
    manager.dlg = ExactOnlyWindow()
    assert manager.ensure_payment_info_window()
    assert {"title": "결재정보", "control_type": "Button"} in manager.dlg.lookups


def test_approval_tab_uses_exact_lookup_without_toolbar_scan():
    collector = OfficialCollector.__new__(OfficialCollector)
    collector.dlg = ExactOnlyWindow()
    collector.window_manager = Mock()
    collector.app = SimpleNamespace(process=123)
    collector.approval_line_handler = Mock()
    collector.open_approval_dialog()
    assert collector.dlg.lookups == [
        {"title": UIConfig.APPROVAL_TAB_TITLE, "control_type": "TabItem"}
    ]


@pytest.mark.parametrize(
    "body_text, expected_clicks",
    [("결재선 변경을 완료했습니다.", 1), ("결재를 진행하시겠습니까?", 0)],
)
def test_save_consumes_completion_result_after_original_dialog_disappears(
    monkeypatch, body_text, expected_clicks
):
    handler = ApprovalLineHandler()
    wrapper = Mock()
    wrapper.process_id.return_value = 123
    wrapper.is_visible.return_value = True
    specification = Mock()
    specification.wrapper_object.return_value = wrapper
    specification.is_visible.side_effect = RuntimeError("closed window lookup")
    save = Mock()
    save.window_text.return_value = "확인"
    save.rectangle.return_value = SimpleNamespace(top=1)
    save.click.side_effect = lambda: setattr(wrapper.is_visible, "return_value", False)
    specification.descendants.return_value = [save]
    result = Mock()
    result.is_visible.return_value = True
    body = Mock()
    body.window_text.return_value = body_text
    acknowledge = Mock()
    acknowledge.window_text.return_value = "확인"
    acknowledge.click.side_effect = lambda: setattr(
        result.is_visible, "return_value", False
    )
    result.descendants.side_effect = lambda **kw: (
        [body] if kw.get("class_name") == "Static" else [acknowledge]
    )
    desktop = Mock()
    desktop.windows.return_value = [result]
    monkeypatch.setattr(
        "services.approval_line_handler.Desktop",
        Mock(return_value=desktop),
        raising=False,
    )
    assert handler.confirm_dialog(
        specification, lambda predicate, **kw: predicate()
    ) is bool(expected_clicks)
    assert acknowledge.click.call_count == expected_clicks
    specification.is_visible.assert_not_called()


def test_manual_timeout_cancels_without_confirming(monkeypatch):
    collector = make_collector()
    requested = []
    monkeypatch.setattr(
        "services.official_service.get_timed_input",
        lambda prompt, **kwargs: requested.append(kwargs["timeout"]) or None,
    )
    assert collector.capture_approval_line() is None
    assert requested == [60.0]
    assert TimeoutConfig.MANUAL_APPROVAL_LINE_WAIT <= 60.0
    collector.cancel_approval_dialog.assert_called_once()
    collector.approval_line_handler.confirm_dialog.assert_not_called()


def test_role_probe_stops_when_close_does_not_hide_dialog():
    collector = make_collector()
    dialog = Mock()
    dialog.wrapper_object.return_value = dialog
    dialog.is_visible.return_value = True
    collector.open_approval_dialog.return_value = dialog
    collector.cancel_approval_dialog = OfficialCollector.cancel_approval_dialog.__get__(
        collector
    )
    collector.approval_line_handler.read_role_markers.return_value = [
        "접수",
        "업무담당자",
    ]
    assert collector.read_approval_role_markers() is None
    collector.approval_line_handler.confirm_dialog.assert_not_called()


def test_manual_capture_waits_for_confirmed_save(monkeypatch):
    collector = make_collector()
    monkeypatch.setattr(
        "services.official_service.get_timed_input", lambda *args, **kwargs: ""
    )
    collector.approval_line_handler.read_dialog_names.return_value = ["Lee", "Kim"]
    collector.approval_line_handler.confirm_dialog.return_value = False
    assert collector.capture_approval_line() is None
    collector.approval_line_handler.confirm_dialog.return_value = True
    assert collector.capture_approval_line() == ["Lee", "Kim"]


def test_ambiguous_reuse_cancels_without_mutation():
    collector = make_collector()
    collector.approval_line_handler.resolve_approvers.return_value = None
    assert not collector.apply_approval_names(["Kim"])
    collector.approval_line_handler.set_approval_line.assert_not_called()
    collector.cancel_approval_dialog.assert_called_once()


def test_role_probe_closes_dialog_even_on_unavailable_columns():
    collector = make_collector()
    collector.approval_line_handler.read_role_markers.return_value = None
    assert collector.read_approval_role_markers() is None
    collector.cancel_approval_dialog.assert_called_once()


def test_role_probe_closes_dialog_when_escape_is_ignored():
    """Replay the live failure: roles read, but Escape leaves the dialog open."""
    collector = make_collector()
    dialog = Mock()
    dialog.wrapper_object.return_value = dialog
    dialog.is_visible.return_value = True
    dialog.close.side_effect = lambda **kwargs: setattr(
        dialog.is_visible, "return_value", False
    )
    collector.open_approval_dialog.return_value = dialog
    collector.cancel_approval_dialog = OfficialCollector.cancel_approval_dialog.__get__(
        collector
    )
    collector.approval_line_handler.read_role_markers.return_value = [
        "접수",
        "업무담당자",
    ]
    assert collector.read_approval_role_markers() == ["접수", "업무담당자"]
    dialog.close.assert_called_once_with(wait_time=TimeoutConfig.APPROVAL_LINE_WAIT)
    dialog.type_keys.assert_not_called()
    collector.approval_line_handler.confirm_dialog.assert_not_called()


def test_cancel_verifies_original_wrapper_without_resolving_closed_window():
    """WindowSpecification lookup fails after its matching dialog disappears."""
    collector = make_collector()
    collector.cancel_approval_dialog = OfficialCollector.cancel_approval_dialog.__get__(
        collector
    )
    wrapper = Mock()
    wrapper.is_visible.return_value = True
    wrapper.close.side_effect = lambda **kwargs: setattr(
        wrapper.is_visible, "return_value", False
    )
    specification = Mock()
    specification.wrapper_object.return_value = wrapper
    specification.close.side_effect = wrapper.close
    specification.is_visible.side_effect = RuntimeError("closed window not found")

    assert collector.cancel_approval_dialog(specification) is True
    specification.is_visible.assert_not_called()
    wrapper.close.assert_called_once_with(wait_time=TimeoutConfig.APPROVAL_LINE_WAIT)


def test_cancel_treats_destroyed_wrapper_as_closed():
    """A destroyed wrapper after close() proves closure; lookup errors are closed."""
    from pywinauto.findwindows import ElementNotFoundError

    collector = make_collector()
    collector.cancel_approval_dialog = OfficialCollector.cancel_approval_dialog.__get__(
        collector
    )
    wrapper = Mock()
    wrapper.close.return_value = None
    wrapper.is_visible.side_effect = ElementNotFoundError("gone")
    specification = Mock()
    specification.wrapper_object.return_value = wrapper
    assert collector.cancel_approval_dialog(specification) is True
    wrapper.close.assert_called_once_with(wait_time=TimeoutConfig.APPROVAL_LINE_WAIT)


def test_blank_capture_rejected_before_confirm(monkeypatch):
    collector = make_collector()
    monkeypatch.setattr(
        "services.official_service.get_timed_input", lambda *args, **kwargs: ""
    )
    collector.approval_line_handler.read_dialog_names.return_value = ["Kim", ""]
    assert collector.capture_approval_line() is None
    collector.approval_line_handler.confirm_dialog.assert_not_called()


def test_console_failure_cancels_manual_dialog(monkeypatch):
    collector = make_collector()

    def disconnected(*args, **kwargs):
        raise OSError("console disconnected")

    monkeypatch.setattr("services.official_service.get_timed_input", disconnected)
    assert collector.capture_approval_line() is None
    collector.cancel_approval_dialog.assert_called_once()


def test_member_probe_discards_read_only_dialog():
    collector = make_collector()
    collector.approval_line_handler.read_role_members.return_value = [
        ("업무담당자", "Other")
    ]
    assert collector.read_approval_role_members() == [("업무담당자", "Other")]
    collector.cancel_approval_dialog.assert_called_once()


def test_screenshot_followup_text_is_read_from_uia_child_wrappers():
    """UIA children are wrappers, not WindowSpecifications with exists()."""
    collector = make_collector()
    collector.dlg = Mock()
    collector.dlg.window_text.return_value = "전자결재: budget"
    confirm = Mock()
    confirm.exists.return_value = True
    confirm.texts.return_value = ["확인"]
    message = "결재문서를 처리하였습니다.\n다음 문서를 처리하겠습니까?"
    child = SimpleNamespace(window_text=lambda: message)
    confirm.children.side_effect = lambda **criteria: (
        [child] if criteria["control_type"] == "Text" else []
    )
    collector.dlg.child_window.return_value = confirm
    collector.dialog_classifier = DialogClassifier()
    collector.dialog_handler = DialogHandler(collector.dlg, collector.dialog_classifier)
    assert collector._review_transition_ready("전자결재: budget") is True
    assert message in collector.dialog_handler.get_confirm_dialog_text()


def test_followup_yes_caption_has_an_explicit_click_fallback():
    main, dialog, button, absent = Mock(), Mock(), Mock(), Mock()
    absent.exists.return_value = False
    button.exists.return_value = True
    button.is_enabled.return_value = True
    dialog.child_window.side_effect = lambda **criteria: (
        button if criteria["title"] == "예(Y)" else absent
    )
    main.child_window.return_value = absent
    controller = ButtonController(main)
    assert controller._try_click_button(
        UIConfig.DIALOG_BUTTON_PATTERNS["confirm"], "confirm", dialog, "click"
    )
    button.click.assert_called_once()


def test_next_document_waits_for_loading_before_returning_a_title():
    """Replay old title surviving the Yes click until the next document loads."""
    collector = make_collector()
    previous, following = "전자결재: previous", "전자결재: following"
    state = {"title": previous, "clicked": False, "reads": 0}
    collector.dlg = Mock()
    confirm = Mock()
    collector.dlg.child_window.return_value = confirm
    confirm.exists.side_effect = lambda: not state["clicked"]
    collector.dlg.texts.side_effect = lambda: [state["title"]]

    def live_title():
        if state["clicked"]:
            state["reads"] += 1
            if state["reads"] >= 3:
                state["title"] = following
        return state["title"]

    def click(*args):
        state["clicked"] = True
        return True

    collector.dlg.window_text.side_effect = live_title
    collector.button_controller = Mock()
    collector.button_controller.click_dialog_button_unified.side_effect = click
    collector.dialog_handler = Mock()
    collector.dialog_handler.get_confirm_dialog_text.return_value = (
        "결재문서를 처리하였습니다. 다음 문서를 처리하겠습니까?"
    )
    collector.dialog_classifier = DialogClassifier()
    collector._wait_for_condition = lambda predicate, **kwargs: any(
        predicate() for _ in range(3)
    )
    assert collector.handle_document_flow_dialog(DocumentFlowState.CONTINUE)
    assert collector.get_official_title() == following


def test_next_document_timeout_stops_before_reusing_previous_title():
    collector = make_collector()
    collector.dlg = Mock()
    collector.dlg.window_text.return_value = "전자결재: previous"
    collector.dlg.child_window.return_value.exists.return_value = True
    collector.button_controller = Mock()
    collector.button_controller.click_dialog_button_unified.return_value = True
    collector.dialog_handler = Mock()
    collector.dialog_handler.get_confirm_dialog_text.return_value = (
        "다음 문서를 처리하겠습니까?"
    )
    collector.dialog_classifier = DialogClassifier()
    assert not collector.handle_document_flow_dialog(DocumentFlowState.CONTINUE)


def test_initial_document_without_flow_prompt_needs_no_transition():
    collector = make_collector()
    collector.dlg = Mock()
    collector.dlg.child_window.return_value.exists.return_value = False
    collector.button_controller = Mock()
    assert collector.handle_document_flow_dialog(DocumentFlowState.CONTINUE)
    collector.button_controller.click_dialog_button_unified.assert_not_called()


def test_continuation_does_not_confirm_an_unreviewed_approval_prompt():
    collector = make_collector()
    collector.dlg = Mock()
    collector.dlg.child_window.return_value.exists.return_value = True
    collector.button_controller = Mock()
    collector.dialog_handler = Mock()
    collector.dialog_handler.get_confirm_dialog_text.return_value = (
        "결재를 진행하시겠습니까?"
    )
    collector.dialog_classifier = DialogClassifier()
    assert not collector.handle_document_flow_dialog(DocumentFlowState.CONTINUE)
    collector.button_controller.click_dialog_button_unified.assert_not_called()


@pytest.mark.parametrize(
    "title,enabled,expected",
    [
        ("", True, False),
        ("전자결재: previous", True, False),
        ("전자결재: following", False, False),
        ("전자결재: following", True, True),
    ],
)
def test_next_document_readiness_rejects_partial_load(title, enabled, expected):
    collector = make_collector()
    collector.dlg = Mock()
    collector.dlg.window_text.return_value = title
    collector.dlg.is_enabled.return_value = enabled
    dialog = Mock()
    dialog.exists.return_value = False
    assert collector._next_document_ready(dialog, "전자결재: previous") == expected


def test_review_click_leaves_confirmation_to_operator():
    collector = make_collector()
    collector.button_controller = Mock()
    collector.dialog_handler = Mock()
    collector.button_controller.click_approval_button.return_value = True
    assert collector.click_review_approval_button()
    collector.button_controller.click_approval_button.assert_called_once()
    collector.dialog_handler.handle_approval_confirmation.assert_not_called()


@pytest.mark.parametrize("known_prompt", [True, False])
def test_review_confirmation_clicks_only_known_approval_prompt(known_prompt):
    dlg, confirm, prompt, button = Mock(), Mock(), Mock(), Mock()
    dlg.child_window.return_value = confirm
    confirm.exists.return_value = True
    prompt.exists.return_value = known_prompt
    confirm.child_window.side_effect = lambda **criteria: (
        prompt if criteria["class_name"] == "Static" else button
    )
    handler = DialogHandler(dlg, DialogClassifier())
    handler.get_confirm_dialog_text = Mock(
        return_value=(
            "결재를 진행하시겠습니까?" if known_prompt else "unexpected confirmation"
        )
    )
    assert (
        handler.confirm_reviewed_approval(lambda predicate, **kwargs: predicate())
        == known_prompt
    )
    assert button.click.call_count == int(known_prompt)


def test_review_confirmation_reads_known_body_without_static_caption():
    dlg, confirm, absent, button = Mock(), Mock(), Mock(), Mock()
    dlg.child_window.return_value = confirm
    confirm.exists.return_value = True
    absent.exists.return_value = False
    confirm.child_window.side_effect = lambda **criteria: (
        absent if criteria["class_name"] == "Static" else button
    )
    handler = DialogHandler(dlg, DialogClassifier())
    handler.get_confirm_dialog_text = Mock(
        return_value="확인\r\n결재를 진행하시겠습니까?"
    )
    assert handler.confirm_reviewed_approval(lambda predicate, **kwargs: predicate())
    button.click.assert_called_once()


def test_review_confirmation_accepts_already_processed_followup_without_another_click():
    dlg, confirm, absent, button = Mock(), Mock(), Mock(), Mock()
    dlg.child_window.return_value = confirm
    confirm.exists.return_value = True
    absent.exists.return_value = False
    confirm.child_window.side_effect = lambda **criteria: (
        absent if criteria["class_name"] == "Static" else button
    )
    handler = DialogHandler(dlg, DialogClassifier())
    handler.get_confirm_dialog_text = Mock(
        return_value=("결재문서를 처리하였습니다. 다음 문서를 처리하겠습니까?")
    )
    assert handler.confirm_reviewed_approval(lambda predicate, **kwargs: predicate())
    button.click.assert_not_called()


def test_unrecognized_review_confirmation_logs_observed_body(caplog):
    dlg, confirm, absent = Mock(), Mock(), Mock()
    dlg.child_window.return_value = confirm
    confirm.exists.return_value = True
    absent.exists.return_value = False
    confirm.child_window.return_value = absent
    handler = DialogHandler(dlg, DialogClassifier())
    handler.get_confirm_dialog_text = Mock(return_value="unexpected client message")
    assert not handler.confirm_reviewed_approval(
        lambda predicate, **kwargs: predicate()
    )
    assert "unexpected client message" in caplog.text


@pytest.mark.parametrize(
    "confirmed,result,expected",
    [
        (False, "", False),
        (True, "結", False),
        (True, "결재를 진행하시겠습니까?", False),
        (True, "다음 문서를 처리하겠습니까?", True),
        (True, "종료하시겠습니까?", True),
    ],
)
def test_review_success_requires_confirmation_and_transition(
    confirmed, result, expected
):
    collector = make_collector()
    collector.get_official_title = Mock(return_value="전자결재: budget")
    collector.dlg = Mock()
    collector.dlg.window_text.return_value = "전자결재: budget"
    collector.button_controller = Mock()
    collector.dialog_handler = Mock()
    collector.dialog_classifier = DialogClassifier()
    collector.dialog_handler.confirm_reviewed_approval.return_value = confirmed
    collector.dialog_handler.get_confirm_dialog_text.return_value = result
    assert collector.approve_reviewed_document("전자결재: budget") == expected
    collector.button_controller.click_approval_button.assert_called_once()
