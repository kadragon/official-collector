"""
Dialog handler module for official document automation.
Coordinates reception, approval, and flow state using confirmation-window readers.
"""

# Trace: backlog.md - Task-card selection and confirmation fast pass

import _ctypes
from typing import Any, Callable
from pywinauto.findwindows import ElementNotFoundError, ElementAmbiguousError

from config import TimeoutConfig, UIConfig
from utils.error_handler import setup_logger
from utils.performance_logger import log_execution_time
from utils.wait_helpers import wait_for_ui_settle
from services.confirm_dialog_reader import ConfirmDialogReader
from dialogs.dialog_classifier import DialogClassifier, DialogAction

logger = setup_logger(__name__)


class DocumentFlowState:
    """문서 처리 흐름 상태를 나타내는 열거형"""

    CONTINUE = "continue"  # 다음 문서 처리 계속
    EXIT = "exit"  # 처리 종료
    UNKNOWN = "unknown"  # 알 수 없는 상태


class DialogHandler(ConfirmDialogReader):
    """Manages dialog detection, analysis, and flow state for the automation system."""

    def __init__(self, dlg: Any, dialog_classifier: DialogClassifier) -> None:
        """
        Initialize the DialogHandler.

        Args:
            dlg: Main dialog window reference
            dialog_classifier: DialogClassifier instance for dialog action classification
        """
        super().__init__(dlg)
        self.dialog_classifier = dialog_classifier

    def check_document_flow_state(self) -> str:
        """
        현재 문서 처리 흐름 상태를 확인합니다.

        Returns:
            str: 현재 문서 처리 상태 (CONTINUE, EXIT, UNKNOWN)
        """
        try:
            # 확인 창이 존재하는지 확인
            confirm_window = self.dlg.child_window(title="확인", control_type="Window")
            if not confirm_window.exists():
                return DocumentFlowState.CONTINUE

            # 창의 텍스트 내용을 확인하여 상태 결정
            window_text = self.get_confirm_dialog_text()
            action = self.dialog_classifier.classify_dialog_action(window_text)

            if action == DialogAction.UNKNOWN and (
                window_text.strip() == "확인" or not window_text.strip()
            ):
                # 텍스트를 충분히 읽지 못한 경우, 더 자세히 분석
                logger.warning(
                    "대화상자 텍스트가 불완전합니다. 더 상세한 분석을 시도합니다."
                )
                detailed_text = self.get_detailed_dialog_text()
                if detailed_text:
                    logger.info("상세 텍스트 발견: '%s'", detailed_text)
                    action = self.dialog_classifier.classify_dialog_action(
                        detailed_text
                    )

                if action == DialogAction.UNKNOWN:
                    logger.warning("대화상자 내용을 판단할 수 없습니다")
                    return DocumentFlowState.UNKNOWN

            # DialogAction을 DocumentFlowState로 변환
            if action == DialogAction.EXIT:
                flow_state = DocumentFlowState.EXIT
            elif action in (
                DialogAction.CONTINUE,
                DialogAction.APPROVE,
                DialogAction.CANCEL_APPROVE,
            ):
                flow_state = DocumentFlowState.CONTINUE
            else:
                flow_state = DocumentFlowState.UNKNOWN

            # 로깅
            action_descriptions = {
                DialogAction.CONTINUE: "다음 문서 처리 대화상자 감지",
                DialogAction.EXIT: "종료 확인 대화상자 감지",
                DialogAction.APPROVE: "결재 진행 확인 대화상자 감지",
                DialogAction.CANCEL_APPROVE: "취소 결재 확인 대화상자 감지",
                DialogAction.UNKNOWN: "알 수 없는 확인 대화상자",
            }

            logger.info(action_descriptions.get(action, f"알 수 없는 액션: {action}"))
            return flow_state

        except (AttributeError, RuntimeError, ElementNotFoundError) as e:
            logger.debug("문서 흐름 상태 확인 중 예외: %s", e)
            return DocumentFlowState.CONTINUE
        except Exception as e:
            logger.warning("예상치 못한 오류: %s", e)
            return DocumentFlowState.EXIT

    @log_execution_time(logger)
    def _confirm_known_reception_body(
        self, expected: str, timeout: float, wait_for_condition: Callable
    ) -> bool:
        """Resolve matching windows without lazy title lookups, then retain the HWND."""
        observed_text = ""
        matching_dialog = None
        try:
            scope = self.dlg.wrapper_object()
        except (
            ElementNotFoundError,
            ElementAmbiguousError,
            AttributeError,
            RuntimeError,
            OSError,
            _ctypes.COMError,
            IndexError,
        ) as error:
            logger.warning("Reception window unavailable: %s", error)
            return False

        def ready() -> bool:
            nonlocal observed_text, matching_dialog
            try:
                dialogs = scope.descendants(
                    title=UIConfig.CONFIRM_BUTTON, control_type="Window"
                )
                if len(dialogs) != 1:
                    return False
                candidate = dialogs[0]
                observed_text = self.get_quick_dialog_text(
                    candidate, patterns=(expected,)
                )
                if not observed_text.strip():
                    # Preserve the old exact Static lookup for nested/non-Text bodies.
                    controls = candidate.descendants(
                        title=expected, class_name="Static"
                    )
                    if len(controls) != 1:
                        return False
                    observed_text = str(controls[0].window_text() or "").strip()
                if observed_text.strip() != expected:
                    return False
                matching_dialog = candidate
                return True
            except (
                ElementNotFoundError,
                ElementAmbiguousError,
                AttributeError,
                RuntimeError,
                OSError,
                _ctypes.COMError,
                IndexError,
            ) as error:
                logger.debug("Reception confirmation read failed: %s", error)
                return False

        if (
            not wait_for_condition(
                ready, timeout=timeout, interval=TimeoutConfig.CONDITION_WAIT_INTERVAL
            )
            or matching_dialog is None
        ):
            logger.warning(
                "Reception confirmation unverified: observed=%r", observed_text
            )
            return False
        try:
            buttons = [
                button
                for button in matching_dialog.descendants(
                    title=UIConfig.CONFIRM_BUTTON, control_type="Button"
                )
                if button.is_visible() and button.is_enabled()
            ]
            if len(buttons) != 1:
                logger.warning("Reception confirmation button is missing or ambiguous")
                return False
            buttons[0].click()
        except (
            ElementNotFoundError,
            ElementAmbiguousError,
            AttributeError,
            RuntimeError,
            OSError,
            _ctypes.COMError,
            IndexError,
        ) as error:
            logger.warning("Reception confirmation click failed: %s", error)
            return False
        logger.info("Reception confirmation clicked: %s", observed_text)
        return True

    @log_execution_time(logger)
    def handle_reception_confirmation(
        self, wait_for_condition_callback: Callable
    ) -> bool:
        """Confirm only the known reception question, using the body fast pass."""
        return bool(
            self._confirm_known_reception_body(
                "문서를 접수하시겠습니까?",
                TimeoutConfig.RECEPTION_CONFIRMATION,
                wait_for_condition_callback,
            )
        )

    @log_execution_time(logger)
    def handle_circulation_completion(
        self, wait_for_condition_callback: Callable
    ) -> bool:
        """Acknowledge only the known circulation completion body."""
        return bool(
            self._confirm_known_reception_body(
                "공람지정을 완료하였습니다.",
                TimeoutConfig.CIRCULATION_COMPLETION,
                wait_for_condition_callback,
            )
        )

    @log_execution_time(logger)
    def handle_reception_result(self, wait_for_condition_callback: Callable) -> bool:
        """
        접수 후 결과 처리 (종료 또는 다음 문서).

        Args:
            wait_for_condition_callback: 조건 대기 콜백 함수
        """
        dialog = self.dlg.child_window(title="확인", control_type="Window")
        observed_text = ""

        def result_ready() -> bool:
            nonlocal observed_text
            if not dialog.exists():
                return False
            observed_text = self.get_quick_dialog_text(
                dialog, patterns=UIConfig.RECEPTION_RESULT_PATTERNS
            )
            if not observed_text.strip() or observed_text.strip() == "확인":
                observed_text = self.get_detailed_dialog_text()
            return (
                "다음 문서를 처리하겠습니까" in observed_text
                or "종료하시겠습니까" in observed_text
            )

        if not wait_for_condition_callback(
            result_ready,
            timeout=TimeoutConfig.REVIEW_RESULT_WAIT,
            interval=TimeoutConfig.CONDITION_WAIT_INTERVAL,
        ):
            logger.warning("Reception result unverified: observed=%r", observed_text)
            return False
        logger.info("Verified reception result: %s", observed_text)
        # Leave the next/exit prompt for the main loop's load guard.
        return True

    @log_execution_time(logger)
    def handle_approval_confirmation(
        self, wait_for_condition_callback: Callable, handle_confirm_callback: Callable
    ) -> None:
        """
        '결재를 진행하시겠습니까?' 확인 대화상자를 처리합니다.

        Args:
            wait_for_condition_callback: 조건 대기 콜백 함수
            handle_confirm_callback: 확인 대화상자 처리 콜백 함수
        """
        # 더 정확하고 빠른 대화상자 식별: 특정 Static 텍스트로 직접 확인
        approval_dialog_appeared = wait_for_condition_callback(
            lambda: (
                self.dlg.child_window(title="확인", control_type="Window").exists()
                and self.dlg.child_window(
                    title="결재를 진행하시겠습니까?", class_name="Static"
                ).exists()
            ),
            timeout=TimeoutConfig.APPROVAL_CONFIRMATION,
            interval=TimeoutConfig.CONDITION_WAIT_INTERVAL,
        )

        if approval_dialog_appeared:
            logger.info("결재 진행 확인 대화상자 감지 - 확인 버튼 클릭")
            # 정확한 메시지가 확인되었으므로 즉시 확인 버튼 클릭
            confirm_dialog = self.dlg.child_window(title="확인", control_type="Window")
            confirm_button = confirm_dialog.child_window(
                title="확인", class_name="Button"
            )
            confirm_button.click()
            logger.debug("결재 진행 확인 완료")
        else:
            # 백업: 일반적인 확인 대화상자가 있는지 확인
            general_dialog_appeared = wait_for_condition_callback(
                lambda: self.dlg.child_window(
                    title="확인", control_type="Window"
                ).exists(),
                timeout=TimeoutConfig.APPROVAL_CONFIRMATION_BACKUP,
            )
            if general_dialog_appeared:
                confirm_dialog = self.dlg.child_window(
                    title="확인", control_type="Window"
                )
                dialog_text = self.analyze_dialog_content(confirm_dialog)
                logger.info("결재 확인 대화상자 텍스트: '%s'", dialog_text)

                # 결재 진행 확인 패턴 체크
                if "결재를 진행하시겠습니까" in dialog_text:
                    logger.info("결재 진행 확인 대화상자 감지 - 확인 버튼 클릭")
                    handle_confirm_callback()
                else:
                    # 기존 분류기도 사용
                    action = self.dialog_classifier.classify_dialog_action(dialog_text)
                    if action == DialogAction.APPROVE:
                        logger.info("결재 진행 확인 대화상자 감지 - 확인 버튼 클릭")
                    else:
                        logger.warning("예상하지 못한 확인 대화상자: %s", dialog_text)
                    handle_confirm_callback()
            else:
                logger.info("결재 진행 확인 대화상자가 나타나지 않음")

    def confirm_reviewed_approval(self, wait_for_condition: Callable) -> bool:
        """Confirm a known approval prompt, or accept an already-visible result."""
        dialog = self.dlg.child_window(title="확인", control_type="Window")
        observed_text = ""
        prompt_kind = ""

        def ready() -> bool:
            nonlocal observed_text, prompt_kind
            if not dialog.exists():
                return False
            observed_text = self.get_confirm_dialog_text()
            action = self.dialog_classifier.classify_dialog_action(observed_text)
            if (
                action == DialogAction.APPROVE
                and "결재를 진행하시겠습니까" in observed_text
            ):
                prompt_kind = "approval"
            elif (
                action == DialogAction.CONTINUE
                and "다음 문서를 처리하겠습니까" in observed_text
            ) or (action == DialogAction.EXIT and "종료하시겠습니까" in observed_text):
                prompt_kind = "result"
            else:
                prompt_kind = ""
            return bool(prompt_kind)

        if not wait_for_condition(
            ready,
            timeout=TimeoutConfig.REVIEW_CONFIRMATION_WAIT,
        ):
            logger.warning(
                "Reviewed approval confirmation unavailable or unexpected: observed=%r",
                observed_text,
            )
            return False
        if prompt_kind == "result":
            logger.info(
                "Reviewed approval already has a result prompt: %s", observed_text
            )
            return True
        dialog.child_window(title="확인", class_name="Button").click()
        logger.info("Reviewed approval confirmation clicked: %s", observed_text)
        return True

    @log_execution_time(logger)
    def handle_approval_result(self, click_confirm_callback: Callable) -> None:
        """
        결재 결과를 처리합니다 (완료 또는 다음 문서) - 초고속 최적화 버전.

        Args:
            click_confirm_callback: 확인 버튼 클릭 콜백 함수
        """
        logger.info("결재 결과 대화상자 대기 시작 - handle_approval_result() 호출됨")
        wait_for_ui_settle(TimeoutConfig.MINIMAL_DELAY)

        # 초고속 대화상자 찾기
        confirm_dialog = self.find_confirm_dialog()

        if not confirm_dialog:
            logger.info("대화상자 없이도 다음 처리 계속 진행")
            return

        # 빠른 텍스트 패턴 매칭 (분석 생략하고 즉시 처리)
        dialog_text = self.get_quick_dialog_text(confirm_dialog)
        logger.info("결재 확인 대화상자 텍스트: '%s'", dialog_text)

        # 즉시 패턴 매칭으로 빠른 처리
        if (
            "다음 문서를 처리하겠습니까" in dialog_text
            or "결재문서가 완료되었습니다" in dialog_text
        ):
            logger.info("다음 문서 처리 대화상자 감지")
            click_confirm_callback(confirm_dialog)
        elif "종료하시겠습니까" in dialog_text:
            logger.info("종료 확인 대화상자 감지 - 프로세스 종료")
            click_confirm_callback(confirm_dialog)
        else:
            logger.warning("Approval result body unverified: %r", dialog_text)
