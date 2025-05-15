"""CMD 창을 제어하기 위한 유틸리티 모듈."""

import sys
import logging
from typing import Optional

from pywinauto import Application
from pywinauto.findwindows import find_window, WindowNotFoundError
from pywinauto.base_wrapper import BaseWrapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CmdControl:
    def __init__(self) -> None:
        self.app: Optional[Application] = None
        self.dlg: Optional[BaseWrapper] = None
        self._connect_cmd_window()

    def _connect_cmd_window(self) -> None:
        """
        'C:'로 시작하는 제목을 가진 CMD 창을 찾아 연결합니다.
        연결 실패 시 에러 로그 출력 후 종료합니다.
        """
        try:
            handle = find_window(title_re="^C:")
            self.app = Application().connect(handle=handle)
            self.dlg = self.app.window(handle=handle)
        except WindowNotFoundError:
            logger.error("CMD 창을 찾을 수 없습니다. 'cmd'로 실행 후 다시 시도하세요.")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"CMD 창 연결 중 오류 발생: {e}")
            sys.exit(1)

    def activate(self) -> None:
        """CMD 창에 포커스를 줍니다."""
        if not self.dlg:
            logger.warning("CMD 창이 연결되어 있지 않습니다.")
            return

        try:
            self.dlg.set_focus()
        except Exception as e:
            logger.exception(f"CMD 창 포커스 실패: {e}")
