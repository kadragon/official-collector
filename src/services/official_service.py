"""
공문 처리기를 제어하는 모듈.
pywinauto를 활용하여 전자결재 및 접수 창과 상호작용합니다.
"""

import time
from typing import Optional, Callable, Any
from enum import Enum
import pyperclip
from pywinauto import Application, keyboard, mouse
from pywinauto.timings import TimeoutError as PyWinAutoTimeoutError
from pywinauto.findwindows import ElementNotFoundError

from config import TimeoutConfig
from utils.error_handler import setup_logger
from utils.performance_logger import log_execution_time
from dialogs.dialog_classifier import DialogClassifier, DialogAction
from utils.text_utils import remove_numbers_from_title

# Import new modular components
from services.window_manager import WindowManager
from services.button_controller import ButtonController
from services.dialog_handler import DialogHandler, DocumentFlowState

logger = setup_logger(__name__)


class OfficialCollector:
    """
    전자결재 및 공문 처리를 위한 클래스.
    """

    def __init__(self) -> None:
        """
        OfficialCollector 인스턴스를 초기화하고, 지정된 창에 연결을 시도합니다.
        """
        self.app: Any = Application(backend="uia")
        self.dialog_classifier = DialogClassifier()

        # Initialize WindowManager and connect to window
        self.window_manager = WindowManager(self.app)
        self.dlg = self.window_manager.connect_to_window(debug_mode=True)

        # Initialize components that depend on dlg
        self.button_controller = ButtonController(self.dlg)
        self.dialog_handler = DialogHandler(self.dlg, self.dialog_classifier)

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
            except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                logger.debug("요소 대기 중 오류 (계속 시도): %s", e)
            except Exception as e:
                logger.warning("요소 대기 중 예상치 못한 오류: %s", e)
            time.sleep(interval)
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
            except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                logger.debug("조건 확인 중 오류 (계속 시도): %s", e)
            except OSError as e:
                # COM 오류 (-2147220991, '이벤트에서 가입자를 불러낼 수 없습니다') 처리
                if e.args[0] == -2147220991:
                    logger.debug("COM 이벤트 오류 (계속 시도): %s", e)
                    time.sleep(TimeoutConfig.SHORT_DELAY)  # 약간의 추가 대기
                else:
                    logger.warning("조건 확인 중 OS 오류: %s", e)
            except Exception as e:
                logger.warning("조건 확인 중 예상치 못한 오류: %s", e)
            time.sleep(interval)
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
        except (PyWinAutoTimeoutError, ElementNotFoundError) as e:
            logger.error("결재선 설정 중 오류 발생: %s", e)
            raise
        except Exception as e:
            logger.error("결재선 설정 중 예상치 못한 오류: %s", e)
            raise

    @log_execution_time(logger, "접수 버튼 처리")
    def reception(self, shared: Optional[str] = None) -> None:
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
            return
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
            self.dialog_handler.handle_reception_confirmation(self._wait_for_condition)
            # 5) 공람지정 완료 확인 처리 (공람대상자가 있는 경우)
            if has_circulation:
                logger.info(
                    "공람대상자가 있어 공람지정 완료 확인 처리를 진행합니다: %s", shared
                )
                self.dialog_handler.handle_circulation_completion(
                    self._wait_for_condition
                )
            else:
                logger.debug("공람대상자가 없어 공람지정 완료 확인을 건너뜁니다")
            # 6) 후속 처리 분기 (종료 또는 다음 문서)
            self.dialog_handler.handle_reception_result(
                self._wait_for_condition, self.button_controller.click_confirm_button
            )
            logger.info("접수 처리 완료")
        except Exception as e:
            logger.error("접수 처리 중 오류 발생: %s", e)
            raise

    def get_official_title(self) -> str:
        """
        공문의 제목을 반환합니다 (숫자 제거).

        Returns:
            str: 공문 제목 (숫자가 제거된 상태).
        """
        if self.dlg:
            texts = self.dlg.texts()
            raw_title = texts[0] if texts else ""
            return remove_numbers_from_title(raw_title)
        logger.error("대상 창이 연결되어 있지 않습니다.")
        return ""

    def document_sort(self, document_group_name: str) -> None:
        """
        전자결재 문서 분류 과정을 실행합니다.

        1) 결재정보 다이얼로그가 있는지 확인한다. 없다면 결재정보 버튼을 클릭해서, 다이얼로그를 띄운다.
        2) 문서카드 선택 프로세스를 진행한다.
        3) 결재 버튼을 클릭한다.
        4) 확인 다이얼로그에 텍스트 '결재를 진행하시겠습니까?' 가 뜨면 확인 버튼을 클릭한다.
        5) 4단계에서 확인 버튼 클릭 후
           5-1) '종료하시겠습니까?' 메시지가 포함된 확인 다이얼로그가 확인되면 확인 버튼을 누르고 분류 종료
           5-2) '문서를 처리하겠습니까?' 메시지가 포함된 확인 다이얼로그가 확인되면 확인 버튼을 누르고 새로 로드된 문서 처리

        Args:
            document_group_name (str): 선택할 문서 그룹 이름.
        """
        if not self.dlg:
            logger.error("대상 창이 연결되어 있지 않습니다.")
            return
        try:
            # 1) 결재정보 다이얼로그 확인 및 열기
            if not self.window_manager.ensure_payment_info_window():
                logger.error("결재정보 창을 열 수 없어 문서 분류를 중단합니다.")
                return
            # 2) 문서카드 선택 프로세스 진행
            self._perform_task_card_selection(document_group_name)
            # 3) 결재 버튼 클릭
            self.button_controller.click_approval_button()
            # 4) '결재를 진행하시겠습니까?' 확인 대화상자 처리
            self.dialog_handler.handle_approval_confirmation(
                self._wait_for_condition, self.button_controller.click_confirm_button
            )
            # 5) 최종 결과 처리 (완료 또는 다음 문서)
            self.dialog_handler.handle_approval_result(
                lambda dialog: self.button_controller.click_dialog_button_unified(
                    "confirm", dialog
                )
            )
            logger.info("문서 분류 처리 완료")
        except Exception as e:
            logger.error("문서 분류 중 오류 발생: %s", e)
            raise

    @log_execution_time(logger)
    def _perform_task_card_selection(self, document_group_name: str) -> None:
        """문서카드 선택 프로세스를 수행합니다."""
        info_window = self.window_manager.wait_for_window("결재정보")
        info_window.set_focus()
        keyboard.send_keys("{TAB 3}")
        keyboard.send_keys("{SPACE}")
        # '과제카드 선택' 다이얼로그가 나타날 때까지 대기
        dialog = self.window_manager.wait_for_window("과제카드 선택")
        dialog_rect = dialog.rectangle()
        mouse.click(coords=(dialog_rect.right - 20, dialog_rect.top + 50))
        keyboard.send_keys("{TAB 2}")
        pyperclip.copy(document_group_name)
        keyboard.send_keys("^v")
        keyboard.send_keys("{ENTER}")
        time.sleep(TimeoutConfig.SHORT_DELAY)
        keyboard.send_keys("{TAB}")
        keyboard.send_keys("{SPACE}")
        keyboard.send_keys("{TAB 3}")
        keyboard.send_keys("{ENTER}")
        time.sleep(TimeoutConfig.SHORT_DELAY)
        keyboard.send_keys("{ENTER}")
        logger.info("문서카드 선택 완료: %s", document_group_name)

    def check_document_flow_state(self) -> str:
        """
        현재 문서 처리 흐름 상태를 확인합니다.

        Returns:
            str: 현재 문서 처리 상태
        """
        return self.dialog_handler.check_document_flow_state()

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
        try:
            if state == DocumentFlowState.CONTINUE:
                if auto_continue:
                    logger.info("자동으로 다음 문서 처리 계속")
                    self.button_controller.click_dialog_button_unified("confirm")
                    return True
                else:
                    # 사용자에게 선택 권한 제공
                    logger.info("다음 문서 처리 여부를 사용자가 결정")
                    self.button_controller.click_dialog_button_unified("confirm")
                    return True
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
        except Exception as e:
            logger.error("문서 흐름 대화상자 처리 중 오류: %s", e)
            return False

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
