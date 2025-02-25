"""CMD 창을 제어하기 위한 유틸리티 모듈."""

import sys
import logging
from typing import Optional

from pywinauto import Application
from pywinauto.findwindows import find_window, WindowNotFoundError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CmdControl:
    """
    CMD 창 제어를 위한 클래스.
    """

    def __init__(self) -> None:
        """
        CmdControl 인스턴스를 초기화하고 CMD 창에 연결을 시도합니다.
        """
        self.app: Optional[Application] = None
        self.dlg: Optional[Application.window] = None
        self.find_and_connect()

    def find_and_connect(self) -> None:
        """
        CMD 창의 핸들을 찾아 pywinauto Application에 연결합니다.
        창을 찾지 못하면 에러 메시지를 기록하고 프로그램을 종료합니다.
        """
        try:
            handle = find_window(title_re="^C:")
            self.app = Application().connect(handle=handle)
            self.dlg = self.app.top_window()
        except WindowNotFoundError:
            logger.error("제어 창이 없습니다. cmd를 통해서 실행해주세요.")
            sys.exit(1)

    def activate(self) -> None:
        """
        연결된 CMD 창에 포커스를 설정합니다.
        창이 연결되지 않았다면 경고 메시지를 기록합니다.
        """
        if self.dlg:
            self.dlg.set_focus()
        else:
            logger.warning("창이 연결되지 않았습니다.")
