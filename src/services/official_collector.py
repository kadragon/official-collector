"""
공문 처리기를 제어하는 모듈.

pywinauto를 활용하여 전자결재 및 접수 창과 상호작용합니다.
"""

import time
from typing import Optional, Callable
from enum import Enum

import pyperclip
from pywinauto import Application, keyboard, mouse, findwindows
from pywinauto.timings import TimeoutError as PyWinAutoTimeoutError
from pywinauto.findwindows import ElementNotFoundError
from utils.error_handler import setup_logger, handle_connection_error

logger = setup_logger(__name__)

class DocumentFlowState(Enum):
    """문서 처리 흐름 상태를 나타내는 열거형"""
    CONTINUE = "continue"  # 다음 문서 처리 계속
    EXIT = "exit"  # 처리 종료
    UNKNOWN = "unknown"  # 알 수 없는 상태


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

    def _wait_for_element(self, element_selector: Callable,
                          timeout: float = 10.0, interval: float = 0.1) -> bool:
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
            raise PyWinAutoTimeoutError(
                f"창 '{title}'을(를) {timeout}초 내에 찾을 수 없습니다."
            )

    def _wait_for_condition(self, condition: Callable[[], bool],
                            timeout: float = 10.0, interval: float = 0.1) -> bool:
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

        # 현재 사용 가능한 창 목록을 로깅
        try:
            available_windows = findwindows.find_windows()
            logger.info("사용 가능한 창 개수: %s", len(available_windows))
            for hwnd in available_windows[:5]:  # 처음 5개만 로깅
                try:
                    title = findwindows.window_text(hwnd)
                    if title and ("접수" in title or "전자결재" in title):
                        logger.info("발견된 관련 창: '%s'", title)
                except:
                    pass
        except Exception as e:
            logger.warning("창 목록 조회 중 오류: %s", e)

        for title_pattern, display_name in window_titles:
            try:
                logger.info("%s 창 연결 시도 중... (패턴: %s)", display_name, title_pattern)
                self.app.connect(title_re=title_pattern)
                self.dlg = self.app.top_window()
                actual_title = self.dlg.window_text()
                logger.info("%s 창에 연결되었습니다. 실제 제목: '%s'", display_name, actual_title)
                # 창이 실제로 준비될 때까지 대기 (더 긴 타임아웃과 예외 처리)
                try:
                    self.dlg.wait('ready', timeout=5)
                    logger.info("%s 창이 준비 상태입니다.", display_name)
                except PyWinAutoTimeoutError:
                    logger.warning("%s 창 준비 대기 타임아웃, 하지만 연결은 성공했습니다.", display_name)
                    # 창이 연결되었으므로 계속 진행
                return
            except (ElementNotFoundError, PyWinAutoTimeoutError) as e:
                logger.warning("%s 창 연결 실패: %s", display_name, e)
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
                logger.error("결재선 설정 중 오류 발생: %s", e)
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

    def check_document_flow_state(self) -> DocumentFlowState:
        """
        현재 문서 처리 흐름 상태를 확인합니다.
        
        Returns:
            DocumentFlowState: 현재 문서 처리 상태
        """
        try:
            # 확인 창이 존재하는지 확인
            confirm_window = self.dlg.child_window(title='확인', control_type='Window')
            if not confirm_window.exists():
                return DocumentFlowState.CONTINUE
            
            # 창의 텍스트 내용을 확인하여 상태 결정
            window_text = self._get_confirm_dialog_text()
            
            if "다음 문서를 처리하겠습니다" in window_text:
                logger.info("다음 문서 처리 대화상자 감지")
                return DocumentFlowState.CONTINUE
            elif "종료하시겠습니까" in window_text:
                logger.info("종료 확인 대화상자 감지") 
                return DocumentFlowState.EXIT
            elif "다음" in window_text and "문서" in window_text:
                logger.info("다음 문서 관련 대화상자 감지 (부분 매칭)")
                return DocumentFlowState.CONTINUE
            elif "종료" in window_text or "끝" in window_text or "완료" in window_text:
                logger.info("종료 관련 대화상자 감지 (부분 매칭)")
                return DocumentFlowState.EXIT
            elif window_text.strip() == "확인" or not window_text.strip():
                # 텍스트를 충분히 읽지 못한 경우, 더 자세히 분석
                logger.warning("대화상자 텍스트가 불완전합니다. 더 상세한 분석을 시도합니다.")
                detailed_text = self._get_detailed_dialog_text()
                if detailed_text:
                    logger.info("상세 텍스트 발견: '%s'", detailed_text)
                    if "다음 문서를 처리하겠습니다" in detailed_text or "다음" in detailed_text:
                        return DocumentFlowState.CONTINUE
                    elif "종료하시겠습니다" in detailed_text or "종료" in detailed_text:
                        return DocumentFlowState.EXIT
                
                # 여전히 판단할 수 없는 경우 UNKNOWN으로 처리
                logger.warning("대화상자 내용을 판단할 수 없습니다")
                return DocumentFlowState.UNKNOWN
            else:
                logger.info("알 수 없는 확인 대화상자: '%s'", window_text)
                return DocumentFlowState.UNKNOWN
                
        except (AttributeError, RuntimeError, ElementNotFoundError) as e:
            logger.debug("문서 흐름 상태 확인 중 예외: %s", e)
            return DocumentFlowState.CONTINUE
        except Exception as e:
            logger.warning("예상치 못한 오류: %s", e)
            return DocumentFlowState.EXIT
    
    def _get_confirm_dialog_text(self) -> str:
        """
        확인 대화상자의 텍스트 내용을 가져옵니다.
        
        Returns:
            str: 대화상자의 텍스트 내용
        """
        try:
            confirm_window = self.dlg.child_window(title='확인', control_type='Window')
            if confirm_window.exists():
                # 대화상자 내의 모든 텍스트를 수집
                texts = confirm_window.texts()
                all_text = " ".join(texts) if texts else ""
                
                # Static 컨트롤에서도 텍스트 수집 시도
                try:
                    static_controls = confirm_window.children(control_type='Text')
                    for control in static_controls:
                        if control.exists():
                            control_text = control.window_text()
                            if control_text and control_text not in all_text:
                                all_text += " " + control_text
                except:
                    pass
                
                # Edit 컨트롤에서도 텍스트 수집 시도  
                try:
                    edit_controls = confirm_window.children(control_type='Edit')
                    for control in edit_controls:
                        if control.exists():
                            control_text = control.window_text()
                            if control_text and control_text not in all_text:
                                all_text += " " + control_text
                except:
                    pass
                
                logger.debug("대화상자에서 수집된 전체 텍스트: '%s'", all_text)
                return all_text
            return ""
        except Exception as e:
            logger.debug("확인 대화상자 텍스트 가져오기 실패: %s", e)
            return ""
    
    def _get_detailed_dialog_text(self) -> str:
        """
        확인 대화상자의 상세 텍스트를 다양한 방법으로 수집합니다.
        
        Returns:
            str: 대화상자의 상세 텍스트 내용
        """
        try:
            confirm_window = self.dlg.child_window(title='확인', control_type='Window')
            if not confirm_window.exists():
                return ""
            
            all_texts = []
            
            # 모든 자식 컨트롤 순회
            try:
                children = confirm_window.children()
                for child in children:
                    try:
                        text = child.window_text()
                        if text and text.strip() and text != '확인' and text not in all_texts:
                            all_texts.append(text.strip())
                    except:
                        continue
            except:
                pass
            
            # Print control identifiers for debugging (only if no text found)
            if not all_texts:
                try:
                    logger.debug("확인 창 컨트롤 구조 분석 중...")
                    # 컨트롤 구조를 문자열로 캡처
                    import io
                    import sys
                    old_stdout = sys.stdout
                    sys.stdout = mystdout = io.StringIO()
                    try:
                        confirm_window.print_control_identifiers()
                        control_info = mystdout.getvalue()
                        logger.debug("컨트롤 정보: %s", control_info[:500])  # 처음 500자만 로깅
                    finally:
                        sys.stdout = old_stdout
                except:
                    pass
            
            result = " ".join(all_texts)
            logger.debug("상세 텍스트 수집 결과: '%s'", result)
            return result
            
        except Exception as e:
            logger.debug("상세 대화상자 텍스트 가져오기 실패: %s", e)
            return ""
    
    def handle_document_flow_dialog(self, state: DocumentFlowState, auto_continue: bool = True) -> bool:
        """
        문서 처리 흐름 대화상자를 처리합니다.
        
        Args:
            state: 현재 문서 흐름 상태
            auto_continue: 자동으로 다음 문서 처리를 계속할지 여부
            
        Returns:
            bool: 처리 계속 여부 (True: 계속, False: 종료)
        """
        try:
            # 가능한 확인 버튼들을 순서대로 시도
            confirm_buttons = ['예(Y)', '확인', '예', 'OK']
            cancel_buttons = ['아니오(N)', '취소', '아니오', 'Cancel']
            
            if state == DocumentFlowState.CONTINUE:
                if auto_continue:
                    logger.info("자동으로 다음 문서 처리 계속")
                    return self._click_dialog_button(confirm_buttons)
                else:
                    # 사용자에게 선택 권한 제공
                    logger.info("다음 문서 처리 여부를 사용자가 결정")
                    return self._click_dialog_button(confirm_buttons)
                    
            elif state == DocumentFlowState.EXIT:
                logger.info("문서 처리 종료 확인")
                self._click_dialog_button(confirm_buttons)
                return False
                
            elif state == DocumentFlowState.UNKNOWN:
                logger.warning("알 수 없는 대화상자 - 기본 처리")
                self._click_dialog_button(confirm_buttons)
                return False
                
            return True
            
        except Exception as e:
            logger.error("문서 흐름 대화상자 처리 중 오류: %s", e)
            return False
    
    def _click_dialog_button(self, button_names: list) -> bool:
        """
        대화상자에서 사용 가능한 버튼을 찾아 클릭합니다.
        
        Args:
            button_names: 시도할 버튼 이름들의 리스트
            
        Returns:
            bool: 버튼 클릭 성공 여부
        """
        for button_name in button_names:
            try:
                button = self.dlg[button_name]
                if button.exists() and button.is_enabled():
                    logger.debug("버튼 '%s' 클릭", button_name)
                    button.click()
                    return True
            except Exception:
                continue
        
        logger.warning("사용 가능한 버튼을 찾을 수 없습니다: %s", button_names)
        return False
    
    def check_end_collecting(self) -> bool:
        """
        정리가 끝났는지 확인합니다. (이전 버전과의 호환성을 위한 메서드)
        
        Returns:
            bool: 정리가 끝났으면 True, 아니면 False 반환
        """
        state = self.check_document_flow_state()
        if state == DocumentFlowState.CONTINUE:
            return not self.handle_document_flow_dialog(state)
        elif state == DocumentFlowState.EXIT:
            return self.handle_document_flow_dialog(state)
        else:
            return self.handle_document_flow_dialog(state)


if __name__ == '__main__':
    officialCollector = OfficialCollector()
    officialCollector.dlg.print_control_identifiers()
