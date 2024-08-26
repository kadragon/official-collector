import sys
from typing import Optional

from pywinauto import Application
from pywinauto.findwindows import find_window, WindowNotFoundError


class CmdControl:
    def __init__(self):
        self.app: Optional[Application] = None
        self.dlg: Optional[Application.window] = None
        self.find_and_connect()

    def find_and_connect(self) -> None:
        try:
            handle = find_window(title_re="^C:")
            self.app = Application().connect(handle=handle)
            self.dlg = self.app.top_window()
        except WindowNotFoundError:
            print("제어 창이 없습니다. cmd를 통해서 실행해주세요.")
            sys.exit(1)

    def activate(self) -> None:
        if self.dlg:
            self.dlg.set_focus()
        else:
            print("창이 연결되지 않았습니다.")


def main() -> None:
    cmd = CmdControl()
    cmd.activate()


if __name__ == '__main__':
    main()
