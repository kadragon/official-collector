"""
공문 처리기를 제어하는 모듈.

pywinauto를 활용하여 전자결재 및 접수 창과 상호작용합니다.
"""

import time
from typing import Optional, Callable

import pyperclip
from pywinauto import Application, keyboard, mouse, findwindows
from pywinauto.timings import TimeoutError as PyWinAutoTimeoutError
from pywinauto.findwindows import ElementNotFoundError
from utils.error_handler import setup_logger, handle_connection_error

logger = setup_logger(__name__)


class OfficialCollector:
    """
    전자결재 및 공문 처리를 위한 클래스.
    """

    def __init__(self) -> None:
        """
        OfficialCollector 인스턴스를 초기화하고, 지정된 창에 연결을 시도합니다.
        """
        self.app: Application = Application(backend="uia")
        self.dlg: Optional[Application.window] = None
        self._connect_to_window()

    def _wait_for_element(self, element_selector: Callable, timeout: float = 10.0, interval: float = 0.1) -> bool:
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
            except Exception:
                pass
            time.sleep(interval)
        return False

    def _wait_for_window(self, title: str, timeout: float = 10.0):
        """
        특정 창이 나타날 때까지 대기합니다.
        
        Args:
            title: 대기할 창의 제목
            timeout: 최대 대기 시간 (초)
            
        Returns:
            찾은 창 객체
            
        Raises:
            PyWinAutoTimeoutError: 타임아웃된 경우
        """
        try:
            window = self.dlg.child_window(title=title, control_type='Window')
            window.wait('visible', timeout=timeout)
            return window
        except Exception:
            raise PyWinAutoTimeoutError(f"창 '{title}'을(를) {timeout}초 내에 찾을 수 없습니다.")

    def _wait_for_condition(self, condition: Callable[[], bool], timeout: float = 10.0, interval: float = 0.1) -> bool:
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
            except Exception:
                pass
            time.sleep(interval)
        return False

    @handle_connection_error("공문 처리기 연결", logger)
    def _connect_to_window(self, max_attempts: int = 10, wait_time: int = 5) -> None:
        """
        접수 또는 전자결재 창에 연결을 시도합니다.

        Args:
            max_attempts (int): 최대 시도 횟수.
            wait_time (int): 각 시도 사이의 대기 시간 (초).
        Raises:
            PyWinAutoTimeoutError: 지정된 창을 찾지 못한 경우.
        """
        window_titles = [("^접수", "접수"), ("^전자결재", "전자결재")]
        
        for title_pattern, display_name in window_titles:
            try:
                self.app.connect(title_re=title_pattern)
                self.dlg = self.app.top_window()
                # 창이 실제로 준비될 때까지 대기
                self.dlg.wait('ready', timeout=10)
                logger.info(f"{display_name} 창에 연결되었습니다.")
                return
            except (ElementNotFoundError, PyWinAutoTimeoutError):
                continue
                
        raise PyWinAutoTimeoutError("공문 처리기를 찾을 수 없습니다.")

    def add_share(self, share_name: str) -> None:
        """
        공람 그룹에 지정된 이름을 추가합니다.

        Args:
            share_name (str): 추가할 공람 대상자의 이름.
        """
        if self.dlg:
            self.dlg['공람지정'].click()
            self.dlg['공람그룹'].select()
            self.dlg[share_name].select()
            self.dlg['▶ 추가'].click()
            self.dlg['확인'].click()
        else:
            logger.error("대상 창이 연결되어 있지 않습니다.")

    def approval(self, approval_name: str) -> None:
        """
        결재선을 설정합니다.

        Args:
            approval_name (str): 결재선 이름.
        """
        if self.dlg:
            try:
                # 결재정보 창 열기
                info_window_spec = self.dlg.child_window(title='결재정보', control_type='Window')
                if not info_window_spec.exists():
                    self.dlg['결재정보'].click()
                    info_window_spec.wait('visible', timeout=10)

                # 결재선 선택
                approval_selector = self.dlg['결재선']
                approval_selector.select()
                approval_selector.wait('enabled', timeout=5)
                
                keyboard.send_keys('{TAB 5}')
                pyperclip.copy(approval_name)
                keyboard.send_keys('^v{DOWN}')
                
                # 확인 버튼 클릭
                confirm_btn = self.dlg['확인']
                confirm_btn.wait('enabled', timeout=5)
                confirm_btn.click()
                
            except (PyWinAutoTimeoutError, ElementNotFoundError) as e:
                logger.error(f"결재선 설정 중 오류 발생: {e}")
        else:
            logger.error("대상 창이 연결되어 있지 않습니다.")

    def reception(self) -> None:
        """
        접수 버튼을 클릭하여 문서를 접수합니다.
        """
        if self.dlg:
            self.dlg['접수'].click()
            
            # 확인 버튼이 나타날 때까지 대기하고 클릭
            confirm_btn = self.dlg['확인2']
            confirm_btn.wait('enabled', timeout=10)
            confirm_btn.click()
        else:
            logger.error("대상 창이 연결되어 있지 않습니다.")

    def get_official_title(self) -> str:
        """
        공문의 제목을 반환합니다.

        Returns:
            str: 공문 제목.
        """
        if self.dlg:
            texts = self.dlg.texts()
            return texts[0] if texts else ""
        logger.error("대상 창이 연결되어 있지 않습니다.")
        return ""

    def save_pc(self) -> None:
        """
        PC 저장 기능을 수행합니다.
        """
        if self.dlg:
            self.dlg['PC저장'].click()
            
            # HSATTACHBAR_CONTROL 패널이 나타날 때까지 대기
            pane_exists = self._wait_for_condition(
                lambda: self.dlg.child_window(
                    title="HSATTACHBAR_CONTROL", auto_id="4", control_type="Pane"
                ).exists()
            )
            
            if pane_exists:
                if self._wait_for_element(lambda: self.dlg['본문 + 붙임']):
                    self.dlg['본문 + 붙임'].click()
                    if self._wait_for_element(lambda: self.dlg['확인']):
                        self.dlg['확인'].click()

            # 저장 대화상자가 준비될 때까지 대기
            keyboard.send_keys('{TAB}')
            keyboard.send_keys('{DOWN 4}')
            keyboard.send_keys('{ENTER}')
            keyboard.send_keys('{TAB 8}')
            keyboard.send_keys('{DOWN 1}')
            keyboard.send_keys('{ENTER}')
            keyboard.send_keys('%S')
            
            # 저장 완료 후 확인 버튼이 나타날 때까지 대기
            if self._wait_for_element(lambda: self.dlg['확인']):
                self.dlg['확인'].click()
        else:
            logger.error("대상 창이 연결되어 있지 않습니다.")

    def document_sort(self, document_group_name: str) -> None:
        """
        문서 분류 과정을 실행합니다.

        Args:
            document_group_name (str): 선택할 문서 그룹 이름.
        """
        if self.dlg:
            info_window = self.dlg.child_window(
                title='결재정보', control_type='Window')
            if not info_window.exists():
                self.dlg['결재정보'].click()
                self._wait_for_window('결재정보')

            info_window = self._wait_for_window('결재정보')
            info_window.set_focus()

            keyboard.send_keys('{TAB 3}')
            keyboard.send_keys('{SPACE}')
            
            # '과제카드 선택' 다이얼로그가 나타날 때까지 대기
            dialog = self._wait_for_window("과제카드 선택")
            dialog_rect = dialog.rectangle()
            mouse.click(coords=(dialog_rect.right - 20, dialog_rect.top + 50))

            keyboard.send_keys('{TAB 2}')
            pyperclip.copy(document_group_name)
            keyboard.send_keys('^v')
            keyboard.send_keys('{ENTER}')
            
            # 검색 결과가 나타날 때까지 잠시 대기
            self._wait_for_condition(lambda: True, timeout=1.0)

            keyboard.send_keys('{TAB}')
            keyboard.send_keys('{SPACE}')
            keyboard.send_keys('{TAB 3}')
            keyboard.send_keys('{ENTER}')
            
            # 선택 완료 대기
            self._wait_for_condition(lambda: True, timeout=1.0)
            keyboard.send_keys('{ENTER}')

            # 결재 버튼이 클릭 가능해질 때까지 대기
            if self._wait_for_element(lambda: self.dlg['결재']):
                self.dlg['결재'].click()
                keyboard.send_keys('{ENTER}')

            # 확인 창 처리
            confirm_exists = self._wait_for_condition(
                lambda: self.dlg.child_window(title='확인', control_type='Window').exists(),
                timeout=2.0
            )
            
            if not confirm_exists:
                if self._wait_for_element(lambda: self.dlg['예(Y)']):
                    self.dlg['예(Y)'].click()

            logger.info("문서 분류 처리 완료")
        else:
            logger.error("대상 창이 연결되어 있지 않습니다.")

    def check_end_collecting(self) -> bool:
        """
        정리가 끝났는지 확인합니다. (다이얼 버튼 확인)

        Returns:
            bool: 정리가 끝났으면 True, 아니면 False 반환
        """
        try:
            if self.dlg.child_window(title='확인', control_type='Window').exists():
                self.dlg['예(Y)'].click()
                return True
            return False
        except (AttributeError, RuntimeError):  # 구체적인 예외 타입 지정
            return False
        except (findwindows.ElementNotFoundError) as e:
            return True
        except Exception as e:
            return True


if __name__ == '__main__':
    officialCollector = OfficialCollector()
    officialCollector.dlg.print_control_identifiers()
