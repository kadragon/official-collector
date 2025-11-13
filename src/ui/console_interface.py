"""
Unified Console Interface

통합된 콘솔 UI 인터페이스 - 터미널 출력, 사용자 상호작용, 삭제 메뉴를 통합하여 제공합니다.
기존의 terminal_ui, user_interaction, deletion_menus 모듈을 하나로 통합한 단일 인터페이스입니다.
"""

import logging
import unicodedata
from enum import Enum, auto
from typing import List, Tuple, Optional
import win32gui
import win32con
from rich.panel import Panel
from utils.error_handler import setup_logger
from ui.rich_console import RichConsole

setup_logger(__name__, console_output=True)

# Initialize Rich Console singleton
_rich_console = RichConsole()


def _logger() -> logging.Logger:
    """Return a module-level logger (supports test monkeypatching)."""
    return logging.getLogger(__name__)


# ============================================================================
# 기본 스타일링 및 출력 유틸리티
# ============================================================================


class Colors:
    """
    터미널 컬러 코드 (deprecated).

    Note: This class is deprecated. Rich library handles all color styling now.
    Kept for backward compatibility only.
    """

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 핵심 색상만 유지
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


class Symbols:
    """
    터미널 심볼 (deprecated).

    Note: This class is deprecated. Rich library uses Unicode symbols directly.
    Kept for backward compatibility only.
    """

    ARROW = "->"
    INFO = "[INFO]"
    WARNING = "[WARN]"
    ERROR = "[ERROR]"
    SUCCESS = "[OK]"


def get_display_width(text: str) -> int:
    """
    Estimate printable width accounting for East Asian characters.

    Note: This function is deprecated. Rich library handles CJK width automatically.
    Kept for backward compatibility only.
    """
    if not text:
        return 0

    has_wide_char = any(
        unicodedata.east_asian_width(ch) in {"F", "W", "A"} for ch in text
    )

    width = 0
    for char in text:
        east_asian_width = unicodedata.east_asian_width(char)
        if east_asian_width in {"F", "W", "A"}:
            width += 2
        else:
            width += 1

        if has_wide_char and char.isalpha() and char.isupper():
            width += 1

    return width


def clear_screen() -> None:
    """화면을 지웁니다."""
    _rich_console.clear_screen()


def draw_separator(char: str = "-", width: int = 60, style: str = "simple") -> None:
    """
    구분선을 그립니다.

    Note: This function is deprecated. Use RichConsole.print_separator() instead.
    """
    _rich_console.print_separator(length=width, char=char)


def draw_header(title: str, width: int = 60) -> None:
    """
    헤더를 그립니다.

    Note: This function is deprecated. Use RichConsole.print_header() instead.
    """
    _rich_console.print_header(title, width=width)


# ============================================================================
# 메시지 출력 함수들
# ============================================================================


def print_info(message: str) -> None:
    """정보 메시지를 출력합니다."""
    _logger().info(message)
    _rich_console.print_info(message)


def print_success(message: str) -> None:
    """성공 메시지를 출력합니다."""
    _logger().info(f"SUCCESS: {message}")
    _rich_console.print_success(message)


def print_warning(message: str) -> None:
    """경고 메시지를 출력합니다."""
    _logger().warning(message)
    _rich_console.print_warning(message)


def print_error(message: str) -> None:
    """에러 메시지를 출력합니다."""
    _logger().error(message)
    _rich_console.print_error(message)


def print_document_info(title: str, doc_type: str = "문서") -> None:
    """문서 정보를 박스 형태로 출력합니다."""
    _logger().info(f"처리 중인 {doc_type}: {title}")
    _rich_console.print_document_info(title, doc_type)


def print_numbered_list(
    items: List[str], start_index: int = 1, highlight_color: str = ""
) -> None:
    """
    번호가 매겨진 목록을 예쁘게 출력합니다.

    Note: highlight_color parameter is deprecated and ignored.
    """
    _rich_console.print_numbered_list(items, start_index=start_index)


def print_selection_menu(
    title: str,
    items: List[str],
    allow_skip: bool = False,
    skip_text: str = "목록에 없음",
) -> None:
    """선택 메뉴를 출력합니다."""
    _rich_console.print_selection_menu(title, items, allow_skip, skip_text)


def get_styled_input(prompt: str, input_color: str = "") -> str:
    """
    스타일이 적용된 입력을 받습니다.

    Note: input_color parameter is deprecated and ignored.
    """
    try:
        # Use simple prompt without ANSI codes for better compatibility
        return input(f"❯ {prompt}: ")
    except EOFError:
        print("\n프로그램을 종료합니다.")
        exit(0)
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
        exit(0)


def print_final_result(success_count: int, total_count: int) -> None:
    """최종 처리 결과를 출력합니다."""
    _logger().info(f"처리 완료 - 성공: {success_count}/{total_count}")
    _rich_console.print_final_result(success_count, total_count)


# ============================================================================
# 사용자 선택 및 입력 검증
# ============================================================================


class SelectionResult(Enum):
    """선택 결과를 나타내는 Enum."""

    SELECTED = auto()
    SKIPPED = auto()
    MANUAL_INPUT = auto()


def get_valid_selection(user_input: str, options: List[str]) -> str:
    """
    사용자 입력을 검증하고 유효한 옵션을 반환합니다.

    Note: This is legacy code. New code should use RichConsole.validate_selection()
    instead for centralized input validation.
    """
    try:
        selection = int(user_input) - 1
    except (TypeError, ValueError) as exc:
        raise ValueError("유효하지 않은 입력입니다. 숫자를 입력해주세요.") from exc

    if 0 <= selection < len(options):
        return options[selection]

    raise ValueError("유효하지 않은 번호입니다.")


def get_user_choice_from_list(
    options: List[str], allow_skip: bool = False
) -> Tuple[SelectionResult, Optional[str]]:
    """사용자에게 목록에서 선택하도록 합니다."""
    while True:
        try:
            selection = get_styled_input("번호를 선택하세요: ")

            if allow_skip and selection == "0":
                return SelectionResult.SKIPPED, None

            selected_index = int(selection) - 1
            if 0 <= selected_index < len(options):
                return SelectionResult.SELECTED, options[selected_index]
            else:
                _logger().warning(f"유효하지 않은 번호 선택: {selection}")
                print("유효하지 않은 번호입니다. 다시 선택해주세요.")
        except ValueError:
            _logger().warning(f"유효하지 않은 입력: {selection}")
            print("유효하지 않은 입력입니다. 번호를 입력해주세요.")


def get_user_choice_from_recommendations(
    title: str, recommendations: List[str]
) -> Tuple[SelectionResult, Optional[str]]:
    """사용자에게 추천 목록에서 선택하도록 합니다."""
    activate_cmd_window()  # 포커스 활성화 추가
    print_selection_menu(
        "추천 목록",
        recommendations,
        allow_skip=True,
        skip_text="추천 없음 (다음 단계로 이동)",
    )

    while True:
        try:
            selection = get_styled_input("번호를 선택하세요: ")
            _logger().info(f"사용자 선택 입력: '{selection}'")
            if selection == "0":
                _logger().info("사용자가 추천 없음(0) 선택 - SKIPPED 반환")
                return SelectionResult.SKIPPED, None

            selected_index = int(selection) - 1
            if 0 <= selected_index < len(recommendations):
                return SelectionResult.SELECTED, recommendations[selected_index]
            else:
                _logger().warning(f"유효하지 않은 번호 선택 (추천에서): {selection}")
                print("유효하지 않은 번호입니다. 다시 선택해주세요.")
        except ValueError:
            _logger().warning(
                f"유효하지 않은 입력 (추천에서): {selection if 'selection' in locals() else '알 수 없음'}"
            )
            print("유효하지 않은 입력입니다. 번호를 입력해주세요.")


def confirm_choice(message: str, default_yes: bool = True) -> bool:
    """사용자에게 예/아니오 확인을 요청합니다."""
    prompt_suffix = " (Y/n): " if default_yes else " (y/N): "
    confirm = input(message + prompt_suffix)

    if not confirm:
        return default_yes

    return confirm.lower() == "y"


def activate_cmd_window() -> None:
    """CMD 창을 활성화합니다 (사용자 상호작용 전)."""
    try:
        from pywinauto import Application

        # 방법 1: 창 제목으로 찾기 (bat 파일에서 title 설정한 경우)
        try:
            app = Application().connect(title="DocumentAutoClassifier")
            window = app.window(title="DocumentAutoClassifier")
            window.set_focus()
            _logger().debug("창 제목으로 CMD 창 포커스 활성화 성공")
            return
        except Exception as exc:
            _logger().debug("Failed to focus DocumentAutoClassifier window: %s", exc)

        # 방법 2: 현재 콘솔 창 핸들 사용 (기존 방법)
        console_hwnd = win32gui.GetConsoleWindow()
        if console_hwnd:
            win32gui.ShowWindow(console_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(console_hwnd)
            _logger().debug("핸들로 CMD 창 포커스 활성화 성공")
        else:
            _logger().debug("콘솔 창 핸들을 찾을 수 없습니다")
    except Exception as e:
        _logger().debug(f"CMD 창 활성화 중 오류: {e}")


# ============================================================================
# 통합된 콘솔 인터페이스 클래스
# ============================================================================


class ConsoleInterface:
    """통합된 콘솔 사용자 인터페이스."""

    def __init__(self) -> None:
        """초기화."""
        pass

    # ========================================================================
    # 접수 문서 관련 메서드
    # ========================================================================

    def select_approval_and_share(
        self, approval_list: List[str], share_list: List[str]
    ) -> Tuple[str, str]:
        """담당자와 공람대상자를 선택합니다."""
        activate_cmd_window()
        clear_screen()

        if len(approval_list) == 1:
            selected_approval = approval_list[0]
            print_success(f"담당자 자동 선택: {selected_approval}")
        else:
            print_selection_menu("담당자 선택", approval_list)
            while True:
                try:
                    user_input = get_styled_input("번호를 선택하세요: ")
                    selected_approval = get_valid_selection(user_input, approval_list)
                    break
                except ValueError as e:
                    print(str(e))

        # 담당자 선택 완료 메시지 출력
        print_success(f"{selected_approval} 담당으로 선택 완료")
        print()

        print_selection_menu("공람자 선택", share_list)
        while True:
            try:
                user_input = get_styled_input("번호를 선택하세요: ")
                selected_share = get_valid_selection(user_input, share_list)
                break
            except ValueError as e:
                print(str(e))

        return selected_approval, selected_share

    # ========================================================================
    # 과제 카드 관련 메서드
    # ========================================================================

    def confirm_recommendation(self, title: str, recommended_task_title: str) -> bool:
        """추천된 과제 카드를 확인합니다."""
        activate_cmd_window()
        clear_screen()

        content = (
            f"[dim]공문 제목:[/dim] {title}\n"
            f"[green]추천 항목:[/green] [bold]{recommended_task_title}[/bold]"
        )
        panel = Panel(
            content,
            title="[bold white]추천 확인[/bold white]",
            border_style="cyan",
            padding=(1, 2),
        )
        _rich_console.console.print()
        _rich_console.console.print(panel)
        _rich_console.console.print()

        return _rich_console.confirm("이 추천을 사용하시겠습니까?", default=True)

    def choose_from_predefined_list(
        self, title: str, card_list: List[str]
    ) -> Tuple[SelectionResult, Optional[str]]:
        """미리 정의된 과제 카드 목록에서 선택합니다."""
        activate_cmd_window()
        clear_screen()
        print_document_info(title, "과제 카드 선택")

        print_selection_menu(
            "목록에서 선택", card_list, allow_skip=True, skip_text="목록에 없음"
        )
        return get_user_choice_from_list(card_list, allow_skip=True)

    def choose_from_full_list(
        self, title: str, card_list: List[str]
    ) -> Tuple[SelectionResult, Optional[str]]:
        """전체 과제 카드 목록에서 선택합니다."""
        activate_cmd_window()
        clear_screen()
        print_document_info(title, "전체 목록에서 선택")

        sorted_card_list = sorted(card_list)
        print_selection_menu("전체 목록에서 선택", sorted_card_list, allow_skip=False)
        return get_user_choice_from_list(sorted_card_list, allow_skip=False)

    def choose_from_recommendations(
        self, title: str, recommendations: List[str]
    ) -> Tuple[SelectionResult, Optional[str]]:
        """추천 목록에서 선택합니다."""
        activate_cmd_window()
        clear_screen()
        print_document_info(title, "추천 목록")

        print_selection_menu(
            "추천 목록",
            recommendations,
            allow_skip=True,
            skip_text="추천 없음 (다음 단계로 이동)",
        )
        return get_user_choice_from_list(recommendations, allow_skip=True)

    def get_manual_task_card(self, title: str) -> Optional[str]:
        """직접 과제 카드 이름을 입력받습니다."""
        activate_cmd_window()
        clear_screen()
        print_document_info(title, "직접 입력")

        return input(get_styled_input("과제 카드 이름: "))

    # ========================================================================
    # 삭제 관련 메서드
    # ========================================================================

    def show_deletion_menu(self) -> str:
        """삭제 작업 메뉴를 표시합니다."""
        activate_cmd_window()
        clear_screen()

        options = [
            "과제 카드 목록 보기 및 삭제",
            "접수 문서 목록 보기 및 삭제",
            "개별 과제 카드 삭제",
            "개별 접수 문서 삭제",
            "일괄 삭제",
            "취소",
        ]

        print_selection_menu("삭제 작업 선택", options)

        while True:
            try:
                user_input = get_styled_input("번호를 선택하세요: ")
                choice = get_valid_selection(user_input, options)
                return choice
            except ValueError as e:
                print(str(e))

    def show_items_for_deletion(self, items: List[Tuple], item_type: str) -> List[int]:
        """삭제할 항목들을 표시하고 선택을 받습니다."""
        activate_cmd_window()
        clear_screen()

        if not items:
            _logger().info("삭제 가능한 %s이 없습니다.", item_type)
            _rich_console.print_warning(f"삭제 가능한 {item_type}이 없습니다.")
            input("엔터를 눌러 계속...")
            return []

        _logger().info("저장된 %s 목록 표시 (%d개)", item_type, len(items))

        # Use Rich Table for displaying items
        _rich_console.print_deletion_items(items, item_type)
        _rich_console.print_deletion_instructions()

        user_input = get_styled_input("선택").strip()

        if user_input.lower() == "q":
            return []
        elif user_input.lower() == "all":
            if _rich_console.confirm(
                f"모든 {item_type}을 삭제하시겠습니까?", default=False
            ):
                return list(range(len(items)))
            else:
                return []
        else:
            try:
                indices = []
                for num_str in user_input.split(","):
                    num = int(num_str.strip()) - 1
                    if 0 <= num < len(items):
                        indices.append(num)
                    else:
                        _logger().warning("잘못된 번호 입력: %s", num_str.strip())
                        _rich_console.print_warning(f"잘못된 번호: {num_str.strip()}")

                if indices and _rich_console.confirm_deletion(
                    len(indices), item_type, default=False
                ):
                    _logger().info("%d개 항목 삭제 확인됨", len(indices))
                    return indices
                else:
                    return []
            except ValueError:
                _logger().warning("사용자가 올바르지 않은 숫자 입력")
                _rich_console.print_error("올바른 숫자를 입력해주세요.")
                input("엔터를 눌러 계속...")
                return []

    def get_title_for_deletion(self, item_type: str) -> Optional[str]:
        """삭제할 항목의 제목을 직접 입력받습니다."""
        activate_cmd_window()
        clear_screen()

        _logger().info("%s 개별 삭제 시작", item_type)

        _rich_console.print_deletion_header(item_type)

        title = get_styled_input(f"삭제할 {item_type}의 제목을 입력하세요").strip()

        if title and _rich_console.confirm(
            f"'{title}' {item_type}을/를 삭제하시겠습니까?", default=False
        ):
            _logger().info("%s 삭제 확인: %s", item_type, title)
            return title
        return None

    def confirm_bulk_deletion(self) -> bool:
        """일괄 삭제를 확인합니다."""
        activate_cmd_window()
        clear_screen()

        return _rich_console.confirm_bulk_deletion()

    # ========================================================================
    # 기타 유틸리티 메서드
    # ========================================================================

    def print_final_result(self, success_count: int, total_count: int) -> None:
        """최종 처리 결과를 출력합니다."""
        _logger().info("처리 완료 - 성공: %d/%d", success_count, total_count)
        _rich_console.print_final_result(success_count, total_count)

    def wait_for_enter(self, message: str = "계속하려면 Enter를 누르세요...") -> None:
        """Enter 키 대기."""
        _rich_console.console.print(f"\n[dim]{message}[/dim]", end="")
        input()
