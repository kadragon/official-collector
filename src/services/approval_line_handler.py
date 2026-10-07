# Trace: backlog.md - Build 접수 approval line from org chart in predetermined order
"""
Approval-line builder driven by the org chart.

Replaces the preregistered 결재선 combo (OfficialCollector.approval), whose
entries vary per document, with deterministic org-chart selection:

1. Pick each person in the TreeView under their department node.
2. Click the add button to stage them in the approval ListView.
3. Move rows up until the staged order matches the predetermined order.
4. Click confirm to save.

Verified against the live client: the client prepends added rows, the
결재방법 column is assigned automatically, and the TreeView/ListView pair is
visible only through the win32 backend (uia shows just the tab shell).
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

from config import TimeoutConfig, UIConfig
from utils.error_handler import handle_pywinauto_error, setup_logger
from utils.performance_logger import log_execution_time

logger = setup_logger(__name__)


@dataclass(frozen=True)
class Approver:
    """One approval-line member.

    Attributes:
        department: Org-chart department node, e.g. "정보전산원".
        name: Person name, matched against the first token of the tree
            node text, e.g. "김승현" matches "김승현 정보전산원장".
    """

    department: str
    name: str


def match_node_text(node_texts: List[str], name: str) -> str:
    """Return the tree node text whose first token equals name.

    Raises:
        ValueError: No match, or more than one match (homonym).
    """
    hits = [text for text in node_texts if text.split() and text.split()[0] == name]
    if not hits:
        raise ValueError(f"조직도에서 찾을 수 없음: {name}")
    if len(hits) > 1:
        raise ValueError(f"조직도 동명이인: {name} ({hits})")
    return hits[0]


def plan_up_moves(current: List[str], target: List[str]) -> List[int]:
    """Plan select-and-move-up steps turning current order into target order.

    Each returned index is a ListView row to select and move up by one;
    applying them in sequence yields target. The client only offers an
    up button that moves the selected row, hence this shape.

    Raises:
        ValueError: Target has duplicates, or the two sets differ (only
            exact-set reorder is supported; adding/removing is separate).
    """
    if len(set(target)) != len(target):
        raise ValueError(f"중복된 승인자: {target}")
    if set(current) != set(target):
        missing = [name for name in target if name not in current]
        extra = [name for name in current if name not in target]
        raise ValueError(f"결재선 불일치 (미추가: {missing}, 여분: {extra})")
    moves: List[int] = []
    working = list(current)
    for position, want in enumerate(target):
        while working.index(want) != position:
            index = working.index(want)
            moves.append(index)
            working[index - 1], working[index] = working[index], working[index - 1]
    return moves


class ApprovalLineHandler:
    """Builds the approval ListView from org-chart nodes."""

    def __init__(self, timeout: float = TimeoutConfig.APPROVAL_LINE_WAIT) -> None:
        """Initialize the handler.

        Args:
            timeout: Per-step bound for add/reorder verification waits.
        """
        self.timeout = timeout

    @handle_pywinauto_error("결재정보(win32) 연결", logger, default_return=None)
    def connect_approval_window(self) -> Any:
        """Connect to the payment-info dialog through the win32 backend.

        The org-chart TreeView/ListView pair is invisible to uia, so a
        separate win32 handle is required even though OfficialCollector
        drives the main window through uia.

        Returns:
            Any: The 결재정보 dialog, or None on failure.
        """
        # pylint: disable=import-outside-toplevel
        # Local import: win32 backend exists on Windows only; keeping it here
        # lets the module (and its unit tests) import anywhere.
        from pywinauto import Application

        app = Application(backend="win32")
        app.connect(title_re=UIConfig.PAYMENT_INFO_TITLE)
        dialog = app.window(title=UIConfig.PAYMENT_INFO_TITLE)
        logger.info("결재정보(win32) 연결: %s", dialog.window_text())
        return dialog

    def set_approval_line(
        self,
        dialog: Any,
        approvers: List[Approver],
        wait_for_condition: Callable[..., bool],
    ) -> bool:
        """Stage and save the approval line in the predetermined order.

        Args:
            dialog: win32 결재정보 dialog (see connect_approval_window).
            approvers: Desired members in display order (first = top row).
            wait_for_condition: Polling helper, same shape as
                OfficialCollector._wait_for_condition.

        Returns:
            bool: True when the saved order matches, False otherwise.
        """
        result = self._set_approval_line(dialog, approvers, wait_for_condition)
        return bool(result)

    @log_execution_time(logger, "조직도 결재선 지정")
    @handle_pywinauto_error("조직도 결재선 지정", logger, default_return=False)
    def _set_approval_line(
        self,
        dialog: Any,
        approvers: List[Approver],
        wait_for_condition: Callable[..., bool],
    ) -> bool:
        """Implement set_approval_line with error handling and timing."""
        if not self._valid_request(approvers):
            return False
        resolved = self._resolve_components(dialog)
        if resolved is None:
            return False
        tree, listview = resolved
        target = [approver.name for approver in approvers]
        if not self._stage_missing(dialog, tree, listview, approvers, wait_for_condition):
            return False
        try:
            staged = self.reorder(dialog, listview, target, wait_for_condition)
        except ValueError as exc:
            logger.error("결재선 검증 실패: %s", exc)
            return False
        if not staged or not self._confirm(dialog):
            return False
        logger.info("조직도 결재선 지정 완료: %s", target)
        return True

    def _valid_request(self, approvers: List[Approver]) -> bool:
        """Reject empty or duplicated approval orders."""
        if not approvers:
            logger.error("결재선 지정 실패: 빈 승인자 목록")
            return False
        if len({approver.name for approver in approvers}) != len(approvers):
            logger.error("결재선 지정 실패: 승인자 중복")
            return False
        return True

    def _resolve_components(self, dialog: Any) -> Optional[Tuple[Any, Any]]:
        """Return the (org tree, approval list) pair, if both visible."""
        tree = self._find_visible_tree(dialog)
        if tree is None:
            logger.error("결재선 지정 실패: 조직도 트리 미발견")
            return None
        listview = self._find_approval_list(dialog)
        if listview is None:
            logger.error("결재선 지정 실패: 결재선 목록 미발견")
            return None
        return (tree, listview)

    def _stage_missing(
        self,
        dialog: Any,
        tree: Any,
        listview: Any,
        approvers: List[Approver],
        wait_for_condition: Callable[..., bool],
    ) -> bool:
        """Add every missing approver; the client prepends added rows, so
        adding in reverse target order lands near the final order."""
        for approver in reversed(approvers):
            if approver.name in self.read_approver_names(listview):
                continue
            if not self.add_approver(
                dialog, tree, approver, listview, wait_for_condition
            ):
                return False
        return True

    def read_approver_names(self, listview: Any) -> List[str]:
        """Return the staged approver names in display order.

        Raises:
            ValueError: The 결재자 column is missing.
        """
        column = self._name_column_index(listview)
        return [
            listview.get_item(i, column)["text"]
            for i in range(listview.item_count())
        ]

    def add_approver(
        self,
        dialog: Any,
        tree: Any,
        approver: Approver,
        listview: Any,
        wait_for_condition: Callable[..., bool],
    ) -> bool:
        """Add one person from the org chart to the approval list.

        Returns:
            bool: True when the row count grew by one.
        """
        try:
            department = tree.get_item(
                [UIConfig.ORGCHART_ROOT_NODE, approver.department]
            )
        except Exception as exc:
            logger.error("부서 노드 미발견: %s (%s)", approver.department, exc)
            return False
        try:
            node_texts = [child.text() for child in department.children()]
        except Exception as exc:
            logger.error("부서 하위 목록 조회 실패: %s (%s)", approver.department, exc)
            return False
        try:
            node_text = match_node_text(node_texts, approver.name)
        except ValueError as exc:
            logger.error("직원 매칭 실패: %s", exc)
            return False
        before = listview.item_count()
        try:
            tree.get_item(
                [UIConfig.ORGCHART_ROOT_NODE, approver.department, node_text]
            ).select()
            add_button = dialog.child_window(
                title=UIConfig.ADD_APPROVER_BUTTON, class_name="Button"
            )
            add_button.click()
        except Exception as exc:
            logger.error("조직도 추가 클릭 실패: %s (%s)", approver.name, exc)
            return False
        if not wait_for_condition(
            lambda: listview.item_count() == before + 1, timeout=self.timeout
        ):
            logger.error("조직도 추가 미반영: %s", approver.name)
            return False
        logger.info("조직도 추가 완료: %s", node_text)
        return True

    def reorder(
        self,
        dialog: Any,
        listview: Any,
        target: List[str],
        wait_for_condition: Callable[..., bool],
    ) -> bool:
        """Move staged rows up until the order matches target.

        Re-plans after every move so a missed click self-corrects instead
        of derailing the remaining steps.

        Raises:
            ValueError: Staged set differs from target (see plan_up_moves).

        Returns:
            bool: True when the final order matches target.
        """
        buttons = self._find_order_buttons(dialog, listview)
        if buttons is None:
            return False
        up_button = buttons[0]
        bound = len(target) * len(target) + len(target)
        for _ in range(bound):
            current = self.read_approver_names(listview)
            if current == target:
                logger.info("결재선 순서 확정: %s", target)
                return True
            index = plan_up_moves(current, target)[0]
            listview.select(index)
            expected = list(current)
            expected[index - 1], expected[index] = expected[index], expected[index - 1]
            up_button.click_input()
            if not wait_for_condition(
                lambda expected=expected: self.read_approver_names(listview)
                == expected,
                timeout=self.timeout,
            ):
                logger.error("순서 이동 미반영: index %s", index)
                return False
        logger.error("순서 정렬 시도 초과: %s", target)
        return False

    def _find_visible_tree(self, dialog: Any) -> Optional[Any]:
        """Return the visible org-chart TreeView, if any."""
        try:
            trees = dialog.descendants(class_name="SysTreeView32")
        except Exception as exc:
            logger.error("트리 조회 실패: %s", exc)
            return None
        for tree in trees:
            try:
                if tree.is_visible():
                    return tree
            except Exception as exc:
                logger.debug("트리 가시성 확인 실패: %s", exc)
        return None

    def _find_approval_list(self, dialog: Any) -> Optional[Any]:
        """Return the approval ListView (List1), if present."""
        try:
            lists = dialog.descendants(class_name="SysListView32")
        except Exception as exc:
            logger.error("목록 조회 실패: %s", exc)
            return None
        for listview in lists:
            try:
                if listview.window_text() == UIConfig.APPROVAL_LIST_NAME:
                    return listview
            except Exception as exc:
                logger.debug("목록 제목 확인 실패: %s", exc)
        return None

    def _name_column_index(self, listview: Any) -> int:
        """Return the 결재자 column index.

        Raises:
            ValueError: The column header is missing.
        """
        for index in range(listview.column_count()):
            if listview.get_column(index)["text"] == UIConfig.APPROVER_NAME_COLUMN:
                return index
        raise ValueError("결재자 열 미발견")

    def _find_order_buttons(
        self, dialog: Any, listview: Any
    ) -> Optional[Tuple[Any, Any]]:
        """Return the (up, down) order buttons beside the approval list.

        Identified geometrically: untitled visible buttons whose top edge
        falls inside the list span, sorted top-first. Rect coordinates are
        never hardcoded so the lookup survives resolution changes.
        """
        rect = listview.rectangle()
        candidates = []
        try:
            buttons = dialog.descendants(class_name="Button")
        except Exception as exc:
            logger.error("버튼 조회 실패: %s", exc)
            return None
        for button in buttons:
            try:
                if button.window_text() != "" or not button.is_visible():
                    continue
                top = button.rectangle().top
                if rect.top <= top <= rect.bottom:
                    candidates.append(button)
            except Exception as exc:
                logger.debug("순서 버튼 후보 확인 실패: %s", exc)
        candidates.sort(key=lambda button: button.rectangle().top)
        if len(candidates) < 2:
            logger.error("순서 버튼 미발견")
            return None
        return (candidates[0], candidates[1])

    def _confirm(self, dialog: Any) -> bool:
        """Click the visible confirm button to save the approval line."""
        try:
            confirms = [
                button
                for button in dialog.descendants(class_name="Button")
                if button.window_text() == UIConfig.CONFIRM_BUTTON
                and button.is_visible()
                and button.is_enabled()
            ]
        except Exception as exc:
            logger.error("확인 버튼 조회 실패: %s", exc)
            return False
        if not confirms:
            logger.error("확인 버튼 미발견")
            return False
        confirms.sort(key=lambda button: button.rectangle().top)
        try:
            confirms[0].click()
        except Exception as exc:
            logger.error("확인 버튼 클릭 실패: %s", exc)
            return False
        logger.info("결재정보 확인 클릭")
        return True
