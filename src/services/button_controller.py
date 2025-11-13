"""
Button controller module for official document automation.
Handles all button click operations with unified logic.
"""

import time
from typing import Any
from pywinauto import keyboard

from config import UIConfig, TimeoutConfig
from utils.error_handler import setup_logger

logger = setup_logger(__name__)


class ButtonController:
    """Manages button click operations for the official document automation system."""

    def __init__(self, dlg: Any) -> None:
        """
        Initialize the ButtonController.

        Args:
            dlg: Main dialog window reference
        """
        self.dlg = dlg

    def click_dialog_button_unified(
        self, button_type: str = "confirm", confirm_dialog: Any = None
    ) -> bool:
        """
        대화상자에서 버튼을 클릭하는 통합 메서드.

        Args:
            button_type: 클릭할 버튼 유형 ("confirm" 또는 "cancel")
            confirm_dialog: 특정 대화상자 객체 (None이면 자동 탐색)

        Returns:
            bool: 버튼 클릭 성공 여부
        """
        # 버튼 패턴 가져오기
        button_patterns = UIConfig.DIALOG_BUTTON_PATTERNS.get(button_type, [])
        if not button_patterns:
            logger.warning("알 수 없는 버튼 유형: %s", button_type)
            return False

        # 대화상자 확인
        target_dialog = confirm_dialog
        if target_dialog is None:
            try:
                target_dialog = self.dlg.child_window(
                    title="확인", control_type="Window"
                )
                if not target_dialog.exists():
                    logger.debug("확인 창이 존재하지 않음 - 버튼 클릭 시도 생략")
                    return True  # 창이 없으면 성공으로 간주
            except Exception as e:
                logger.debug("확인 창 존재 여부 확인 실패: %s", e)
                return True

        # 버튼 패턴으로 클릭 시도
        for title, class_name in button_patterns:
            # 먼저 대화상자에서 찾기
            if target_dialog:
                try:
                    button = target_dialog.child_window(
                        title=title, class_name=class_name
                    )
                    if button.exists() and button.is_enabled():
                        button.click()
                        logger.debug("%s 버튼 클릭 완료 (버튼: %s)", button_type, title)
                        return True
                except Exception as e:
                    logger.debug(
                        "대화상자에서 버튼 찾기 실패 (%s/%s): %s", button_type, title, e
                    )

            # 메인 다이얼로그에서도 시도
            try:
                button = self.dlg.child_window(title=title, class_name=class_name)
                if button.exists() and button.is_enabled():
                    button.click()
                    logger.debug(
                        "메인 창에서 %s 버튼 클릭 완료 (버튼: %s)", button_type, title
                    )
                    return True
            except Exception as e:
                logger.debug("메인 창에서 버튼 찾기 실패 (%s/%s): %s", button_type, title, e)

        # 버튼을 찾지 못한 경우 키보드로 시도
        try:
            if button_type == "confirm":
                logger.debug("버튼을 찾지 못해 키보드로 시도 (%s)", button_type)
                keyboard.send_keys("y")
                time.sleep(TimeoutConfig.MINIMAL_DELAY)
            else:
                logger.debug("버튼을 찾지 못해 키보드 ESC로 시도 (%s)", button_type)
                keyboard.send_keys("{ESC}")
                time.sleep(TimeoutConfig.MINIMAL_DELAY)
            return True
        except Exception as e:
            logger.warning("%s 버튼 클릭 실패, 키보드로 재시도: %s", button_type, e)
            try:
                keyboard.send_keys("{ENTER}")
                time.sleep(TimeoutConfig.SHORT_DELAY)
                return True
            except Exception as ke:
                logger.error("키보드 입력도 실패 (%s): %s", button_type, ke)
                return False

    def click_cancel_button(self) -> bool:
        """
        대화상자에서 취소 버튼을 클릭합니다.

        Returns:
            bool: 취소 버튼 클릭 성공 여부
        """
        return self.click_dialog_button_unified("cancel")

    def click_confirm_button(self) -> bool:
        """
        대화상자에서 확인 버튼을 클릭합니다.

        Returns:
            bool: 확인 버튼 클릭 성공 여부
        """
        return self.click_dialog_button_unified("confirm")

    def click_approval_button(self) -> bool:
        """
        결재 버튼을 클릭합니다.

        Returns:
            bool: 결재 버튼 클릭 성공 여부

        Raises:
            Exception: 결재 버튼을 찾을 수 없는 경우
        """
        try:
            button = self.dlg["결재"]
            if button.exists() and button.is_enabled():
                logger.info("결재 버튼 클릭")
                button.click()
                return True
            else:
                raise Exception("결재 버튼을 찾을 수 없습니다")
        except Exception as e:
            logger.error("결재 버튼 클릭 실패: %s", e)
            raise
