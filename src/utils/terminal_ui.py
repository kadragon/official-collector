"""
터미널 UI 개선을 위한 유틸리티 모듈.
"""

import os
import logging
from typing import List


class Colors:
    """터미널 컬러 코드."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # 기본 색상
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'


class Symbols:
    """터미널 심볼."""
    ARROW = "->"
    INFO = "[INFO]"
    WARNING = "[WARN]"
    ERROR = "[ERROR]"
    SUCCESS = "[OK]"


def get_display_width(text: str) -> int:
    """텍스트의 실제 표시 너비를 계산합니다 (한글 고려)."""
    width = 0
    for char in text:
        # 한글, 중국어, 일본어 등은 2칸, 나머지는 1칸
        if ord(char) > 127:  # ASCII가 아닌 문자
            width += 2
        else:
            width += 1
    return width


def clear_screen():
    """화면을 지웁니다."""
    try:
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        # Fallback: print newlines to simulate clearing
        print('\n' * 50)


def draw_separator(char='─', width=60):
    """구분선을 그립니다."""
    print(char * width)


def draw_header(title: str, width=60):
    """헤더를 그립니다."""
    print()
    print("=" * width)
    print(f"{title:^{width}}")
    print("=" * width)
    print()


def draw_section_header(title: str, width=60):
    """섹션 헤더를 그립니다."""
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'─' * width}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'─' * width}{Colors.RESET}")
    print()


def print_info(message: str):
    """정보 메시지를 출력합니다."""
    logger = logging.getLogger(__name__)
    logger.info(message)
    print(f"{Colors.BLUE}{Symbols.INFO} {message}{Colors.RESET}")


def print_success(message: str):
    """성공 메시지를 출력합니다."""
    logger = logging.getLogger(__name__)
    logger.info(f"SUCCESS: {message}")
    print(f"{Colors.GREEN}{Symbols.SUCCESS} {message}{Colors.RESET}")


def print_warning(message: str):
    """경고 메시지를 출력합니다."""
    logger = logging.getLogger(__name__)
    logger.warning(message)
    print(f"{Colors.YELLOW}{Symbols.WARNING} {message}{Colors.RESET}")


def print_error(message: str):
    """에러 메시지를 출력합니다."""
    logger = logging.getLogger(__name__)
    logger.error(message)
    print(f"{Colors.RED}{Symbols.ERROR} {message}{Colors.RESET}")


def print_document_info(title: str, doc_type: str = "문서"):
    """문서 정보를 예쁘게 출력합니다."""
    logger = logging.getLogger(__name__)
    logger.info(f"처리 중인 {doc_type}: {title}")
    
    # 터미널 너비를 고려한 최대 표시 너비 설정
    max_display_width = 60

    # 제목이 너무 길면 줄바꿈 처리
    if get_display_width(title) > max_display_width - 4:  # 여백을 고려한 실제 내용 너비
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

    # 박스 너비 계산 (가장 긴 줄의 표시 너비 기준)
    content_display_width = max(get_display_width(line) for line in lines)
    header_text = f"처리 중인 {doc_type}"
    header_display_width = get_display_width(header_text) + 4

    # 박스 실제 너비는 표시 너비와 동일하게 설정
    box_display_width = max(content_display_width, header_display_width) + 4

    print()
    # 상단 테두리
    header_dashes = box_display_width - get_display_width(header_text) - 3
    print(f"{Colors.BOLD}{Colors.WHITE}┌─ {header_text} {'─' * header_dashes}┐{Colors.RESET}")

    # 내용 출력
    for line in lines:
        line_display_width = get_display_width(line)
        padding_spaces = box_display_width - line_display_width - 2
        print(f"{Colors.BOLD}{Colors.WHITE}│ {line}{' ' * padding_spaces}│{Colors.RESET}")

    # 하단 테두리
    print(f"{Colors.BOLD}{Colors.WHITE}└{'─' * box_display_width}┘{Colors.RESET}")
    print()


def print_numbered_list(items: List[str], start_index=1, highlight_color=Colors.CYAN):
    """번호가 매겨진 목록을 예쁘게 출력합니다."""
    for idx, item in enumerate(items):
        number = f"[{idx + start_index:02d}]"

        # 항목이 너무 길면 줄바꿈 처리
        if get_display_width(item) > 60:
            words = item.split()
            lines = []
            current_line = ""

            for word in words:
                test_line = current_line + word + " " if current_line else word + " "
                if get_display_width(test_line) <= 55:  # 들여쓰기 고려
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + " "

            if current_line:
                lines.append(current_line.strip())

            # 첫 번째 줄은 번호와 함께 출력
            if lines:
                print(f"  {highlight_color}{number}{Colors.RESET} {lines[0]}")
                # 나머지 줄들은 들여쓰기하여 출력
                for line in lines[1:]:
                    print(f"      {line}")
        else:
            # 짧은 항목은 그대로 출력
            print(f"  {highlight_color}{number}{Colors.RESET} {item}")


def print_selection_menu(title: str, items: List[str], allow_skip=False, skip_text="목록에 없음"):
    """선택 메뉴를 예쁘게 출력합니다."""
    draw_section_header(title)

    print_numbered_list(items)

    if allow_skip:
        print(f"  {Colors.YELLOW}[00]{Colors.RESET} {skip_text}")

    print()


def print_recommendation_menu(title: str, recommended_item: str):
    """추천 확인 메뉴를 예쁘게 출력합니다."""
    draw_section_header("추천 확인")

    print(f"  {Colors.DIM}공문 제목:{Colors.RESET} {title}")
    print(f"  {Colors.GREEN}추천 항목:{Colors.RESET} {Colors.BOLD}{recommended_item}{Colors.RESET}")
    print()


def get_styled_input(prompt: str, input_color=Colors.CYAN):
    """스타일이 적용된 입력을 받습니다."""
    return input(f"{input_color}{Symbols.ARROW} {prompt}{Colors.RESET}")


def print_processing_status(step: str, current: int, total: int):
    """처리 상태를 출력합니다."""
    percentage = (current / total) * 100 if total > 0 else 0
    bar_length = 30
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = '█' * filled_length + '░' * (bar_length - filled_length)

    print(f"\r{Colors.BLUE}{step}{Colors.RESET} [{bar}] {percentage:.1f}% ({current}/{total})", end='', flush=True)


def wait_for_enter(message="계속하려면 Enter를 누르세요..."):
    """Enter 키 대기."""
    input(f"\n{Colors.DIM}{message}{Colors.RESET}")


def print_final_result(success_count: int, total_count: int):
    """최종 결과를 출력합니다."""
    logger = logging.getLogger(__name__)
    logger.info(f"처리 완료 - 성공: {success_count}/{total_count}")
    
    draw_header("처리 완료")

    if success_count == total_count:
        print_success(f"모든 문서 처리 완료: {success_count}/{total_count}")
    else:
        print_warning(f"일부 문서 처리 완료: {success_count}/{total_count}")
        print_error(f"실패: {total_count - success_count}건")

    print()
