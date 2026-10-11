# Trace: backlog.md - Task-card selection and confirmation fast pass
"""Confirmation workflows read bodies once and reject unrelated prompts."""

from unittest.mock import Mock
from unittest.mock import call

import pytest

from config import TimeoutConfig
from dialogs.dialog_classifier import DialogClassifier
from services.dialog_handler import DialogHandler
from pywinauto.findwindows import ElementAmbiguousError
from pywinauto.findbestmatch import MatchError


def make_handler(body, caption="확인"):
    dialog = Mock()
    dialog.exists.return_value = True
    dialog.window_text.return_value = caption
    controls = [Mock(window_text=Mock(return_value=text)) for text in body]
    dialog.children.return_value = controls
    button = dialog.child_window.return_value
    button.is_visible.return_value = True
    button.is_enabled.return_value = True
    dialog.descendants.side_effect = lambda **criteria: (
        [button] if criteria.get("control_type") == "Button" else []
    )
    dlg = Mock()
    dlg.child_window.return_value = dialog
    dlg.wrapper_object.return_value.descendants.return_value = [dialog]
    return DialogHandler(dlg, DialogClassifier()), dialog, controls


@pytest.mark.parametrize(
    "body",
    ["문서를 접수하시겠습니까?", "공람지정을 완료하였습니다.", "종료하시겠습니까?"],
)
def test_quick_reader_skips_confirmation_caption_and_reads_body_once(body):
    handler, dialog, controls = make_handler(["확인", body, "unread"])
    assert handler.get_quick_dialog_text(dialog) == body
    controls[0].window_text.assert_called_once_with()
    controls[1].window_text.assert_called_once_with()
    controls[2].window_text.assert_not_called()
    dialog.children.assert_called_once_with(control_type="Text")
    dialog.texts.assert_not_called()


def test_quick_reader_does_not_drop_later_body_or_read_stale_wrappers_twice():
    handler, dialog, controls = make_handler(
        ["확인", " ", "OK", "다음 문서를 처리하겠습니까?"]
    )
    controls[2].window_text.side_effect = RuntimeError("stale child")
    assert handler.get_quick_dialog_text(dialog) == "다음 문서를 처리하겠습니까?"
    assert all(control.window_text.call_count == 1 for control in controls)


@pytest.mark.parametrize(
    "method,body,timeout",
    [
        (
            "handle_reception_confirmation",
            "문서를 접수하시겠습니까?",
            TimeoutConfig.RECEPTION_CONFIRMATION,
        ),
        (
            "handle_circulation_completion",
            "공람지정을 완료하였습니다.",
            TimeoutConfig.CIRCULATION_COMPLETION,
        ),
    ],
)
def test_reception_messages_use_body_fast_pass_and_retained_dialog(
    method, body, timeout
):
    handler, dialog, controls = make_handler([body])
    wait = Mock(side_effect=lambda predicate, **kwargs: predicate())
    assert getattr(handler, method)(wait) is True
    handler.dlg.child_window.assert_not_called()
    controls[0].window_text.assert_called_once_with()
    dialog.descendants.assert_called_once_with(title="확인", control_type="Button")
    dialog.child_window.return_value.click.assert_called_once_with()
    assert wait.call_args.kwargs["timeout"] == timeout


@pytest.mark.parametrize(
    "body", ["알 수 없는 확인창", "취소 결재를 진행하시겠습니까?", "확인"]
)
def test_reception_confirmation_never_clicks_unknown_body(body):
    handler, dialog, _ = make_handler([body])
    wait = lambda predicate, **kwargs: predicate()
    assert handler.handle_reception_confirmation(wait) is False
    dialog.child_window.assert_not_called()


@pytest.mark.parametrize(
    "method,body",
    [
        (
            "handle_reception_confirmation",
            "이미 접수된 문서입니다. 다시 문서를 접수하시겠습니까?",
        ),
        (
            "handle_circulation_completion",
            "공람지정을 완료하였습니다. 그러나 오류가 발생했습니다.",
        ),
    ],
)
def test_confirmation_requires_exact_body_instead_of_phrase_in_warning(method, body):
    handler, dialog, _ = make_handler([body])
    assert getattr(handler, method)(lambda predicate, **kwargs: predicate()) is False
    dialog.child_window.return_value.click.assert_not_called()


def test_confirmation_clicks_original_wrapper_instead_of_replaced_title_spec():
    handler, original, _ = make_handler(["문서를 접수하시겠습니까?"])
    replacement = Mock()
    handler.dlg.child_window.return_value = replacement
    assert (
        handler.handle_reception_confirmation(lambda predicate, **kwargs: predicate())
        is True
    )
    original.child_window.return_value.click.assert_called_once_with()
    replacement.child_window.return_value.click.assert_not_called()
    handler.dlg.child_window.assert_not_called()


def test_confirmation_can_read_exact_nested_static_when_quick_body_is_empty():
    handler, dialog, _ = make_handler([])
    nested = Mock(window_text=Mock(return_value="문서를 접수하시겠습니까?"))
    button = dialog.child_window.return_value
    dialog.descendants.side_effect = [[nested], [button]]
    assert (
        handler.handle_reception_confirmation(lambda predicate, **kwargs: predicate())
        is True
    )
    assert dialog.descendants.call_args_list == [
        call(title="문서를 접수하시겠습니까?", class_name="Static"),
        call(title="확인", control_type="Button"),
    ]
    button.click.assert_called_once_with()


@pytest.mark.parametrize("windows", [[], [Mock(), Mock()]])
def test_confirmation_absent_or_ambiguous_windows_never_click(windows):
    handler, dialog, _ = make_handler(["문서를 접수하시겠습니까?"])
    handler.dlg.wrapper_object.return_value.descendants.return_value = windows
    assert (
        handler.handle_reception_confirmation(lambda predicate, **kwargs: predicate())
        is False
    )
    dialog.child_window.return_value.click.assert_not_called()


def test_confirmation_destroyed_wrapper_returns_failure_without_title_relookup():
    handler, dialog, _ = make_handler(["문서를 접수하시겠습니까?"])
    dialog.descendants.side_effect = RuntimeError("destroyed window")
    assert (
        handler.handle_reception_confirmation(lambda predicate, **kwargs: predicate())
        is False
    )
    handler.dlg.child_window.assert_not_called()
    dialog.child_window.return_value.click.assert_not_called()


@pytest.mark.parametrize(
    "error", [ElementAmbiguousError(), IndexError("stale"), MatchError("name", [])]
)
def test_quick_reader_returns_empty_for_ambiguous_or_unmatched_controls(error):
    handler, dialog, _ = make_handler([])
    dialog.window_text.side_effect = error
    assert handler.get_quick_dialog_text(dialog) == ""


@pytest.mark.parametrize("body", ["다음 문서를 처리하겠습니까?", "종료하시겠습니까?"])
def test_reception_result_reuses_fast_reader_and_leaves_prompt_for_load_guard(body):
    handler, dialog, controls = make_handler([body])
    wait = lambda predicate, **kwargs: predicate()
    assert handler.handle_reception_result(wait) is True
    controls[0].window_text.assert_called_once_with()
    dialog.children.assert_called_once_with(control_type="Text")
    dialog.texts.assert_not_called()
    dialog.child_window.assert_not_called()


@pytest.mark.parametrize("result", ["다음 문서를 처리하겠습니까?", "종료하시겠습니까?"])
@pytest.mark.parametrize(
    "prefix", ["결재문서가 완료되었습니다.", "공람지정을 완료하였습니다."]
)
def test_reception_result_reads_past_completion_body_to_separate_flow_question(
    prefix, result
):
    handler, dialog, controls = make_handler([prefix, result, "unread"])
    assert (
        handler.handle_reception_result(lambda predicate, **kwargs: predicate()) is True
    )
    controls[0].window_text.assert_called_once_with()
    controls[1].window_text.assert_called_once_with()
    controls[2].window_text.assert_not_called()
    dialog.children.assert_called_once_with(control_type="Text")
    dialog.texts.assert_not_called()
    dialog.child_window.assert_not_called()


@pytest.mark.parametrize(
    "body,clicks",
    [
        ("다음 문서를 처리하겠습니까?", 1),
        ("종료하시겠습니까?", 1),
        ("결재문서가 완료되었습니다.", 1),
        ("알 수 없는 확인창", 0),
        ("취소 결재를 진행하시겠습니까?", 0),
        ("확인", 0),
    ],
)
def test_approval_result_matches_body_without_clicking_unknowns(body, clicks):
    handler, dialog, controls = make_handler([body])
    click = Mock()
    handler.handle_approval_result(click)
    assert click.call_count == clicks
    if clicks:
        click.assert_called_once_with(dialog)
    controls[0].window_text.assert_called_once_with()
