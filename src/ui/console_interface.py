"""
Unified Console Interface

통합된 콘솔 UI 인터페이스 - 터미널 출력, 사용자 상호작용, 삭제 메뉴를 통합하여 제공합니다.
기존의 terminal_ui, user_interaction, deletion_menus 모듈을 하나로 통합한 단일 인터페이스입니다.
"""

import os
import logging
import subprocess
from enum import Enum, auto
from typing import List, Tuple, Optional
import win32gui
import win32con
from utils.error_handler import setup_logger

logger = setup_logger(__name__)


# ============================================================================
# 기본 스타일링 및 출력 유틸리티
# ============================================================================


class Colors:
    """터미널 컬러 코드 (필수 색상만 유지)."""

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
    """터미널 심볼 (필수만 유지)."""

    ARROW = "->"
    INFO = "[INFO]"
    WARNING = "[WARN]"
    ERROR = "[ERROR]"
    SUCCESS = "[OK]"


def get_display_width(text: str) -> int:
    """텍스트의 실제 표시 너비를 계산합니다 (한글 고려)."""
    width = 0
    for char in text:
        if ord(char) > 127:  # ASCII가 아닌 문자
            width += 2
        else:
            width += 1
    return width


def clear_screen():
    """화면을 지웁니다."""
    try:
        if os.name == "nt":
            subprocess.run(["cls"], shell=True, check=True)
        else:
            subprocess.run(["clear"], shell=True, check=True)
    except Exception:
        print("\n" * 50)


def draw_separator(char="-", width=60, style="simple"):
    """구분선을 그립니다."""
    if style == "simple":
        print(f"{Colors.DIM}{char * width}{Colors.RESET}")
    elif style == "section":
        print(f"{Colors.CYAN}{'-' * (width // 3)} * {'-' * (width // 3)}{Colors.RESET}")
    elif style == "header":
        print(f"{Colors.BOLD}{Colors.WHITE}{'=' * width}{Colors.RESET}")
    else:
        print(char * width)


def draw_header(title: str, width=60):
    """헤더를 그립니다."""
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'+' + '-' * (width - 2) + '+'}{Colors.RESET}")

    # 제목 길이에 따른 중앙 정렬
    title_display_width = get_display_width(title)
    padding = (width - 2 - title_display_width) // 2
    remaining = width - 2 - title_display_width - padding

    print(
        f"{Colors.BOLD}{Colors.CYAN}|{' ' * padding}{Colors.WHITE}{title}{Colors.CYAN}{' ' * remaining}|{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.CYAN}{'+' + '-' * (width - 2) + '+'}{Colors.RESET}")
    print()


# ============================================================================
# 메시지 출력 함수들
# ============================================================================


def print_info(message: str):
    """정보 메시지를 출력합니다."""
    logger.info(message)
    print(f"{Colors.BLUE}{Symbols.INFO} {message}{Colors.RESET}")


def print_success(message: str):
    """성공 메시지를 출력합니다."""
    logger.info(f"SUCCESS: {message}")
    print(f"{Colors.GREEN}{Symbols.SUCCESS} {message}{Colors.RESET}")


def print_warning(message: str):
    """경고 메시지를 출력합니다."""
    logger.warning(message)
    print(f"{Colors.YELLOW}{Symbols.WARNING} {message}{Colors.RESET}")


def print_error(message: str):
    """에러 메시지를 출력합니다."""
    logger.error(message)
    print(f"{Colors.RED}{Symbols.ERROR} {message}{Colors.RESET}")


def print_document_info(title: str, doc_type: str = "문서"):
    """문서 정보를 박스 형태로 출력합니다."""
    logger.info(f"처리 중인 {doc_type}: {title}")

    max_display_width = 60

    # 제목 줄바꿈 처리
    if get_display_width(title) > max_display_width - 4:
        lines = []
        current_line = ""
        words = title.split()

        for word in words:
            test_line = current_line + word + " " if current_line else word + " "
            if get_display_width(test_line) <= max_display_width - 4:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "

        if current_line:
            lines.append(current_line.strip())
    else:
        lines = [title]

    # 박스 너비 계산
    content_display_width = max(get_display_width(line) for line in lines)
    header_text = f"처리 중인 {doc_type}"
    header_display_width = get_display_width(header_text) + 4
    box_display_width = max(content_display_width, header_display_width) + 4

    print()
    # 상단 테두리
    header_dashes = box_display_width - get_display_width(header_text) - 3
    print(
        f"{Colors.BOLD}{Colors.WHITE}+- {header_text} {'-' * header_dashes}+{Colors.RESET}"
    )

    # 내용 출력
    for line in lines:
        line_display_width = get_display_width(line)
        padding_spaces = box_display_width - line_display_width - 2
        print(
            f"{Colors.BOLD}{Colors.WHITE}| {line}{' ' * padding_spaces}|{Colors.RESET}"
        )

    # 하단 테두리
    print(f"{Colors.BOLD}{Colors.WHITE}+{'-' * box_display_width}+{Colors.RESET}")
    print()


def print_numbered_list(items: List[str], start_index=1, highlight_color=Colors.CYAN):
    """번호가 매겨진 목록을 예쁘게 출력합니다."""
    for idx, item in enumerate(items):
        number = f"[{idx + start_index:02d}]"

        if get_display_width(item) > 60:
            words = item.split()
            lines = []
            current_line = ""

            for word in words:
                test_line = current_line + word + " " if current_line else word + " "
                if get_display_width(test_line) <= 55:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + " "

            if current_line:
                lines.append(current_line.strip())

            if lines:
                print(f"  {highlight_color}{number}{Colors.RESET} {lines[0]}")
                for line in lines[1:]:
                    print(f"      {line}")
        else:
            print(f"  {highlight_color}{number}{Colors.RESET} {item}")


def print_selection_menu(
    title: str, items: List[str], allow_skip=False, skip_text="목록에 없음"
):
    """선택 메뉴를 출력합니다."""
    print()
    print(
        f"{Colors.BOLD}{Colors.WHITE}+- {title} {'-' * (56 - get_display_width(title))}+{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.WHITE}|{' ' * 58}|{Colors.RESET}")
    print()

    print_numbered_list(items)

    if allow_skip:
        print(f"  {Colors.YELLOW}[00]{Colors.RESET} {skip_text}")

    print()
    print(f"{Colors.BOLD}{Colors.WHITE}+{'-' * 58}+{Colors.RESET}")
    print()


def get_styled_input(prompt: str, input_color=Colors.CYAN):
    """스타일이 적용된 입력을 받습니다."""
    try:
        return input(f"{input_color}{Symbols.ARROW} {prompt}{Colors.RESET}")
    except EOFError:
        print("\n프로그램을 종료합니다.")
        exit(0)
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
        exit(0)


def print_final_result(success_count: int, total_count: int):
    """최종 처리 결과를 출력합니다."""
    logger.info(f"처리 완료 - 성공: {success_count}/{total_count}")

    draw_header("처리 완료")

    if success_count == total_count:
        print_success(f"모든 문서 처리 완료: {success_count}/{total_count}")
    else:
        print_warning(f"일부 문서 처리 완료: {success_count}/{total_count}")
        print_error(f"실패: {total_count - success_count}건")

    print()


# ============================================================================
# 사용자 선택 및 입력 검증
# ============================================================================


class SelectionResult(Enum):
    """선택 결과를 나타내는 Enum."""

    SELECTED = auto()
    SKIPPED = auto()
    MANUAL_INPUT = auto()


def get_valid_selection(user_input: str, options: List[str]) -> str:
    """사용자 입력을 검증하고 유효한 옵션을 반환합니다."""
    try:
        selection = int(user_input) - 1
        if 0 <= selection < len(options):
            return options[selection]
        else:
            raise ValueError("유효하지 않은 번호입니다.")
    except ValueError:
        raise ValueError("유효하지 않은 입력입니다. 숫자를 입력해주세요.")


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
                logger.warning(f"유효하지 않은 번호 선택: {selection}")
                print("유효하지 않은 번호입니다. 다시 선택해주세요.")
        except ValueError:
            logger.warning(f"유효하지 않은 입력: {selection}")
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
            logger.info(f"사용자 선택 입력: '{selection}'")
            if selection == "0":
                logger.info("사용자가 추천 없음(0) 선택 - SKIPPED 반환")
                return SelectionResult.SKIPPED, None

            selected_index = int(selection) - 1
            if 0 <= selected_index < len(recommendations):
                return SelectionResult.SELECTED, recommendations[selected_index]
            else:
                logger.warning(f"유효하지 않은 번호 선택 (추천에서): {selection}")
                print("유효하지 않은 번호입니다. 다시 선택해주세요.")
        except ValueError:
            logger.warning(
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


def activate_cmd_window():
    """CMD 창을 활성화합니다 (사용자 상호작용 전)."""
    try:
        from pywinauto import Application

        # 방법 1: 창 제목으로 찾기 (bat 파일에서 title 설정한 경우)
        try:
            app = Application().connect(title="DocumentAutoClassifier")
            window = app.window(title="DocumentAutoClassifier")
            window.set_focus()
            logger.debug("창 제목으로 CMD 창 포커스 활성화 성공")
            return
        except Exception:
            pass

        # 방법 2: 현재 콘솔 창 핸들 사용 (기존 방법)
        console_hwnd = win32gui.GetConsoleWindow()
        if console_hwnd:
            win32gui.ShowWindow(console_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(console_hwnd)
            logger.debug("핸들로 CMD 창 포커스 활성화 성공")
        else:
            logger.debug("콘솔 창 핸들을 찾을 수 없습니다")
    except Exception as e:
        logger.debug(f"CMD 창 활성화 중 오류: {e}")
        pass


# ============================================================================
# 통합된 콘솔 인터페이스 클래스
# ============================================================================


class ConsoleInterface:
    """통합된 콘솔 사용자 인터페이스."""

    def __init__(self):
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

        print()
        print(f"{Colors.BOLD}{Colors.WHITE}+- 추천 확인 {'-' * 47}+{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.WHITE}|{' ' * 58}|{Colors.RESET}")
        print()

        print(f"  {Colors.DIM}공문 제목:{Colors.RESET} {title}")
        print(
            f"  {Colors.GREEN}추천 항목:{Colors.RESET} {Colors.BOLD}{recommended_task_title}{Colors.RESET}"
        )
        print()

        return confirm_choice("이 추천을 사용하시겠습니까?", default_yes=True)

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
            logger.info(f"삭제 가능한 {item_type}이 없습니다.")
            print(f"삭제 가능한 {item_type}이 없습니다.")
            input("엔터를 눌러 계속...")
            return []

        logger.info(f"저장된 {item_type} 목록 표시 ({len(items)}개)")

        print(
            f"\n{Colors.BOLD}{Colors.CYAN}+- 저장된 {item_type} 목록 {'-' * (40 - get_display_width(item_type))}+{Colors.RESET}"
        )
        print(f"{Colors.BOLD}{Colors.CYAN}|{' ' * 58}|{Colors.RESET}")
        for i, item in enumerate(items, 1):
            if item_type == "과제 카드":
                if len(item) >= 3:
                    title, task_title, registered_at = item[0], item[1], item[2]
                    print(
                        f"{Colors.CYAN}|{Colors.RESET} {i:2d}. {title} -> {task_title} [등록: {registered_at}]"
                    )
                else:
                    title, task_title = item[0], item[1]
                    print(
                        f"{Colors.CYAN}|{Colors.RESET} {i:2d}. {title} -> {task_title}"
                    )
            else:  # 접수 문서
                if len(item) >= 4:
                    title, approval, share, registered_at = (
                        item[0],
                        item[1],
                        item[2],
                        item[3],
                    )
                    print(
                        f"{Colors.CYAN}|{Colors.RESET} {i:2d}. {title} (담당: {approval}, 공람: {share}) [등록: {registered_at}]"
                    )
                else:
                    title, approval, share = item[0], item[1], item[2]
                    print(
                        f"{Colors.CYAN}|{Colors.RESET} {i:2d}. {title} (담당: {approval}, 공람: {share})"
                    )

        print(f"{Colors.BOLD}{Colors.CYAN}+{'-' * 58}+{Colors.RESET}")

        print(
            f"\n{Colors.DIM}삭제할 항목 번호를 입력하세요 (여러 개는 쉼표로 구분, 전체 삭제는 'all', 취소는 'q'):{Colors.RESET}"
        )
        user_input = get_styled_input("선택: ").strip()

        if user_input.lower() == "q":
            return []
        elif user_input.lower() == "all":
            if confirm_choice(
                f"모든 {item_type}을 삭제하시겠습니까?", default_yes=False
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
                        logger.warning(f"잘못된 번호 입력: {num_str.strip()}")
                        print(f"잘못된 번호: {num_str.strip()}")

                if indices and confirm_choice(
                    f"선택한 {len(indices)}개 항목을 삭제하시겠습니까?",
                    default_yes=False,
                ):
                    logger.info(f"{len(indices)}개 항목 삭제 확인됨")
                    return indices
                else:
                    return []
            except ValueError:
                logger.warning("사용자가 올바르지 않은 숫자 입력")
                print("올바른 숫자를 입력해주세요.")
                input("엔터를 눌러 계속...")
                return []

    def get_title_for_deletion(self, item_type: str) -> Optional[str]:
        """삭제할 항목의 제목을 직접 입력받습니다."""
        activate_cmd_window()
        clear_screen()

        logger.info(f"{item_type} 개별 삭제 시작")

        print(
            f"\n{Colors.BOLD}{Colors.CYAN}+- {item_type} 개별 삭제 {'-' * (38 - get_display_width(item_type))}+{Colors.RESET}"
        )
        print(f"{Colors.BOLD}{Colors.CYAN}|{' ' * 58}|{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}+{'-' * 58}+{Colors.RESET}")

        title = get_styled_input(f"삭제할 {item_type}의 제목을 입력하세요: ").strip()

        if title and confirm_choice(
            f"'{title}' {item_type}을/를 삭제하시겠습니까?", default_yes=False
        ):
            logger.info(f"{item_type} 삭제 확인: {title}")
            return title
        return None

    def confirm_bulk_deletion(self) -> bool:
        """일괄 삭제를 확인합니다."""
        activate_cmd_window()
        clear_screen()

        print(
            f"\n{Colors.RED}╔═══════════════════════════════════════════╗{Colors.RESET}"
        )
        print(
            f"{Colors.RED}║{Colors.BOLD}{Colors.WHITE}    ⚠️  일괄 삭제 경고    {Colors.RESET}{Colors.RED}║{Colors.RESET}"
        )
        print(
            f"{Colors.RED}╚═══════════════════════════════════════════╝{Colors.RESET}"
        )
        print(f"{Colors.YELLOW}모든 과제 카드와 접수 문서가 삭제됩니다.{Colors.RESET}")
        print(f"{Colors.YELLOW}이 작업은 되돌릴 수 없습니다.{Colors.RESET}")
        print()

        return confirm_choice(
            "정말로 모든 데이터를 삭제하시겠습니까?", default_yes=False
        )

    # ========================================================================
    # 기타 유틸리티 메서드
    # ========================================================================

    def print_final_result(self, success_count: int, total_count: int):
        """최종 처리 결과를 출력합니다."""
        logger.info(f"처리 완료 - 성공: {success_count}/{total_count}")

        draw_header("처리 완료")

        if success_count == total_count:
            print_success(f"모든 문서 처리 완료: {success_count}/{total_count}")
        else:
            print_warning(f"일부 문서 처리 완료: {success_count}/{total_count}")
            print_error(f"실패: {total_count - success_count}건")

        print()

    def wait_for_enter(self, message="계속하려면 Enter를 누르세요..."):
        """Enter 키 대기."""
        input(f"\n{Colors.DIM}{message}{Colors.RESET}")
