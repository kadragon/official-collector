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
    if sorted(current) != sorted(target):
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
    def connect_approval_window(self, process_id: Optional[int] = None) -> Any:
        """Connect to the payment-info dialog through the win32 backend.

        The org-chart TreeView/ListView pair is invisible to uia, so a
        separate win32 handle is required even though OfficialCollector
        drives the main window through uia. Scoping to the known process
        avoids attaching to a same-titled dialog of another instance.

        Args:
            process_id: Owning process id, when the caller knows it.

        Returns:
            Any: The 결재정보 dialog, or None on failure.
        """
        # pylint: disable=import-outside-toplevel
        # Local import: win32 backend exists on Windows only; keeping it here
        # lets the module (and its unit tests) import anywhere.
        from pywinauto import Application

        app = Application(backend="win32")
        if process_id is None:
            app.connect(title_re=UIConfig.PAYMENT_INFO_TITLE)
        else:
            app.connect(title_re=UIConfig.PAYMENT_INFO_TITLE, process=process_id)
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
        resolved = self._wait_for_components(dialog, wait_for_condition)
        if resolved is None:
            logger.error("결재선 지정 실패: 조직도 트리/목록 미발견")
            return False
        tree, listview = resolved
        target = [approver.name for approver in approvers]
        if not self._sync_members(dialog, tree, listview, approvers, wait_for_condition):
            return False
        try:
            staged = self.reorder(dialog, listview, target, wait_for_condition)
        except ValueError as exc:
            logger.error("결재선 검증 실패: %s", exc)
            return False
        if not staged or not self._confirm(dialog, wait_for_condition):
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

    def _wait_for_components(
        self, dialog: Any, wait_for_condition: Callable[..., bool]
    ) -> Optional[Tuple[Any, Any]]:
        """Wait until the org tree and approval list are both visible.

        The tab content draws shortly after the tab switch, so the first
        lookup may legitimately find nothing.
        """
        holder: dict = {}

        def _ready() -> bool:
            tree = self._find_visible_tree(dialog, quiet=True)
            listview = self._find_approval_list(dialog, quiet=True)
            if tree is None or listview is None:
                return False
            holder["pair"] = (tree, listview)
            return True

        if not wait_for_condition(_ready, timeout=self.timeout):
            # One loud attempt for diagnostics before giving up.
            self._resolve_components(dialog, quiet=False)
            return None
        pair = holder.get("pair")
        return pair if isinstance(pair, tuple) else None

    def _resolve_components(
        self, dialog: Any, quiet: bool = False
    ) -> Optional[Tuple[Any, Any]]:
        """Return the (org tree, approval list) pair, if both visible."""
        tree = self._find_visible_tree(dialog, quiet=quiet)
        if tree is None:
            if not quiet:
                logger.error("결재선 지정 실패: 조직도 트리 미발견")
            return None
        listview = self._find_approval_list(dialog, quiet=quiet)
        if listview is None:
            if not quiet:
                logger.error("결재선 지정 실패: 결재선 목록 미발견")
            return None
        return (tree, listview)

    def _sync_members(
        self,
        dialog: Any,
        tree: Any,
        listview: Any,
        approvers: List[Approver],
        wait_for_condition: Callable[..., bool],
    ) -> bool:
        """Remove off-target rows, then add every missing approver."""
        target = [approver.name for approver in approvers]
        if not self._remove_extras(dialog, listview, target, wait_for_condition):
            return False
        return self._stage_missing(dialog, tree, listview, approvers, wait_for_condition)

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

    def _child_texts(self, node: Any) -> List[str]:
        """Return child node texts; empty on error or while lazy-loading."""
        try:
            return [child.text() for child in node.children()]
        except Exception as exc:
            logger.debug("하위 노드 조회 실패: %s", exc)
            return []

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
        node_text = self._resolve_person_node(tree, approver, wait_for_condition)
        if node_text is None:
            return False
        before = listview.item_count()
        try:
            leaf = tree.get_item(
                [UIConfig.ORGCHART_ROOT_NODE, approver.department, node_text],
                exact=True,
            )
            if leaf.text() != node_text:
                logger.error("직원 노드 불일치: %s", approver.name)
                return False
            leaf.select()
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

    def _resolve_person_node(
        self,
        tree: Any,
        approver: Approver,
        wait_for_condition: Callable[..., bool],
    ) -> Optional[str]:
        """Expand the department and resolve the person's node text."""
        try:
            department = tree.get_item(
                [UIConfig.ORGCHART_ROOT_NODE, approver.department], exact=True
            )
            if department.text() != approver.department:
                logger.error("부서 노드 불일치: %s", approver.department)
                return None
            department.expand()
        except Exception as exc:
            logger.error("부서 노드 미발견: %s (%s)", approver.department, exc)
            return None
        if not wait_for_condition(
            lambda: self._child_texts(department), timeout=self.timeout
        ):
            logger.error("부서 하위 목록 미로딩: %s", approver.department)
            return None
        try:
            return match_node_text(self._child_texts(department), approver.name)
        except ValueError as exc:
            logger.error("직원 매칭 실패: %s", exc)
            return None

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
            self._select_only(listview, index)
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

    def _select_only(self, listview: Any, index: int) -> None:
        """Clear stale selections before selecting one row.

        select() only sets the flag on the new row, so without clearing,
        earlier rows stay selected and the order button moves the wrong row.
        """
        try:
            for row in range(listview.item_count()):
                listview.deselect(row)
        except Exception as exc:
            logger.debug("선택 해제 실패: %s", exc)
        listview.select(index)

    def _remove_extras(
        self,
        dialog: Any,
        listview: Any,
        target: List[str],
        wait_for_condition: Callable[..., bool],
    ) -> bool:
        """Delete staged rows that are not in the target order, bottom-up."""
        try:
            remove_button = dialog.child_window(
                title=UIConfig.REMOVE_APPROVER_BUTTON, class_name="Button"
            )
        except Exception as exc:
            logger.error("삭제 버튼 미발견: %s", exc)
            return False
        for _ in range(listview.item_count()):
            current = self.read_approver_names(listview)
            extras = [name for name in current if name not in target]
            if not extras:
                return True
            index = max(i for i, name in enumerate(current) if name not in target)
            before = listview.item_count()
            self._select_only(listview, index)
            try:
                remove_button.click()
            except Exception as exc:
                logger.error("여분 행 삭제 실패: %s (%s)", current[index], exc)
                return False
            if not wait_for_condition(
                lambda before=before: listview.item_count() == before - 1,
                timeout=self.timeout,
            ):
                logger.error("여분 행 삭제 미반영: %s", current[index])
                return False
            logger.info("여분 행 삭제 완료: %s", current[index])
        logger.error("여분 행 삭제 시도 초과: %s", target)
        return False

    def _find_visible_tree(self, dialog: Any, quiet: bool = False) -> Optional[Any]:
        """Return the visible org-chart TreeView, if any."""
        try:
            trees = dialog.descendants(class_name="SysTreeView32")
        except Exception as exc:
            if not quiet:
                logger.error("트리 조회 실패: %s", exc)
            return None
        for tree in trees:
            try:
                if tree.is_visible():
                    return tree
            except Exception as exc:
                logger.debug("트리 가시성 확인 실패: %s", exc)
        return None

    def _find_approval_list(self, dialog: Any, quiet: bool = False) -> Optional[Any]:
        """Return the approval ListView (List1), if present."""
        try:
            lists = dialog.descendants(class_name="SysListView32")
        except Exception as exc:
            if not quiet:
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
                bounds = button.rectangle()
                if not rect.top <= bounds.top <= rect.bottom:
                    continue
                if bounds.left < rect.right - UIConfig.ORDER_BUTTON_EDGE_TOLERANCE:
                    continue
                candidates.append(button)
            except Exception as exc:
                logger.debug("순서 버튼 후보 확인 실패: %s", exc)
        candidates.sort(key=lambda button: button.rectangle().top)
        if len(candidates) < 2:
            logger.error("순서 버튼 미발견")
            return None
        return (candidates[0], candidates[1])

    def _confirm(
        self, dialog: Any, wait_for_condition: Callable[..., bool]
    ) -> bool:
        """Click confirm and verify the dialog closes (save applied)."""
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
        if not wait_for_condition(lambda: self._dialog_closed(dialog), timeout=self.timeout):
            logger.error("결재정보 저장 미확인: 창이 닫히지 않음")
            return False
        logger.info("결재정보 저장 확인")
        return True

    def _dialog_closed(self, dialog: Any) -> bool:
        """True when the dialog is gone; lookup errors count as closed."""
        try:
            return not dialog.is_visible()
        except Exception as exc:
            logger.debug("결재정보 상태 확인 실패 (닫힘으로 간주): %s", exc)
            return True
