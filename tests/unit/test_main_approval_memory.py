# Trace: backlog.md - Approval decision memory / Assigned reuse / Reception fallback
"""Composition and stage dispatch tests without external services or GUI actions."""

from unittest.mock import Mock
import pytest

import main


@pytest.fixture(autouse=True)
def configured_identity(monkeypatch):
    monkeypatch.setattr(main.config, "_my_name", "Me")


def test_supabase_mode_injects_a_separate_local_approval_store(monkeypatch):
    cloud = Mock()
    local = Mock()
    monkeypatch.setattr(main.config, "get_vector_backend", lambda: "supabase")
    monkeypatch.setattr(main, "OfficialCollector", Mock())
    monkeypatch.setattr(main, "OpenAIEmbeddingService", Mock())
    monkeypatch.setattr(main, "SupabaseService", Mock(return_value=cloud))
    monkeypatch.setattr(main, "LocalEmbeddingService", Mock())
    monkeypatch.setattr(main, "LocalVectorService", Mock(return_value=local))
    app = main.Main()
    assert app.document_processor.supabase_service is cloud
    assert app.document_processor.approval_store is local


def test_local_mode_reuses_one_local_store(monkeypatch):
    local = Mock()
    monkeypatch.setattr(main.config, "get_vector_backend", lambda: "local")
    monkeypatch.setattr(main, "OfficialCollector", Mock())
    monkeypatch.setattr(main, "LocalEmbeddingService", Mock())
    factory = Mock(return_value=local)
    monkeypatch.setattr(main, "LocalVectorService", factory)
    app = main.Main()
    assert (
        app.document_processor.approval_store is app.document_processor.supabase_service
    )
    factory.assert_called_once()


def test_assigned_stage_does_not_call_task_card_matching(monkeypatch):
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.document_processor = Mock()
    app.document_processor.process_assigned_document.return_value = True
    monkeypatch.setattr(main, "clear_screen", lambda: None)
    assert app._handle_assigned_document("전자결재: [a] [b] budget") is True
    app.document_processor.process_assigned_document.assert_called_once_with(
        "budget",
        app.collector.apply_approval_names,
        app.collector.capture_approval_line,
    )
    app.document_processor.process_task_card_matching.assert_not_called()


def test_stage_probe_uses_verified_role_strings():
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.collector.read_approval_role_members.return_value = [
        ("접수", "Reception"),
        ("업무담당자", "Me"),
    ]
    assert app._classify_document("전자결재: [a] [b] budget") == 2
    assert app._classify_document("접수: budget") == 1
    app.collector.read_approval_role_members.assert_called_once()


def test_failed_stage_probe_stops_without_guessing():
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.collector.read_approval_role_members.return_value = None
    assert app._classify_document("전자결재: budget") is None


@pytest.mark.parametrize("role", ["검토", "결재"])
def test_submitted_document_routes_own_reviewer_to_consent(role):
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.collector.read_approval_role_members.return_value = [
        ("기안", "Drafter"),
        (role, "Me"),
    ]
    assert app._classify_document("전자결재: submitted") == 4
    assert app.review_handler_name == "Drafter"
    assert app.review_role_label == "기안자"


def test_submitted_document_without_own_approval_role_stops():
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.collector.read_approval_role_members.return_value = [
        ("기안", "Drafter"),
        ("검토", "Other"),
    ]
    assert app._classify_document("전자결재: submitted") is None


@pytest.mark.parametrize("confirmed, expected", [(True, 3), (False, None)])
def test_final_handler_requires_completion_confirmation(
    monkeypatch, confirmed, expected
):
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.collector.read_approval_role_members.return_value = [
        ("업무담당자", "Me"),
        ("업무관리자", "Superior"),
        ("접수", "Reception"),
    ]
    monkeypatch.setattr(
        main,
        "choose_timed_option",
        lambda *args: "결재 완료 후 최종 업무처리" if confirmed else None,
    )
    assert app._classify_document("전자결재: final") == expected


@pytest.mark.parametrize(
    "members",
    [
        [("업무담당자", "Me")],
        [("접수", "Reception"), ("결재", "Superior"), ("업무담당자", "Me")],
    ],
)
# Trace: backlog.md - Unknown document stage must stop before completion
def test_run_unverified_own_stage_never_completes_document(monkeypatch, members):
    app = main.Main.__new__(main.Main)
    app.auto_continue = True
    app.collector = Mock()
    app.document_processor = Mock()
    app.collector.check_document_flow_state.side_effect = [
        main.DocumentFlowState.CONTINUE,
        main.DocumentFlowState.EXIT,
    ]
    app.collector.handle_document_flow_dialog.return_value = True
    app.collector.get_official_title.return_value = "전자결재: [a] [b] budget"
    app.collector.read_approval_role_members.return_value = members
    app.document_processor.get_pending_updates_count.return_value = (0, 0)
    monkeypatch.setattr(main, "clear_screen", lambda: None)
    monkeypatch.setattr(main, "wait_for_document_turnaround", lambda: None)
    app.run()
    app.document_processor.process_task_card_matching.assert_not_called()
    app.collector.document_sort.assert_not_called()
    app.collector.approve_reviewed_document.assert_not_called()
    app.collector.check_document_flow_state.assert_called_once()


@pytest.mark.parametrize(
    "roles", [[("업무담당자", "Other")], [("업무담당자", "Other"), ("결재", "Me")]]
)
def test_other_handler_routes_to_review_instead_of_task_cards(roles):
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.collector.read_approval_role_members.return_value = roles
    assert app._classify_document("전자결재: budget") == 4


@pytest.mark.parametrize(
    "answer, clicks", [("검토 완료, 결재", 1), ("건너뛰기", 0), (None, 0)]
)
def test_review_clicks_only_after_explicit_consent(monkeypatch, answer, clicks):
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.review_handler_name = "Other"
    app.collector.get_official_title.return_value = "전자결재: budget"
    monkeypatch.setattr(main, "choose_timed_option", lambda *args, **kwargs: answer)
    app._handle_review_document("전자결재: budget")
    assert app.collector.approve_reviewed_document.call_count == clicks
    app.collector.document_sort.assert_not_called()
    app.collector.apply_approval_names.assert_not_called()


def test_review_consent_does_not_apply_to_a_changed_document(monkeypatch):
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.review_handler_name = "Other"
    app.collector.get_official_title.return_value = "전자결재: another document"
    monkeypatch.setattr(
        main, "choose_timed_option", lambda *args, **kwargs: "검토 완료, 결재"
    )
    assert not app._handle_review_document("전자결재: budget")
    app.collector.approve_reviewed_document.assert_not_called()


def test_unknown_identity_stops_without_guessing(monkeypatch):
    monkeypatch.setattr(main.config, "_my_name", "")
    monkeypatch.setattr(main, "get_timed_text_input", lambda *args, **kwargs: None)
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.collector.read_approval_role_members.return_value = [("업무담당자", "Other")]
    assert app._classify_document("전자결재: budget") is None


@pytest.mark.parametrize(
    "members",
    [
        [],
        [("결재", "Me")],
        [("업무담당자", "")],
        [("업무담당자", "Me"), ("업무담당자", "Other")],
    ],
)
def test_unavailable_or_ambiguous_handler_stops(members):
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.collector.read_approval_role_members.return_value = members
    assert app._classify_document("전자결재: budget") is None


def test_run_other_handler_never_enters_classification_or_line_registration(
    monkeypatch,
):
    app = main.Main.__new__(main.Main)
    app.auto_continue = True
    app.collector = Mock()
    app.document_processor = Mock()
    app.collector.check_document_flow_state.side_effect = [
        main.DocumentFlowState.CONTINUE,
        main.DocumentFlowState.EXIT,
    ]
    app.collector.handle_document_flow_dialog.return_value = True
    app.collector.get_official_title.return_value = "전자결재: [a] [b] budget"
    app.collector.read_approval_role_members.return_value = [
        ("업무담당자", "Other"),
        ("결재", "Me"),
    ]
    app.document_processor.get_pending_updates_count.return_value = (0, 0)
    monkeypatch.setattr(main, "clear_screen", lambda: None)
    monkeypatch.setattr(main, "wait_for_document_turnaround", lambda: None)
    monkeypatch.setattr(
        main, "choose_timed_option", lambda *args, **kwargs: "검토 완료, 결재"
    )
    app.run()
    app.collector.approve_reviewed_document.assert_called_once()
    app.document_processor.process_task_card_matching.assert_not_called()
    app.document_processor.process_assigned_document.assert_not_called()
    assert app.collector.check_document_flow_state.call_count == 2


def test_review_run_processes_two_documents_with_separate_consent(monkeypatch):
    app = main.Main.__new__(main.Main)
    app.auto_continue = True
    app.collector = Mock()
    app.document_processor = Mock()
    app.collector.check_document_flow_state.side_effect = [
        main.DocumentFlowState.CONTINUE,
        main.DocumentFlowState.CONTINUE,
        main.DocumentFlowState.EXIT,
    ]
    app.collector.handle_document_flow_dialog.return_value = True
    first, second = "전자결재: [a] [b] first", "전자결재: [a] [b] second"
    app.collector.get_official_title.side_effect = [first, first, second, second]
    app.collector.read_approval_role_members.return_value = [("업무담당자", "Other")]
    app.collector.approve_reviewed_document.return_value = True
    app.document_processor.get_pending_updates_count.return_value = (0, 0)
    monkeypatch.setattr(main, "clear_screen", lambda: None)
    monkeypatch.setattr(main, "wait_for_document_turnaround", lambda: None)
    consent = Mock(return_value="검토 완료, 결재")
    monkeypatch.setattr(main, "choose_timed_option", consent)
    summary = Mock()
    monkeypatch.setattr(main, "print_final_result", summary)
    app.run()
    assert consent.call_count == 2
    assert app.collector.approve_reviewed_document.call_count == 2
    summary.assert_called_once_with(2, 2)


def test_reception_resets_previous_department_before_exact_reuse():
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.document_processor = Mock()
    app.reception_department = "previous department"
    app.document_processor.process_reception_document.return_value = ("Kim", "공람없음")
    app.collector.apply_approval_names.return_value = True
    assert app._handle_reception_document("접수: budget")
    app.collector.apply_approval_names.assert_called_once_with(
        ["Kim"], main.config.my_department
    )
    app.collector.add_share.assert_not_called()
    app.collector.reception.assert_called_once_with("공람없음")


def test_reception_rpa_failure_discards_learning():
    app = main.Main.__new__(main.Main)
    app.collector = Mock()
    app.document_processor = Mock()
    app.document_processor.process_reception_document.return_value = ("Kim", "공람없음")
    app.collector.apply_approval_names.return_value = True
    app.collector.reception.side_effect = RuntimeError("client rejected document")
    assert not app._handle_reception_document("접수: budget")
    app.document_processor.discard_reception_update.assert_called_once_with(
        "접수: budget"
    )


@pytest.mark.parametrize("applied", [True, False])
def test_run_ends_after_assigned_line_without_reclassifying_same_document(
    monkeypatch, applied
):
    app = main.Main.__new__(main.Main)
    app.auto_continue = True
    app.collector = Mock()
    app.document_processor = Mock()
    app.collector.check_document_flow_state.side_effect = [
        main.DocumentFlowState.CONTINUE,
        main.DocumentFlowState.EXIT,
    ]
    app.collector.handle_document_flow_dialog.return_value = True
    app.collector.get_official_title.return_value = "전자결재: [a] [b] budget"
    app.collector.read_approval_role_members.return_value = [
        ("접수", "Reception"),
        ("업무담당자", "Me"),
    ]
    app.document_processor.process_assigned_document.return_value = applied
    app.document_processor.get_pending_updates_count.return_value = (0, 0)
    monkeypatch.setattr(main, "clear_screen", lambda: None)
    app.run()
    app.collector.check_document_flow_state.assert_called_once()
    app.document_processor.process_task_card_matching.assert_not_called()
    app.collector.document_sort.assert_not_called()
