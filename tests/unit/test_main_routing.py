"""
Unit tests for Main.run() stage routing (backlog.md Now).

Main is built via __new__ with mocked collaborators so no live client or
window connection is needed.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import main as main_module
from main import Main
from services.approval_line_handler import Approver
from services.dialog_handler import DocumentFlowState


def _bare_main(**overrides):
    instance = Main.__new__(Main)
    instance.auto_continue = True
    instance.collector = Mock()
    instance.document_processor = Mock()
    instance.approval_name_list = []
    instance.share_name_list = []
    for key, value in overrides.items():
        setattr(instance, key, value)
    return instance


class TestClassifyCurrentDocument:
    def test_reception_title_is_stage_1(self):
        assert _bare_main()._classify_current_document("접수: 예산안") == 1

    def test_injected_stage_2_rows(self):
        instance = _bare_main()
        assert (
            instance._classify_current_document(
                "전자결재: 안내", ["접수", "업무담당자"]
            )
            == 2
        )

    def test_empty_live_read_defaults_to_stage_3(self):
        instance = _bare_main()
        assert instance._read_staged_approval_methods() == []
        assert instance._classify_current_document("전자결재: 안내") == 3


class TestProcessAssignedDocument:
    def test_unresolved_superiors_skips_with_p1_reference(self):
        instance = _bare_main()
        assert instance._resolve_stage2_superiors() == []
        assert instance._process_assigned_document("전자결재: 안내") is False
        instance.collector.set_approval_line.assert_not_called()

    def test_resolved_superiors_reach_set_approval_line(self):
        superiors = [Approver(department="정보전산원", name="김승현")]
        instance = _bare_main()
        instance.collector.set_approval_line.return_value = True
        with patch.object(
            Main, "_resolve_stage2_superiors", return_value=superiors
        ):
            assert instance._process_assigned_document("전자결재: 안내") is True
        instance.collector.set_approval_line.assert_called_once_with(superiors)


class TestRunRoutesByStage:
    def _run_once(self, title, stage):
        instance = _bare_main()
        instance.collector.check_document_flow_state.side_effect = [
            DocumentFlowState.CONTINUE,
            DocumentFlowState.EXIT,
        ]
        instance.collector.handle_document_flow_dialog.return_value = True
        instance.collector.get_official_title.return_value = title
        instance._classify_current_document = Mock(return_value=stage)
        instance.document_processor.get_pending_updates_count.return_value = (0, 0)
        instance._process_approval_document = Mock(return_value=True)
        instance._process_assigned_document = Mock(return_value=True)
        with (
            patch.object(main_module, "clear_screen"),
            patch.object(main_module, "draw_header"),
            patch.object(main_module, "print_info"),
            patch.object(main_module, "print_document_info"),
            patch.object(main_module, "pause_between_documents"),
            patch.object(main_module, "print_final_result"),
        ):
            instance.run()
        return instance

    def test_stage_2_uses_assigned_path_not_task_card_path(self):
        instance = self._run_once("전자결재: 안내", 2)
        instance._process_assigned_document.assert_called_once()
        instance._process_approval_document.assert_not_called()

    def test_stage_3_keeps_task_card_path(self):
        instance = self._run_once("전자결재: 안내", 3)
        instance._process_approval_document.assert_called_once()
        instance._process_assigned_document.assert_not_called()
