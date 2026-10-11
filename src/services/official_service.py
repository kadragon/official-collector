# Trace: backlog.md - Task-card selection and confirmation fast pass
"""
공문 처리기를 제어하는 모듈.
pywinauto를 활용하여 전자결재 및 접수 창과 상호작용합니다.
"""

import time
from typing import List, Optional, Callable, Any, cast, Tuple
from enum import Enum
import _ctypes
import pyperclip
from pywinauto import Application, keyboard
from pywinauto.timings import TimeoutError as PyWinAutoTimeoutError
from pywinauto.findwindows import ElementAmbiguousError, ElementNotFoundError

from config import TimeoutConfig, UIConfig
from utils.error_handler import setup_logger, handle_pywinauto_error
from utils.performance_logger import log_execution_time
from utils.wait_helpers import wait_for_poll_interval, wait_for_ui_settle
from dialogs.dialog_classifier import DialogClassifier, DialogAction

# Import new modular components
from services.window_manager import WindowManager
from services.button_controller import ButtonController
from services.dialog_handler import DialogHandler, DocumentFlowState
from services.approval_line_handler import ApprovalLineHandler, Approver
from utils.timed_input import get_timed_input, choose_timed_option
from ui.rich_console import RichConsole

logger = setup_logger(__name__)
console = RichConsole()


class OfficialCollector:
    """
    전자결재 및 공문 처리를 위한 클래스.
    """

    def __init__(
        self,
        task_card_capture: Optional[
            Callable[[Any, Optional[str]], Optional[str]]
        ] = None,
    ) -> None:
        """
        OfficialCollector 인스턴스를 초기화하고, 지정된 창에 연결을 시도합니다.
        """
        self.app: Any = Application(backend="uia")
        self.dialog_classifier = DialogClassifier()
        self.task_card_capture = task_card_capture

        # Initialize WindowManager and connect to window
        self.window_manager = WindowManager(self.app)
        self.dlg = self.window_manager.connect_to_window(debug_mode=True)

        # Initialize components that depend on dlg
        self.button_controller = ButtonController(self.dlg)
        self.dialog_handler = DialogHandler(self.dlg, self.dialog_classifier)
        self.approval_line_handler = ApprovalLineHandler()

    def _wait_for_element(
        self,
        element_selector: Callable,
        timeout: float = TimeoutConfig.ELEMENT_WAIT,
        interval: float = TimeoutConfig.ELEMENT_WAIT_INTERVAL,
    ) -> bool:
        """
        요소가 준비될 때까지 대기합니다.

        Args:
            element_selector: 요소를 선택하는 함수
            timeout: 최대 대기 시간 (초)
            interval: 확인 간격 (초)

        Returns:
            bool: 요소가 준비되면 True, 타임아웃되면 False
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                element = element_selector()
                if element.exists() and element.is_enabled():
                    return True
            except (
                ElementNotFoundError,
                ElementAmbiguousError,
                AttributeError,
                RuntimeError,
            ) as e:
                logger.debug("요소 대기 중 오류 (계속 시도): %s", e)
            except (OSError, _ctypes.COMError, ValueError) as e:
                logger.warning("요소 대기 중 예상치 못한 오류: %s", e)
            wait_for_poll_interval(interval)
        return False

    def _wait_for_condition(
        self,
        condition: Callable[[], bool],
        timeout: float = TimeoutConfig.CONDITION_WAIT,
        interval: float = TimeoutConfig.CONDITION_WAIT_INTERVAL,
    ) -> bool:
        """
        조건이 만족될 때까지 대기합니다.

        Args:
            condition: 확인할 조건 함수
            timeout: 최대 대기 시간 (초)
            interval: 확인 간격 (초)

        Returns:
            bool: 조건이 만족되면 True, 타임아웃되면 False
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if condition():
                    return True
            except (
                ElementNotFoundError,
                ElementAmbiguousError,
                AttributeError,
                RuntimeError,
            ) as e:
                logger.debug("조건 확인 중 오류 (계속 시도): %s", e)
            except (OSError, _ctypes.COMError) as e:
                # COM 오류 (-2147220991, '이벤트에서 가입자를 불러낼 수 없습니다') 처리
                if e.args and e.args[0] == -2147220991:
                    logger.debug("COM 이벤트 오류 (계속 시도): %s", e)
                    wait_for_ui_settle(TimeoutConfig.SHORT_DELAY)  # 약간의 추가 대기
                else:
                    logger.warning("조건 확인 중 OS 오류: %s", e)
            except ValueError as e:
                logger.warning("조건 확인 중 예상치 못한 오류: %s", e)
            wait_for_poll_interval(interval)
        return False

    @log_execution_time(logger)
    def add_share(self, share_name: str) -> None:
        """
        공람 그룹에 지정된 이름을 추가합니다.

        Args:
            share_name (str): 추가할 공람 대상자의 이름.
        """
        if self.dlg:
            self.dlg["공람지정"].click()
            self.dlg["공람그룹"].select()
            self.dlg[share_name].select()
            self.dlg["▶ 추가"].click()
            self.dlg["확인"].click()
        else:
            logger.error("대상 창이 연결되어 있지 않습니다.")

    @log_execution_time(logger, "결재선 지정")
    def approval(self, approval_name: str) -> None:
        """
        결재선을 설정합니다.

        접수 문서 처리 순서:
        1) 결재정보 다이얼로그가 있는지 확인한다. 없다면 결재정보 버튼을 클릭해서, 다이얼로그를 띄운다.
        2) 결재선 지정 프로세스를 진행한다.

        Args:
            approval_name (str): 결재선 이름.
        """
        if not self.dlg:
            logger.error("대상 창이 연결되어 있지 않습니다.")
            return
        try:
            # 1) 결재정보 다이얼로그가 있는지 확인하고 필요시 열기
            if not self.window_manager.ensure_payment_info_window():
                logger.error("결재정보 창을 열 수 없어 결재선 설정을 중단합니다.")
                return
            # 2) 결재선 지정 프로세스 진행
            logger.info("결재선 지정 시작: %s", approval_name)
            # 결재선 선택
            approval_selector = self.dlg["결재선"]
            approval_selector.select()
            approval_selector.wait("enabled", timeout=TimeoutConfig.WINDOW_READY)
            keyboard.send_keys("{TAB 5}")
            pyperclip.copy(approval_name)
            keyboard.send_keys("^v{DOWN}")
            # 확인 버튼 클릭
            confirm_btn = self.dlg["확인"]
            confirm_btn.wait("enabled", timeout=TimeoutConfig.WINDOW_READY)
            confirm_btn.click()
            logger.info("결재선 지정 완료: %s", approval_name)
        except (
            PyWinAutoTimeoutError,
            ElementNotFoundError,
            AttributeError,
            RuntimeError,
            OSError,
        ) as e:
            logger.error("결재선 설정 중 오류 발생: %s", e)
            raise

    @log_execution_time(logger, "조직도 결재선 지정")
    def set_approval_line(self, approvers: List[Approver]) -> bool:
        """Build the approval line from the org chart in a fixed order.

        Unlike approval(), which reuses a preregistered 결재선 combo whose
        entries vary per document, this resolves each person in the org
        chart and stages the rows in the given order.

        Args:
            approvers: Desired members in display order (first = top row).

        Returns:
            bool: True when the saved order matches, False otherwise.
        """
        approval_dialog = self.open_approval_dialog()
        if approval_dialog is None:
            return False
        result = self.approval_line_handler.set_approval_line(
            approval_dialog, approvers, self._wait_for_condition
        )
        if not result:
            self.cancel_approval_dialog(approval_dialog)
        return result

    @log_execution_time(logger)
    @handle_pywinauto_error("Open approval dialog", logger, default_return=None)
    def open_approval_dialog(self) -> Any:
        """Open the approval tab and connect to its process-scoped win32 controls."""
        if not self.dlg:
            logger.error("대상 창이 연결되어 있지 않습니다.")
            return None
        try:
            if not self.window_manager.ensure_payment_info_window():
                logger.error(
                    "결재정보 창을 열 수 없어 조직도 결재선 지정을 중단합니다."
                )
                return None
            approval_tab = self.dlg.child_window(
                title=UIConfig.APPROVAL_TAB_TITLE, control_type="TabItem"
            )
            approval_tab.select()
            approval_tab.wait("enabled", timeout=TimeoutConfig.WINDOW_READY)
        except (
            PyWinAutoTimeoutError,
            ElementNotFoundError,
            AttributeError,
            RuntimeError,
            OSError,
        ) as e:
            logger.error("결재선 탭 전환 중 오류 발생: %s", e)
            return None
        process_id = getattr(self.app, "process", None)
        return self.approval_line_handler.connect_approval_window(process_id)

    @handle_pywinauto_error("Cancel approval dialog", logger, default_return=False)
    def cancel_approval_dialog(self, dialog: Any) -> bool:
        """Request window closure without depending on an Escape accelerator."""
        # A WindowSpecification resolves by title on every access. Retain the
        # original HWND wrapper so closure checks cannot re-search a gone dialog.
        window = dialog.wrapper_object()
        window.close(wait_time=TimeoutConfig.APPROVAL_LINE_WAIT)

        def closed() -> bool:
            try:
                return not window.is_visible()
            except (
                ElementNotFoundError,
                ElementAmbiguousError,
                AttributeError,
                RuntimeError,
            ):
                return True

        return self._wait_for_condition(
            closed, timeout=TimeoutConfig.APPROVAL_LINE_WAIT
        )

    @log_execution_time(logger)
    def read_approval_role_markers(self) -> Optional[List[str]]:
        """Probe the known stage-2 roles; close the read-only dialog afterward."""
        dialog = self.open_approval_dialog()
        if dialog is None:
            return None
        markers = self.approval_line_handler.read_role_markers(dialog)
        if not self.cancel_approval_dialog(dialog):
            logger.error("Approval role probe could not close its dialog")
            return None
        return cast(Optional[List[str]], markers)

    @log_execution_time(logger)
    def read_approval_role_members(self) -> Optional[List[Tuple[str, str]]]:
        """Read roles and names together, discarding the read-only dialog."""
        dialog = self.open_approval_dialog()
        if dialog is None:
            return None
        try:
            members = self.approval_line_handler.read_role_members(dialog)
        finally:
            closed = self.cancel_approval_dialog(dialog)
        if not closed:
            logger.error("Approval member probe could not close its dialog")
            return None
        return cast(Optional[List[Tuple[str, str]]], members)

    @handle_pywinauto_error("Reviewed approval button", logger, default_return=False)
    def click_review_approval_button(self) -> bool:
        """Click only the approval button; leave client confirmation to the operator."""
        return bool(self.button_controller.click_approval_button())

    @log_execution_time(logger)
    @handle_pywinauto_error("Reviewed document approval", logger, default_return=False)
    def approve_reviewed_document(self, title: str) -> bool:
        """Submit the consented document, then wait for a verified flow transition."""
        if self.get_official_title() != title:
            logger.warning("Reviewed document changed before submission")
            return False
        original_title = self.dlg.window_text()
        if not self.click_review_approval_button():
            return False
        if not self.dialog_handler.confirm_reviewed_approval(self._wait_for_condition):
            return False
        transitioned = self._wait_for_condition(
            lambda: self._review_transition_ready(original_title),
            timeout=TimeoutConfig.REVIEW_RESULT_WAIT,
        )
        if not transitioned:
            logger.warning(
                "Reviewed approval has no verified result/next document: observed=%r",
                self.dialog_handler.get_confirm_dialog_text(),
            )
        return transitioned

    def _review_transition_ready(self, original_title: str) -> bool:
        """Accept a known next/exit result or a changed document, not another approval."""
        text = self.dialog_handler.get_confirm_dialog_text()
        action = self.dialog_classifier.classify_dialog_action(text)
        if action in (DialogAction.CONTINUE, DialogAction.EXIT):
            return True
        if text.strip():
            return False
        return bool(self.dlg.window_text() != original_title)

    @log_execution_time(logger)
    def get_reception_members(self, department: str) -> tuple[str, List[str]]:
        """List configured department members, or request a bounded department pick."""
        dialog = self.open_approval_dialog()
        if dialog is None:
            return "", []
        result: tuple[str, List[str]] = ("", [])
        try:
            if not department:
                department = (
                    choose_timed_option(
                        "부서 선택",
                        self.approval_line_handler.list_departments(
                            dialog, self._wait_for_condition
                        ),
                    )
                    or ""
                )
            members = self.approval_line_handler.list_department_members(
                dialog, department, self._wait_for_condition
            )
            result = department, members
        finally:
            if not self.cancel_approval_dialog(dialog):
                logger.error("Reception member probe could not close its dialog")
                result = "", []
        return result

    @log_execution_time(logger)
    def apply_approval_names(self, names: List[str], department: str = "") -> bool:
        """Resolve departments before any mutation; abort incomplete/ambiguous reads."""
        dialog = self.open_approval_dialog()
        if dialog is None:
            return False
        if department:
            members = self.approval_line_handler.list_department_members(
                dialog, department, self._wait_for_condition
            )
            valid = all(
                sum(bool(text.split()) and text.split()[0] == name for text in members)
                == 1
                for name in names
            )
            approvers = (
                [Approver(department, name) for name in names]
                if valid and names
                else None
            )
        else:
            approvers = self.approval_line_handler.resolve_approvers(
                dialog, names, self._wait_for_condition
            )
        if approvers is None:
            self.cancel_approval_dialog(dialog)
            return False
        result = self.approval_line_handler.set_approval_line(
            dialog, approvers, self._wait_for_condition
        )
        if not result:
            self.cancel_approval_dialog(dialog)
        return result

    @log_execution_time(logger)
    def capture_approval_line(self) -> Optional[List[str]]:
        """Wait at most 60 seconds for Enter, then read and confirm the staged line."""
        dialog = self.open_approval_dialog()
        if dialog is None:
            return None
        console.print_info(
            "결재선을 구성한 뒤, 확인 버튼을 누르기 전에 콘솔에서 Enter 입력 (60초 이내)"
        )
        try:
            value = get_timed_input(
                "완료 후 Enter (Esc: 건너뛰기)",
                timeout=TimeoutConfig.MANUAL_APPROVAL_LINE_WAIT,
            )
        except (OSError, RuntimeError) as error:
            logger.error("Manual approval console failed: %s", error)
            self.cancel_approval_dialog(dialog)
            return None
        if value is None:
            self.cancel_approval_dialog(dialog)
            return None
        names = self.approval_line_handler.read_dialog_names(dialog)
        if (
            not names
            or any(not name.strip() for name in names)
            or len(set(names)) != len(names)
        ):
            logger.warning("Manual approval line is empty or ambiguous")
            self.cancel_approval_dialog(dialog)
            return None
        if not self.approval_line_handler.confirm_dialog(
            dialog, self._wait_for_condition
        ):
            self.cancel_approval_dialog(dialog)
            return None
        return cast(List[str], names)

    @log_execution_time(logger, "접수 버튼 처리")
    def reception(self, shared: Optional[str] = None) -> bool:
        """
        접수 버튼을 클릭하여 문서를 접수합니다.

        접수 처리 순서:
        3) 접수 버튼 클릭
        4) '문서를 접수하시겠습니까?' 확인 대화상자 → 확인 클릭
        5) 공람대상자가 '공람없음'이 아닐 경우 '공람지정을 완료하였습니다.' → 확인 클릭
        6) 후속 처리:
           6-1) '종료하시겠습니까?' → 확인 클릭하고 분류 종료
           6-2) '문서를 처리하겠습니까?' → 확인 클릭하고 새 문서 처리

        Args:
            shared: 공람대상자 정보. None, 빈 문자열, 또는 '공람없음'인 경우 공람지정 없음으로 처리
        """
        if not self.dlg:
            logger.error("대상 창이 연결되어 있지 않습니다.")
            return False
        # Parameter validation and normalization
        has_circulation = shared and shared.strip() and shared.strip() != "공람없음"
        logger.debug(
            "공람대상자 처리: shared='%s', has_circulation=%s", shared, has_circulation
        )
        try:
            # 3) 접수 버튼 클릭
            logger.info("접수 버튼 클릭")
            self.dlg["접수"].click()
            # 4) '문서를 접수하시겠습니까?' 확인 대화상자 처리
            if not self.dialog_handler.handle_reception_confirmation(
                self._wait_for_condition
            ):
                return False
            # 5) 공람지정 완료 확인 처리 (공람대상자가 있는 경우)
            if has_circulation:
                logger.info(
                    "공람대상자가 있어 공람지정 완료 확인 처리를 진행합니다: %s", shared
                )
                if not self.dialog_handler.handle_circulation_completion(
                    self._wait_for_condition
                ):
                    return False
            else:
                logger.debug("공람대상자가 없어 공람지정 완료 확인을 건너뜁니다")
            # 6) 후속 처리 분기 (종료 또는 다음 문서)
            if not self.dialog_handler.handle_reception_result(
                self._wait_for_condition
            ):
                return False
            logger.info("접수 처리 완료")
            return True
        except (
            PyWinAutoTimeoutError,
            ElementNotFoundError,
            AttributeError,
            RuntimeError,
            OSError,
        ) as e:
            logger.error("접수 처리 중 오류 발생: %s", e)
            raise

    def get_official_title(self) -> str:
        """
        Return the raw document title for identity checks and matching.

        Returns:
            str: Raw title, preserving years and attachment metadata.
        """
        if self.dlg:
            texts = self.dlg.texts()
            raw_title = texts[0] if texts else ""
            return str(raw_title)
        logger.error("대상 창이 연결되어 있지 않습니다.")
        return ""

    def document_sort(self, document_group_name: str) -> bool:
        """Reuse verified capture and guarded approval for the legacy entry point."""
        if not self.dlg:
            logger.error("Target document window is not connected")
            return False
        original_title = self.get_official_title()
        if not original_title:
            logger.warning("Task-card document identity is unavailable")
            return False
        if not self._perform_task_card_selection(document_group_name):
            return False
        if self.get_official_title() != original_title:
            logger.warning("Task-card document changed during selection")
            return False
        if not self.approve_reviewed_document(original_title):
            logger.warning("Task-card document approval is unverified")
            return False
        return True

    @log_execution_time(logger)
    def _perform_task_card_selection(self, document_group_name: str) -> bool:
        """Use the injected client capture; no coordinate clicks or fixed waits."""
        if self.task_card_capture is None:
            logger.warning("Verified task-card capture is not configured")
            return False
        selected = self.task_card_capture(self, document_group_name)
        if not selected or not selected.strip():
            logger.warning("Task-card selection cancelled or unverified")
            return False
        if selected.strip() != document_group_name.strip():
            logger.warning(
                "Task-card selection differs from the requested card: requested=%s, selected=%s",
                document_group_name,
                selected,
            )
            return False
        logger.info("Verified task-card selection: %s", selected)
        return True

    def check_document_flow_state(self) -> str:
        """
        현재 문서 처리 흐름 상태를 확인합니다.

        Returns:
            str: 현재 문서 처리 상태
        """
        return self.dialog_handler.check_document_flow_state()

    @handle_pywinauto_error("문서 흐름 대화상자 처리", logger, default_return=False)
    def handle_document_flow_dialog(
        self, state: str, auto_continue: bool = True
    ) -> bool:
        """
        문서 처리 흐름 대화상자를 처리합니다.

        Args:
            state: 현재 문서 흐름 상태
            auto_continue: 자동으로 다음 문서 처리를 계속할지 여부

        Returns:
            bool: 처리 계속 여부 (True: 계속, False: 종료)
        """
        if state == DocumentFlowState.CONTINUE:
            dialog = self.dlg.child_window(title="확인", control_type="Window")
            if not dialog.exists():
                return True
            text = self.dialog_handler.get_confirm_dialog_text()
            if (
                self.dialog_classifier.classify_dialog_action(text)
                != DialogAction.CONTINUE
            ):
                logger.warning("Refusing unexpected continuation prompt: %s", text)
                return False
            previous_title = self.dlg.window_text()
            msg = (
                "자동으로 다음 문서 처리 계속"
                if auto_continue
                else "다음 문서 처리 여부를 사용자가 결정"
            )
            logger.info(msg)
            if not self.button_controller.click_dialog_button_unified(
                "confirm", dialog
            ):
                return False
            ready = self._wait_for_condition(
                lambda: self._next_document_ready(dialog, previous_title),
                timeout=TimeoutConfig.NEXT_DOCUMENT_WAIT,
            )
            if not ready:
                logger.warning(
                    "Next document did not finish loading: %s", previous_title
                )
            return ready
        elif state == DocumentFlowState.EXIT:
            logger.info("문서 처리 종료 확인")
            self.button_controller.click_dialog_button_unified("confirm")
            return False
        elif state == DocumentFlowState.UNKNOWN:
            logger.warning("알 수 없는 대화상자 - 기본 처리")
            self.button_controller.click_dialog_button_unified("confirm")
            return False
        else:
            logger.warning("알 수 없는 상태: %s", state)
            return False

    def _next_document_ready(self, dialog: Any, previous_title: str) -> bool:
        """Do not expose the old or empty title while the next document is loading."""
        if dialog.exists():
            return False
        title = self.dlg.window_text()
        return bool(title.strip() and title != previous_title and self.dlg.is_enabled())

    def handle_cancel_dialog(self) -> bool:
        """
        대화상자에서 취소 버튼을 클릭합니다.

        Returns:
            bool: 취소 버튼 클릭 성공 여부
        """
        return self.button_controller.click_cancel_button()

    def handle_confirm_dialog(self) -> bool:
        """
        대화상자에서 확인 버튼을 클릭합니다.

        Returns:
            bool: 확인 버튼 클릭 성공 여부
        """
        return self.button_controller.click_confirm_button()


if __name__ == "__main__":
    pass
