"""
공문 처리기를 제어하는 모듈.

pywinauto를 활용하여 전자결재 및 접수 창과 상호작용합니다.
"""

import time
import logging
from typing import Optional

from pywinauto import Application, keyboard, mouse, findwindows
from pywinauto.timings import TimeoutError as PyWinAutoTimeoutError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    def _connect_to_window(self, max_attempts: int = 10, wait_time: int = 5) -> None:
        """
        접수 또는 전자결재 창에 연결을 시도합니다.

        Args:
            max_attempts (int): 최대 시도 횟수.
            wait_time (int): 각 시도 사이의 대기 시간 (초).
        Raises:
            PyWinAutoTimeoutError: 지정된 창을 찾지 못한 경우.
        """
        for attempt in range(max_attempts):
            try:
                self.app.connect(title_re="^접수")
                self.dlg = self.app.top_window()
                logger.info("접수 창에 연결되었습니다.")
                return
            except findwindows.ElementNotFoundError:
                try:
                    self.app.connect(title_re="^전자결재")
                    self.dlg = self.app.top_window()
                    logger.info("전자결재 창에 연결되었습니다.")
                    return
                except findwindows.ElementNotFoundError:
                    logger.info("공문 처리기를 찾지 못했습니다. "
                                "실행을 기다리는 중입니다... (시도 %d/%d)", attempt + 1, max_attempts)
                    time.sleep(wait_time)

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
            info_window = self.dlg.child_window(title='결재정보', control_type='Window')
            if not info_window.exists():
                self.dlg['결재정보'].click()

            self.dlg['결재선'].select()
            time.sleep(0.5)
            keyboard.send_keys('{TAB 5}')
            keyboard.send_keys(approval_name)
            keyboard.send_keys('{DOWN}')
            self.dlg['확인'].click()
        else:
            logger.error("대상 창이 연결되어 있지 않습니다.")

    def reception(self) -> None:
        """
        접수 버튼을 클릭하여 문서를 접수합니다.
        """
        if self.dlg:
            self.dlg['접수'].click()
            time.sleep(0.5)
            self.dlg['확인2'].click()
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
            time.sleep(0.5)
            pane = self.dlg.child_window(
                title="HSATTACHBAR_CONTROL", auto_id="4", control_type="Pane"
            )
            if pane.exists():
                self.dlg['본문 + 붙임'].click()
                self.dlg['확인'].click()

            time.sleep(0.5)
            keyboard.send_keys('{TAB}')
            keyboard.send_keys('{DOWN 4}')
            keyboard.send_keys('{ENTER}')
            keyboard.send_keys('{TAB 8}')
            keyboard.send_keys('{DOWN 1}')
            keyboard.send_keys('{ENTER}')
            keyboard.send_keys('%S')
            time.sleep(0.5)
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
            info_window = self.dlg.child_window(title='결재정보', control_type='Window')
            if not info_window.exists():
                self.dlg['결재정보'].click()

            time.sleep(0.5)
            info_window.set_focus()

            keyboard.send_keys('{TAB 3}')
            keyboard.send_keys('{SPACE}')
            time.sleep(2)

            # '과제카드 선택' 다이얼로그 찾기
            dialog = self.dlg.child_window(title="과제카드 선택", control_type="Window")
            dialog_rect = dialog.rectangle()
            mouse.click(coords=(dialog_rect.right - 20, dialog_rect.top + 50))

            keyboard.send_keys('{TAB 2}')
            keyboard.send_keys(document_group_name)
            keyboard.send_keys('{ENTER}')
            time.sleep(0.5)

            keyboard.send_keys('{TAB}')
            keyboard.send_keys('{SPACE}')
            keyboard.send_keys('{TAB 3}')
            keyboard.send_keys('{ENTER}')
            time.sleep(0.5)
            keyboard.send_keys('{ENTER}')

            self.dlg['결재'].click()
            keyboard.send_keys('{ENTER}')

            confirm_window = self.dlg.child_window(title='확인', control_type='Window')
            if not confirm_window.exists():
                self.dlg['예(Y)'].click()

            logger.info("문서 분류 대기중...")
            time.sleep(2)
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

# if __name__ == '__main__':
    # officialCollector = OfficialCollector()
    # print_control_identifiers()
