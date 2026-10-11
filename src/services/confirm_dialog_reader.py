"""Confirmation-window discovery and text extraction, independent of workflows."""

# Trace: backlog.md - Task-card selection and confirmation fast pass

import io
import sys
import time
import _ctypes
from typing import Any, Callable

from pywinauto import Desktop
from pywinauto.findwindows import ElementNotFoundError

from config import TimeoutConfig, UIConfig
from utils.error_handler import setup_logger
from utils.wait_helpers import wait_for_poll_interval

logger = setup_logger(__name__)


class ConfirmDialogReader:
    """Read confirmation windows without choosing or executing workflow actions."""

    def __init__(self, dlg: Any) -> None:
        self.dlg = dlg

    def find_confirm_dialog(self) -> Any:
        """
        초고속 확인 대화상자 찾기 - 성능 최적화된 버전.

        Returns:
            Any: 확인 대화상자 객체, 없으면 None
        """
        logger.debug("확인 대화상자 초고속 검색 시작")

        # 방법 1: 즉시 존재 여부 확인 (대기 없음)
        try:
            dialog = self.dlg.child_window(title="확인", control_type="Window")
            if dialog.exists():
                logger.debug("즉시 확인 대화상자 발견")
                return dialog
        except Exception as e:
            logger.debug("즉시 확인 실패: %s", e)

        # 방법 2: 짧은 대기시간으로 재시도
        try:
            if self._wait_for_dialog_condition(
                lambda: self.dlg.child_window(
                    title="확인", control_type="Window"
                ).exists(),
                timeout=TimeoutConfig.FAST_DIALOG_IMMEDIATE,
                interval=TimeoutConfig.FAST_DIALOG_INTERVAL,
            ):
                dialog = self.dlg.child_window(title="확인", control_type="Window")
                logger.debug("짧은 대기 후 확인 대화상자 발견")
                return dialog
        except Exception as e:
            logger.debug("짧은 대기 방법 실패: %s", e)

        # 방법 3: Desktop에서 매우 짧게 찾기 (백업)
        try:
            desktop = Desktop(backend="uia")
            desktop_dialog = desktop.window(title="확인", class_name="#32770")
            if desktop_dialog.exists():
                logger.debug("Desktop에서 즉시 확인 대화상자 발견")
                return desktop_dialog
        except Exception as e:
            logger.debug("Desktop 즉시 확인 실패: %s", e)

        logger.debug("초고속 방법으로 확인 대화상자를 찾지 못함")
        return None

    def _wait_for_dialog_condition(
        self, condition: Callable, timeout: float, interval: float
    ) -> bool:
        """
        대화상자 조건을 확인합니다 (간소화 버전).

        Args:
            condition: 확인할 조건 함수
            timeout: 최대 대기 시간
            interval: 확인 간격

        Returns:
            bool: 조건 만족 여부
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if condition():
                    return True
            except Exception as e:
                logger.debug("조건 확인 중 오류: %s", e)
            wait_for_poll_interval(interval)
        return False

    def analyze_dialog_content(self, confirm_dialog: Any) -> str:
        """
        대화상자의 모든 텍스트 내용을 분석합니다.

        Args:
            confirm_dialog: 분석할 대화상자 객체

        Returns:
            str: 대화상자의 전체 텍스트 내용
        """
        try:
            # 모든 Static 컨트롤에서 텍스트 수집
            static_texts = []
            try:
                static_controls = confirm_dialog.children(class_name="Static")
                for control in static_controls:
                    try:
                        text = control.window_text().strip()
                        if text:  # 빈 텍스트 제외
                            static_texts.append(text)
                    except Exception as exc:
                        logger.debug("Static control text read failed: %s", exc)
                        continue
            except Exception as e:
                logger.debug("Static 컨트롤 수집 실패: %s", e)

            # 전체 대화상자 텍스트도 시도
            try:
                full_text = confirm_dialog.window_text()
                if full_text:
                    static_texts.append(full_text)
            except Exception as exc:
                logger.debug("Confirm dialog full text read failed: %s", exc)

            # 수집된 모든 텍스트 로그 출력
            combined_text = " | ".join(static_texts)
            logger.debug("대화상자 텍스트 내용: %s", static_texts)
            return combined_text

        except Exception as e:
            logger.warning("대화상자 내용 분석 실패: %s", e)
            return ""

    def get_quick_dialog_text(self, confirm_dialog: Any) -> str:
        """Read a body once, skipping the caption and stopping on known messages."""
        try:
            text = str(confirm_dialog.window_text() or "").strip()
            if text and text != UIConfig.CONFIRM_BUTTON:
                return text
            parts = []
            # UIA child wrappers have no exists(); read each directly.
            for control in confirm_dialog.children(control_type="Text"):
                try:
                    body = str(control.window_text() or "").strip()
                except (
                    ElementNotFoundError,
                    AttributeError,
                    RuntimeError,
                    OSError,
                    _ctypes.COMError,
                ) as error:
                    logger.debug("Confirmation child read failed: %s", error)
                    continue
                if body and body != UIConfig.CONFIRM_BUTTON and body not in parts:
                    parts.append(body)
                    if any(
                        pattern in body for pattern in UIConfig.CONFIRM_BODY_PATTERNS
                    ):
                        return body
            return " ".join(parts)
        except (
            ElementNotFoundError,
            AttributeError,
            RuntimeError,
            OSError,
            _ctypes.COMError,
        ) as error:
            logger.debug("Quick confirmation body read failed: %s", error)
            return ""

    def get_confirm_dialog_text(self) -> str:
        """
        확인 대화상자의 텍스트 내용을 가져옵니다.

        Returns:
            str: 대화상자의 텍스트 내용
        """
        try:
            confirm_window = self.dlg.child_window(title="확인", control_type="Window")
            if confirm_window.exists():
                # 대화상자 내의 모든 텍스트를 수집
                texts = confirm_window.texts()
                all_text = " ".join(texts) if texts else ""
                # Static 컨트롤에서도 텍스트 수집 시도
                try:
                    static_controls = confirm_window.children(control_type="Text")
                    for control in static_controls:
                        control_text = control.window_text()
                        if control_text and control_text not in all_text:
                            all_text += " " + control_text
                except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                    logger.debug("Static 컨트롤에서 텍스트 수집 실패: %s", e)
                except Exception as e:
                    logger.warning(
                        "Static 컨트롤 텍스트 수집 중 예상치 못한 오류: %s", e
                    )
                # Edit 컨트롤에서도 텍스트 수집 시도
                try:
                    edit_controls = confirm_window.children(control_type="Edit")
                    for control in edit_controls:
                        control_text = control.window_text()
                        if control_text and control_text not in all_text:
                            all_text += " " + control_text
                except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                    logger.debug("Edit 컨트롤에서 텍스트 수집 실패: %s", e)
                except Exception as e:
                    logger.warning("Edit 컨트롤 텍스트 수집 중 예상치 못한 오류: %s", e)
                logger.debug("대화상자에서 수집된 전체 텍스트: '%s'", all_text)
                return all_text
            return ""
        except Exception as e:
            logger.debug("확인 대화상자 텍스트 가져오기 실패: %s", e)
            return ""

    def get_detailed_dialog_text(self) -> str:
        """
        확인 대화상자의 상세 텍스트를 다양한 방법으로 수집합니다.

        Returns:
            str: 대화상자의 상세 텍스트 내용
        """
        try:
            confirm_window = self.dlg.child_window(title="확인", control_type="Window")
            if not confirm_window.exists():
                return ""
            all_texts = []
            # 모든 자식 컨트롤 순회
            try:
                children = confirm_window.children()
                for child in children:
                    try:
                        text = child.window_text()
                        if (
                            text
                            and text.strip()
                            and text != "확인"
                            and text not in all_texts
                        ):
                            all_texts.append(text.strip())
                    except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                        logger.debug("자식 컨트롤 텍스트 읽기 실패: %s", e)
                        continue
                    except Exception as e:
                        logger.warning("자식 컨트롤 처리 중 예상치 못한 오류: %s", e)
                        continue
            except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                logger.debug("자식 컨트롤 목록 조회 실패: %s", e)
            except Exception as e:
                logger.warning("자식 컨트롤 순회 중 예상치 못한 오류: %s", e)
            # Print control identifiers for debugging (only if no text found)
            if not all_texts:
                try:
                    logger.debug("확인 창 컨트롤 구조 분석 중...")
                    # 컨트롤 구조를 문자열로 캡처
                    old_stdout = sys.stdout
                    sys.stdout = mystdout = io.StringIO()
                    try:
                        confirm_window.print_control_identifiers()
                        control_info = mystdout.getvalue()
                        # 처음 500자만 로깅
                        logger.debug("컨트롤 정보: %s", control_info[:500])
                    finally:
                        sys.stdout = old_stdout
                except (ElementNotFoundError, AttributeError, RuntimeError) as e:
                    logger.debug("컨트롤 구조 분석 실패: %s", e)
                except Exception as e:
                    logger.warning("컨트롤 구조 분석 중 예상치 못한 오류: %s", e)
            result = " ".join(all_texts)
            logger.debug("상세 텍스트 수집 결과: '%s'", result)
            return result
        except Exception as e:
            logger.debug("상세 대화상자 텍스트 가져오기 실패: %s", e)
            return ""
