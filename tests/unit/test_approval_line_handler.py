# Trace: backlog.md - Build 접수 approval line from org chart in predetermined order
"""Tests for ApprovalLineHandler (org-chart approval line, predetermined order)."""

import pytest
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

from services.approval_line_handler import (
    Approver,
    ApprovalLineHandler,
    match_node_text,
    plan_up_moves,
)


# ---------------------------------------------------------------------- #
# Fakes (mimic the pywinauto wrapper surface used by the handler)
# ---------------------------------------------------------------------- #


class FakeNode:
    def __init__(self, text: str, kids: Optional[List["FakeNode"]] = None) -> None:
        self._text = text
        self._kids = kids or []
        self.selected = False
        self.expanded = False

    def text(self) -> str:
        return self._text

    def select(self) -> None:
        self.selected = True

    def expand(self) -> None:
        self.expanded = True

    def is_expanded(self) -> bool:
        return self.expanded

    def children(self) -> List["FakeNode"]:
        # Models lazy loading: children appear only after expand().
        return list(self._kids) if self.expanded else []


class FakeTree:
    """get_item(path) resolves nested dict: {part: (node_text, {child...})}."""

    def __init__(self, root_name: str, depts: Dict[str, List[str]]) -> None:
        kids = [
            FakeNode(dept, [FakeNode(n) for n in names])
            for dept, names in depts.items()
        ]
        self._root = FakeNode(root_name, kids)
        self._root.expand()  # top-level departments are always visible

    def is_visible(self) -> bool:
        return True

    def get_item(self, path: List[str], exact: bool = False) -> FakeNode:
        node = self._root
        if path[0] != node.text():
            raise RuntimeError("root mismatch: %s" % path[0])
        for part in path[1:]:
            for kid in node.children():
                if kid.text() == part:
                    node = kid
                    break
            else:
                raise RuntimeError("node not found: %s" % part)
        return node


class FakeListView:
    HEADERS = ["직위", "직급", "결재방법", "결재자"]

    def __init__(self, rows: List[List[str]]) -> None:
        self.rows = [list(r) for r in rows]
        self.selected: set = set()
        self._title = "List1"

    def window_text(self) -> str:
        return self._title

    def rectangle(self) -> SimpleNamespace:
        return SimpleNamespace(top=381, left=1008, right=1302, bottom=696)

    def item_count(self) -> int:
        return len(self.rows)

    def column_count(self) -> int:
        return len(self.HEADERS)

    def get_column(self, i: int) -> Dict[str, str]:
        return {"text": self.HEADERS[i]}

    def get_item(self, i: int, j: int) -> Dict[str, str]:
        return {"text": self.rows[i][j]}

    def select(self, i: int) -> None:
        self.selected.add(i)

    def deselect(self, i: int) -> None:
        self.selected.discard(i)

    def prepend(self, row: List[str]) -> None:
        self.rows.insert(0, list(row))

    def move_up_selected(self) -> None:
        if len(self.selected) != 1:
            return
        i = next(iter(self.selected))
        if i <= 0:
            return
        self.rows[i - 1], self.rows[i] = self.rows[i], self.rows[i - 1]
        self.selected = {i - 1}


def _rect(top: int, left: int = 1304, right: int = 1328) -> SimpleNamespace:
    return SimpleNamespace(top=top, left=left, right=right, bottom=top + 21)


class FuzzyTree(FakeTree):
    """Resolves any path to a wrong node (models fuzzy mismatch)."""

    def get_item(self, path: List[str], exact: bool = False) -> FakeNode:
        return FakeNode("교무과")


class FakeButton:
    def __init__(
        self,
        title: str,
        rect_top: int = 0,
        effect: Optional[Callable[[], None]] = None,
        left: int = 1304,
    ) -> None:
        self._title = title
        self._rect = _rect(rect_top, left=left)
        self._effect = effect
        self.clicks = 0

    def window_text(self) -> str:
        return self._title

    def rectangle(self) -> SimpleNamespace:
        return self._rect

    def is_visible(self) -> bool:
        return True

    def is_enabled(self) -> bool:
        return True

    def click(self) -> None:
        self.clicks += 1
        if self._effect:
            self._effect()

    def click_input(self) -> None:
        self.click()


class FakeDialog:
    """descendants() serves ListViews + Buttons; child_window() serves ▶ 추가."""

    LIST_RECT = SimpleNamespace(top=381, left=1008, right=1302, bottom=696)

    def __init__(self, tree: FakeTree, lv: FakeListView) -> None:
        self.tree = tree
        self.lv = lv
        self.open = True
        self.add_button = FakeButton("▶ 추가", rect_top=416)
        self.remove_button = FakeButton("◀ 삭제", rect_top=452)
        self.up_button = FakeButton("", rect_top=411)
        self.down_button = FakeButton("", rect_top=441)
        # Stray untitled button left of the list: must be ignored.
        self.stray_button = FakeButton("", rect_top=500, left=900)
        self.confirm_button = FakeButton("확인", rect_top=801)
        # wire effects after list exists
        self.up_button._effect = self.lv.move_up_selected
        self.remove_button._effect = self._remove_selected
        self.confirm_button._effect = self._close

    def is_visible(self) -> bool:
        return self.open

    def _close(self) -> None:
        self.open = False

    def _remove_selected(self) -> None:
        if len(self.lv.selected) == 1:
            self.lv.rows.pop(next(iter(self.lv.selected)))
            self.lv.selected.clear()

    def descendants(self, class_name: str = "") -> List[Any]:
        if class_name == "SysTreeView32":
            return [self.tree]
        if class_name == "SysListView32":
            return [self.lv]
        if class_name == "Button":
            return [
                self.add_button,
                self.remove_button,
                self.up_button,
                self.down_button,
                self.stray_button,
                self.confirm_button,
            ]
        return []

    def child_window(self, title: str = "", class_name: str = "") -> FakeButton:
        if title == "▶ 추가":
            return self.add_button
        if title == "◀ 삭제":
            return self.remove_button
        raise RuntimeError("unexpected child_window: %s" % title)


def immediate_wait(condition: Callable[[], bool], timeout: Any = None, interval: Any = None) -> bool:
    return bool(condition())


def make_org() -> FakeTree:
    return FakeTree(
        "한국교원대학교",
        {
            "정보전산원": [
                "김승현 정보전산원장",
                "홍성민 정보보안담당관",
                "강동욱 정보화지원팀장",
            ]
        },
    )


def row_for(node_text: str) -> List[str]:
    mapping = {
        "강동욱 정보화지원팀장": ["정보화지원팀장", "전산주사", "업무담당자", "강동욱"],
        "김승현 정보전산원장": ["정보전산원장", "부교수", "업무관리자", "김승현"],
        "홍성민 정보보안담당관": ["정보보안담당관", "전산주사", "업무관리자", "홍성민"],
    }
    return mapping[node_text]


# ---------------------------------------------------------------------- #
# Pure logic: node matching
# ---------------------------------------------------------------------- #


class TestMatchNodeText:
    def test_exact_match(self) -> None:
        nodes = ["김승현 정보전산원장", "홍성민 정보보안담당관"]
        assert match_node_text(nodes, "김승현") == "김승현 정보전산원장"

    def test_trailing_space_name(self) -> None:
        assert match_node_text(["김수현 "], "김수현") == "김수현 "

    def test_no_match_raises(self) -> None:
        with pytest.raises(ValueError):
            match_node_text(["홍성민 정보보안담당관"], "이순신")

    def test_ambiguous_raises(self) -> None:
        with pytest.raises(ValueError):
            match_node_text(["김승현 정보전산원장", "김승현 주무관"], "김승현")

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            match_node_text([], "김승현")


# ---------------------------------------------------------------------- #
# Pure logic: move planning
# ---------------------------------------------------------------------- #


class TestPlanUpMoves:
    def test_ordered_needs_no_moves(self) -> None:
        assert plan_up_moves(["강동욱", "김승현"], ["강동욱", "김승현"]) == []

    def test_reversed_three(self) -> None:
        assert plan_up_moves(
            ["홍성민", "김승현", "강동욱"], ["강동욱", "김승현", "홍성민"]
        ) == [2, 1, 2]

    def test_single_move(self) -> None:
        assert plan_up_moves(["홍성민", "강동욱", "김승현"], ["강동욱", "홍성민", "김승현"]) == [1]

    def test_missing_target_raises(self) -> None:
        with pytest.raises(ValueError):
            plan_up_moves(["강동욱"], ["강동욱", "김승현"])

    def test_extra_current_raises(self) -> None:
        with pytest.raises(ValueError):
            plan_up_moves(["강동욱", "김승현", "이순신"], ["강동욱", "김승현"])

    def test_duplicate_target_raises(self) -> None:
        with pytest.raises(ValueError):
            plan_up_moves(["강동욱", "김승현"], ["강동욱", "강동욱"])

    def test_same_set_different_multiset_raises(self) -> None:
        with pytest.raises(ValueError):
            plan_up_moves(
                ["강동욱", "강동욱", "김승현"], ["강동욱", "김승현", "김승현"]
            )


# ---------------------------------------------------------------------- #
# Handler with fakes
# ---------------------------------------------------------------------- #


TARGET = [
    Approver(department="정보전산원", name="강동욱"),
    Approver(department="정보전산원", name="김승현"),
    Approver(department="정보전산원", name="홍성민"),
]


class TestSetApprovalLine:
    def test_adds_missing_and_orders(self) -> None:
        tree = make_org()
        lv = FakeListView([row_for("강동욱 정보화지원팀장")])
        dlg = FakeDialog(tree, lv)
        # ▶ 추가 prepends the selected tree node (fake the client effect)
        selected: List[str] = []

        orig_get = tree.get_item

        def tracking_get(path: List[str], exact: bool = False) -> FakeNode:
            node = orig_get(path)
            if len(path) == 3:
                selected.append(path[2])
            return node

        tree.get_item = tracking_get  # type: ignore[method-assign]
        dlg.add_button._effect = lambda: lv.prepend(row_for(selected[-1]))

        handler = ApprovalLineHandler()
        assert handler.set_approval_line(dlg, TARGET, immediate_wait) is True
        assert [lv.get_item(i, 3)["text"] for i in range(lv.item_count())] == [
            "강동욱",
            "김승현",
            "홍성민",
        ]
        assert dlg.confirm_button.clicks == 1

    def test_already_ordered_just_confirms(self) -> None:
        tree = make_org()
        lv = FakeListView(
            [
                row_for("강동욱 정보화지원팀장"),
                row_for("김승현 정보전산원장"),
                row_for("홍성민 정보보안담당관"),
            ]
        )
        dlg = FakeDialog(tree, lv)
        handler = ApprovalLineHandler()
        assert handler.set_approval_line(dlg, TARGET, immediate_wait) is True
        assert dlg.add_button.clicks == 0
        assert dlg.confirm_button.clicks == 1

    def test_unknown_person_fails_without_confirm(self) -> None:
        tree = make_org()
        lv = FakeListView([row_for("강동욱 정보화지원팀장")])
        dlg = FakeDialog(tree, lv)
        handler = ApprovalLineHandler()
        bad = [Approver(department="정보전산원", name="이순신")]
        assert handler.set_approval_line(dlg, bad, immediate_wait) is False
        assert dlg.confirm_button.clicks == 0

    def test_fuzzy_department_mismatch_fails(self) -> None:
        lv = FakeListView([row_for("강동욱 정보화지원팀장")])
        dlg = FakeDialog(FuzzyTree("한국교원대학교", {}), lv)
        handler = ApprovalLineHandler()
        bad = [Approver(department="정보전산원", name="김승현")]
        assert handler.set_approval_line(dlg, bad, immediate_wait) is False
        assert dlg.confirm_button.clicks == 0

    def test_unclosed_dialog_fails(self) -> None:
        tree = make_org()
        lv = FakeListView(
            [
                row_for("강동욱 정보화지원팀장"),
                row_for("김승현 정보전산원장"),
                row_for("홍성민 정보보안담당관"),
            ]
        )
        dlg = FakeDialog(tree, lv)
        dlg.confirm_button._effect = None  # dialog stays open: save unconfirmed
        handler = ApprovalLineHandler()
        assert handler.set_approval_line(dlg, TARGET, immediate_wait) is False

    def test_extra_rows_removed_before_staging(self) -> None:
        tree = make_org()
        lv = FakeListView(
            [
                row_for("강동욱 정보화지원팀장"),
                ["대기발령", "X", "X", "이순신"],
            ]
        )
        dlg = FakeDialog(tree, lv)
        selected: List[str] = []
        orig_get = tree.get_item

        def tracking_get(path: List[str], exact: bool = False) -> FakeNode:
            node = orig_get(path)
            if len(path) == 3:
                selected.append(path[2])
            return node

        tree.get_item = tracking_get  # type: ignore[method-assign]
        dlg.add_button._effect = lambda: lv.prepend(row_for(selected[-1]))

        handler = ApprovalLineHandler()
        assert handler.set_approval_line(dlg, TARGET, immediate_wait) is True
        assert [lv.get_item(i, 3)["text"] for i in range(lv.item_count())] == [
            "강동욱",
            "김승현",
            "홍성민",
        ]
        assert dlg.remove_button.clicks == 1
        assert dlg.confirm_button.clicks == 1

    def test_missing_components_fails(self) -> None:
        dlg = FakeDialog(make_org(), FakeListView([]))
        dlg.tree = None  # type: ignore[assignment]

        def no_tree(class_name: str = "") -> List[Any]:
            if class_name == "SysTreeView32":
                return []
            return FakeDialog.descendants(dlg, class_name)

        dlg.descendants = no_tree  # type: ignore[method-assign]
        handler = ApprovalLineHandler()
        assert handler.set_approval_line(dlg, TARGET, immediate_wait) is False
        assert dlg.confirm_button.clicks == 0
