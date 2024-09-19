import time
from typing import Optional
from pywinauto import Application, keyboard, findwindows, mouse
from pywinauto.timings import TimeoutError


class OfficialCollector:
    def __init__(self):
        self.app: Application = Application(backend="uia")
        self.dlg: Optional[Application.window] = None
        self._connect_to_window()

    def _connect_to_window(self, max_attempts: int = 12, wait_time: int = 5) -> None:
        for _ in range(max_attempts):
            try:
                self.app.connect(title_re="^접수")
                self.dlg = self.app.top_window()
                return
            except findwindows.ElementNotFoundError:
                try:
                    self.app.connect(title_re="^전자결재")
                    self.dlg = self.app.top_window()
                    return
                except findwindows.ElementNotFoundError:
                    print("공문 처리기가 없습니다.\n공문 처리기가 실행되기를 기다리는 중입니다.")
                    time.sleep(wait_time)

        raise TimeoutError("공문 처리기를 찾을 수 없습니다.")

    def add_share(self, share_name: str) -> None:
        self.dlg['공람지정'].click()
        self.dlg['공람그룹'].select()
        self.dlg[share_name].select()
        self.dlg['▶ 추가'].click()
        self.dlg['확인'].click()

    def approval(self, approval_name: str) -> None:
        if not self.dlg.child_window(title='결재정보', control_type='Window').exists():
            self.dlg['결재정보'].click()

        self.dlg['결재선'].select()
        time.sleep(0.5)
        keyboard.send_keys('{TAB 5}')
        keyboard.send_keys(approval_name)
        keyboard.send_keys('{DOWN}')
        self.dlg['확인'].click()

    def reception(self) -> None:
        self.dlg['접수'].click()
        time.sleep(0.5)
        self.dlg['확인2'].click()

    def get_official_title(self) -> str:
        return self.dlg.texts()[0]

    def save_pc(self) -> None:
        self.dlg['PC저장'].click()

        time.sleep(0.5)

        pane = self.dlg.child_window(
            title="HSATTACHBAR_CONTROL", auto_id="4", control_type="Pane")

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

    def document_sort(self, document_group_name):
        if not self.dlg.child_window(title='결재정보', control_type='Window').exists():
            self.dlg['결재정보'].click()

        time.sleep(0.5)

        self.dlg.child_window(title='결재정보', control_type='Window').set_focus()

        keyboard.send_keys('{TAB 3}')
        keyboard.send_keys('{SPACE}')

        time.sleep(2)

        # '과제카드 선택' 다이얼로그를 찾습니다.
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

        if not self.dlg.child_window(title='확인', control_type='Window').exists():
            self.dlg['예(Y)'].click()

        print('대기중')

        time.sleep(2)
        # self.dlg.print_control_identifiers()


if __name__ == '__main__':
    collector = OfficialCollector()
    collector.dlg.print_control_identifiers()
    # collector.save_pc()

    # collector.document_sort('일반서무')

    # for control in collector.dlg:
    #     print(control, "\n")

    # procs = findwindows.find_elements()
    # process_id = None
    # for p in procs:
    #     if p.class_name == "XSViewBMSWndClass":
    #         process_id = p.process_id

    # app = Application()
    # app.connect(process=process_id)
    # dlg = app.top_window()
    # # dlg.print_control_identifiers()
    # # print(dlg.texts())
    # for control in dlg.children():
    #     print(control.window_text())

    # if not dlg.child_window(title='결재정보', control_type='Window').exists():
    #     dlg['결재정보'].click()
