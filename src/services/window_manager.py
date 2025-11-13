"""
Window connection and management module for official document automation.
Handles window detection, connection, and state management.
"""

import time
from typing import Any
import win32gui
from pywinauto import findwindows
from pywinauto.timings import TimeoutError as PyWinAutoTimeoutError
from pywinauto.findwindows import ElementNotFoundError

from config import UIConfig, TimeoutConfig
from utils.error_handler import setup_logger, handle_connection_error
from utils.performance_logger import log_execution_time

logger = setup_logger(__name__)


class WindowManager:
    """Manages window connections and state for the official document automation system."""

    def __init__(self, app: Any, dlg: Any) -> None:
        """
        Initialize the WindowManager.

        Args:
            app: pywinauto Application instance
            dlg: Main dialog window reference
        """
        self.app = app
        self.dlg = dlg

    @handle_connection_error("공문 처리기 연결", logger)
    def connect_to_window(
        self, max_attempts: int = 10, wait_time: int = 2, debug_mode: bool = False
    ) -> None:
        """
        접수 또는 전자결재 창에 연결을 시도합니다.

        Args:
            max_attempts (int): 최대 시도 횟수.
            wait_time (int): 각 시도 사이의 대기 시간 (초).
            debug_mode (bool): 디버그 모드 - 창 목록 상세 로깅 여부.

        Raises:
            PyWinAutoTimeoutError: 지정된 창을 찾지 못한 경우.
        """
        window_titles = UIConfig.WINDOW_TITLE_PATTERNS

        # 디버그 모드일 때만 창 목록 상세 로깅 (성능 최적화)
        if debug_mode:
            try:
                available_windows = findwindows.find_windows()
                logger.info("사용 가능한 창 개수: %s", len(available_windows))
                for hwnd in available_windows[:5]:  # 처음 5개만 로깅
                    try:
                        title = win32gui.GetWindowText(hwnd)
                        if title and ("접수" in title or "전자결재" in title):
                            logger.info("발견된 관련 창: '%s'", title)
                    except (OSError, RuntimeError) as e:
                        logger.debug("창 제목 조회 실패 (hwnd: %s): %s", hwnd, e)
                    except Exception as e:
                        logger.warning(
                            "창 제목 조회 중 예상치 못한 오류 (hwnd: %s): %s", hwnd, e
                        )
            except Exception as e:
                logger.warning("창 목록 조회 중 오류: %s", e)

        for title_pattern, display_name in window_titles:
            try:
                logger.info(
                    "%s 창 연결 시도 중... (패턴: %s)", display_name, title_pattern
                )
                self.app.connect(title_re=title_pattern)
                self.dlg = self.app.top_window()
                actual_title = self.dlg.window_text()
                logger.info(
                    "%s 창에 연결되었습니다. 실제 제목: '%s'",
                    display_name,
                    actual_title,
                )
                # 창이 실제로 준비될 때까지 대기 (최적화된 타임아웃)
                try:
                    self.dlg.wait("ready", timeout=TimeoutConfig.WINDOW_READY)
                    logger.debug("%s 창이 준비 상태입니다.", display_name)
                except PyWinAutoTimeoutError:
                    logger.debug(
                        "%s 창 준비 대기 타임아웃, 하지만 연결은 성공했습니다.",
                        display_name,
                    )
                    # 창이 연결되었으므로 계속 진행
                return
            except (ElementNotFoundError, PyWinAutoTimeoutError) as e:
                logger.warning("%s 창 연결 실패: %s", display_name, e)
                continue
        raise PyWinAutoTimeoutError("공문 처리기를 찾을 수 없습니다.")

    def wait_for_window(
        self, title: str, timeout: float = TimeoutConfig.WINDOW_WAIT
    ) -> Any:
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
            window = self.dlg.child_window(title=title, control_type="Window")
            if window is None:
                raise PyWinAutoTimeoutError(f"창 '{title}'을(를) 찾을 수 없습니다.")
            window.wait("visible", timeout=timeout)
            return window
        except Exception:
            raise PyWinAutoTimeoutError(
                f"창 '{title}'을(를) {timeout}초 내에 찾을 수 없습니다."
            )

    @log_execution_time(logger)
    def ensure_payment_info_window(self) -> bool:
        """
        결재정보 창이 표시되어 있는지 확인하고, 없으면 열어줍니다.

        Returns:
            bool: 결재정보 창이 성공적으로 표시되었으면 True, 실패하면 False
        """
        try:
            # 결재정보 창이 이미 열려있는지 확인
            info_window_spec = self.dlg.child_window(
                title="결재정보", control_type="Window"
            )
            if info_window_spec.exists():
                logger.debug("결재정보 창이 이미 열려있습니다.")
                return True
            # 결재정보 창이 없으면 결재정보 버튼 클릭
            logger.info("결재정보 창이 표시되지 않음 - 결재정보 버튼 클릭")
            payment_info_buttons = UIConfig.PAYMENT_INFO_BUTTONS
            for button_name in payment_info_buttons:
                try:
                    button = self.dlg[button_name]
                    if button.exists() and button.is_enabled():
                        logger.info("'%s' 버튼 클릭하여 결재정보 창 열기", button_name)
                        button.click()
                        # 창이 열릴 때까지 대기
                        if info_window_spec.wait(
                            "visible", timeout=TimeoutConfig.PAYMENT_INFO_WINDOW
                        ):
                            logger.info("결재정보 창이 성공적으로 열렸습니다.")
                            return True
                        else:
                            logger.warning("결재정보 창 열기 타임아웃")
                            return False
                except (ElementNotFoundError, PyWinAutoTimeoutError) as e:
                    logger.debug("'%s' 버튼 클릭 실패: %s", button_name, e)
                    continue
                except Exception as e:
                    logger.warning(
                        "'%s' 버튼 클릭 중 예상치 못한 오류: %s", button_name, e
                    )
                    continue
            logger.error("결재정보 버튼을 찾을 수 없거나 클릭할 수 없습니다.")
            return False
        except Exception as e:
            logger.error("결재정보 창 확인 중 오류 발생: %s", e)
            return False
