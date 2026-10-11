# Trace: backlog.md - Final handler task-card completion
"""Capture user selection from the complete client unit-task-card chooser."""

from typing import Any, Optional
from pywinauto import Desktop
from config import UIConfig, TimeoutConfig
from ui.rich_console import RichConsole
from utils.timed_input import get_timed_input
from utils.error_handler import setup_logger, handle_pywinauto_error
from utils.performance_logger import log_execution_time

logger = setup_logger(__name__)
console = RichConsole()


class TaskCardHandler:
    """Read back the chosen card; never infer it from the recommendation."""

    @log_execution_time(logger)
    @handle_pywinauto_error("Final task-card capture", logger, default_return=None)
    def capture(self, collector: Any, recommendation: Optional[str]) -> Optional[str]:
        original_title = collector.dlg.window_text()
        if not collector.window_manager.ensure_payment_info_window():
            return None
        process = collector.app.process
        desktop = Desktop(backend="win32")
        chooser = desktop.window(title=UIConfig.TASK_CARD_DIALOG_TITLE, process=process)
        info = desktop.window(title=UIConfig.PAYMENT_INFO_TITLE, process=process)
        if not chooser.exists():
            collector.dlg.child_window(
                title=UIConfig.DOCUMENT_INFO_TAB_TITLE, control_type="TabItem"
            ).select()
            info.child_window(
                control_id=UIConfig.TASK_CARD_SELECT_ID,
                class_name="Button",
                visible_only=True,
            ).click()
        chooser.wait("visible", timeout=TimeoutConfig.WINDOW_READY)
        if recommendation:
            console.print_info(f"DB 추천 과제카드: {recommendation}")
        else:
            console.print_info("DB 추천 없음. 전체 단위과제카드에서 선택하세요")
        console.print_info(
            "과제카드 선택 창에서 선택 후 확인. 문서정보 확인은 누르지 말고 콘솔에서 Enter 입력"
        )
        if (
            get_timed_input(
                "과제카드 선택 완료 후 Enter (Esc: 중단)",
                timeout=TimeoutConfig.USER_SELECTION_WAIT,
            )
            is None
        ):
            logger.warning("Task-card selection cancelled or timed out")
            return None
        if chooser.exists() or collector.dlg.window_text() != original_title:
            logger.warning("Task-card chooser still open or document changed")
            return None
        selected = (
            info.child_window(
                control_id=UIConfig.TASK_CARD_FIELD_ID, class_name="ComboBox"
            )
            .window_text()
            .strip()
        )
        if not selected:
            logger.warning("Selected task-card field is empty")
            return None
        window = info.wrapper_object()
        info.child_window(control_id=1, class_name="Button", visible_only=True).click()
        if not collector._wait_for_condition(
            lambda: not window.is_visible() and collector.dlg.is_enabled(),
            timeout=TimeoutConfig.WINDOW_READY,
        ):
            logger.warning("Task-card information save unverified")
            return None
        if collector.dlg.window_text() != original_title:
            logger.warning("Document changed during task-card information save")
            return None
        return str(selected)
