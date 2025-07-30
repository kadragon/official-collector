"""CMD 창을 제어하기 위한 유틸리티 모듈."""

import sys
from typing import Optional

from pywinauto import Application
from pywinauto.findwindows import find_window, WindowNotFoundError
from pywinauto.base_wrapper import BaseWrapper
from utils.error_handler import setup_logger

logger = setup_logger(__name__)


class CommandExecutor:
    def __init__(self) -> None:
        self.app: Optional[Application] = None
        self.dlg: Optional[BaseWrapper] = None
        self._connect_cmd_window()

    def _connect_cmd_window(self) -> None:
        """
        'C:'로 시작하는 제목을 가진 CMD 창을 찾아 연결합니다.
        연결 실패 시 에러 로그 출력하지만 계속 진행합니다.
        """
        try:
            handle = find_window(title_re="^C:")
            self.app = Application().connect(handle=handle)
            self.dlg = self.app.window(handle=handle)
            logger.info("CMD 창에 연결되었습니다.")
        except WindowNotFoundError:
            logger.error("CMD 창을 찾을 수 없습니다. 'cmd'로 실행 후 다시 시도하세요.")
            # CMD 창이 없어도 계속 진행
            self.app = None
            self.dlg = None
        except Exception as e:
            logger.exception("CMD 창 연결 중 오류 발생: %s", e)
            self.app = None
            self.dlg = None

    def activate(self) -> None:
        """CMD 창에 포커스를 줍니다."""
        if not self.dlg:
            logger.warning("CMD 창이 연결되어 있지 않습니다.")
            return

        try:
            self.dlg.set_focus()
        except Exception as e:
            logger.exception("CMD 창 포커스 실패: %s", e)
