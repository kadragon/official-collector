"""
User Interaction Manager

사용자와의 상호작용을 담당하는 UI 컴포넌트들을 제공합니다.
과제카드 선택, 추천 확인 등의 사용자 인터페이스 기능과
사용자 입력 검증 및 선택 메뉴 기능을 통합하여 제공합니다.
"""

import logging
import subprocess
from enum import Enum, auto
from typing import Tuple, List, Optional
from utils.error_handler import setup_logger
from .terminal_ui import (
    clear_screen,
    print_document_info,
    print_selection_menu,
    print_recommendation_menu,
    get_styled_input,
    print_success,
    draw_separator
)

logger = setup_logger(__name__)


# ============================================================================
# 입력 검증 및 선택 관련 클래스/함수 (기존 input_validator.py)
# ============================================================================

class SelectionResult(Enum):
    """선택 결과를 나타내는 Enum."""
    SELECTED = auto()
    SKIPPED = auto()
    MANUAL_INPUT = auto()


def get_valid_selection(user_input: str, options: List[str]) -> str:
    """
    사용자 입력을 검증하고 유효한 옵션을 반환합니다.

    Args:
        user_input (str): 사용자가 입력한 값.
        options (List[str]): 선택 가능한 옵션 리스트.

    Returns:
        str: 사용자가 선택한 옵션.
    """
    try:
        selection = int(user_input) - 1  # 1-based to 0-based
        if 0 <= selection < len(options):
            return options[selection]
        else:
            raise ValueError("유효하지 않은 번호입니다.")
    except ValueError:
        raise ValueError("유효하지 않은 입력입니다. 숫자를 입력해주세요.")


def display_numbered_options(options: List[str], start_index: int = 1, show_skip_option: bool = False) -> None:
    """
    번호가 매겨진 옵션 목록을 표시합니다.

    Args:
        options (List[str]): 표시할 옵션 목록.
        start_index (int): 시작 번호 (기본값: 1).
        show_skip_option (bool): "목록에 없음" 옵션을 표시할지 여부.
    """
    logger.debug(f"옵션 목록 표시: {len(options)}개 항목")
    
    for idx, option in enumerate(options):
        print(f"[{idx + start_index:02d}] {option}")

    if show_skip_option:
        print("[0] 목록에 없음")


def get_user_choice_from_list(title: str, options: List[str], allow_skip: bool = False) -> Tuple[SelectionResult, Optional[str]]:
    """
    사용자에게 목록에서 선택하도록 합니다.

    Args:
        title (str): 선택 대상의 제목.
        options (List[str]): 선택 가능한 옵션 목록.
        allow_skip (bool): 건너뛰기 옵션을 허용할지 여부.

    Returns:
        Tuple[SelectionResult, Optional[str]]: (선택 결과, 선택된 값)
    """
    skip_text = "목록에 없음" if allow_skip else None
    print_selection_menu("목록에서 선택", options, allow_skip, skip_text)

    while True:
        try:
            selection = get_styled_input("번호를 선택하세요: ")

            if allow_skip and selection == '0':
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


def get_user_choice_from_recommendations(title: str, recommendations: List[str]) -> Tuple[SelectionResult, Optional[str]]:
    """
    사용자에게 추천 목록에서 선택하도록 합니다.

    Args:
        title (str): 선택 대상의 제목.
        recommendations (List[str]): 추천 목록.

    Returns:
        Tuple[SelectionResult, Optional[str]]: (선택 결과, 선택된 값)
    """
    print_selection_menu("추천 목록", recommendations, allow_skip=True, skip_text="추천 없음 (다음 단계로 이동)")

    while True:
        try:
            selection = get_styled_input("번호를 선택하세요: ")
            if selection == "0":
                return SelectionResult.SKIPPED, None

            selected_index = int(selection) - 1
            if 0 <= selected_index < len(recommendations):
                return SelectionResult.SELECTED, recommendations[selected_index]
            else:
                logger.warning(f"유효하지 않은 번호 선택 (추천에서): {selection}")
                print("유효하지 않은 번호입니다. 다시 선택해주세요.")
        except ValueError:
            logger.warning(f"유효하지 않은 입력 (추천에서): {selection}")
            print("유효하지 않은 입력입니다. 번호를 입력해주세요.")


def get_manual_input(prompt: str) -> Optional[str]:
    """
    사용자로부터 직접 입력을 받습니다.

    Args:
        prompt (str): 입력 프롬프트 메시지.

    Returns:
        Optional[str]: 사용자가 입력한 값.
    """
    return input(prompt)


def confirm_choice(message: str, default_yes: bool = True) -> bool:
    """
    사용자에게 예/아니오 확인을 요청합니다.

    Args:
        message (str): 확인 메시지.
        default_yes (bool): 기본값이 예인지 여부.

    Returns:
        bool: 사용자의 선택 (True: 예, False: 아니오).
    """
    prompt_suffix = " (Y/n): " if default_yes else " (y/N): "
    confirm = input(message + prompt_suffix)

    if not confirm:  # 빈 입력인 경우 기본값 사용
        return default_yes

    return confirm.lower() == 'y'


class UserInteractionManager:
    """사용자 상호작용을 담당하는 클래스."""

    def __init__(self) -> None:
        """초기화."""
        pass  # CMD 창 활성화는 필요시 직접 처리

    def select_approval_and_share(self, approval_list: List[str],
                                  share_list: List[str]) -> Tuple[str, str]:
        """
        사용자에게 담당자와 공람대상자를 선택하도록 요청합니다.

        Args:
            approval_list (List[str]): 선택 가능한 담당자 목록.
            share_list (List[str]): 선택 가능한 공람 대상자 목록.

        Returns:
            Tuple[str, str]: (선택된 담당자, 선택된 공람 대상자)
        """
        # CMD 창 활성화 (간단한 방법)
        try:
            subprocess.run('cmd /c echo', shell=True, capture_output=True)
        except:
            pass
        clear_screen()

        if len(approval_list) == 1:
            selected_approval = approval_list[0]
            print_success(f"담당자 자동 선택: {selected_approval}")
        else:
            print_selection_menu("담당자 선택", approval_list)
            while True:
                try:
                    user_input = get_styled_input("번호를 선택하세요: ")
                    selected_approval = get_valid_selection(
                        user_input, approval_list)
                    break
                except ValueError as e:
                    print(str(e))

        draw_separator()
        print_selection_menu("공람자 선택", share_list)
        while True:
            try:
                user_input = get_styled_input("번호를 선택하세요: ")
                selected_share = get_valid_selection(user_input, share_list)
                break
            except ValueError as e:
                print(str(e))

        return selected_approval, selected_share

    def confirm_recommendation(self, title: str, recommended_task_title: str) -> bool:
        """
        사용자에게 추천된 taskTitle을 확인할지 묻습니다.
        """
        # CMD 창 활성화 (간단한 방법)
        try:
            subprocess.run('cmd /c echo', shell=True, capture_output=True)
        except:
            pass
        clear_screen()
        print_recommendation_menu(title, recommended_task_title)
        return confirm_choice(get_styled_input("이 추천을 사용하시겠습니까? (Y/n): "), default_yes=True)

    def choose_from_predefined_list(self, title: str, card_list: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """
        When task cards cannot be recommended, this method displays a predefined list for the user to choose from.
        """
        # CMD 창 활성화 (간단한 방법)
        try:
            subprocess.run('cmd /c echo', shell=True, capture_output=True)
        except:
            pass
        clear_screen()
        print_document_info(title, "과제 카드 선택")
        return get_user_choice_from_list(title, card_list, allow_skip=True)

    def choose_from_full_list(self, title: str, card_list: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """
        Displays the full list of task cards for the user to choose from.
        """
        # CMD 창 활성화 (간단한 방법)
        try:
            subprocess.run('cmd /c echo', shell=True, capture_output=True)
        except:
            pass
        clear_screen()
        print_document_info(title, "전체 목록에서 선택")
        sorted_card_list = sorted(card_list)
        return get_user_choice_from_list(title, sorted_card_list, allow_skip=False)

    def choose_from_recommendations(self, title: str, recommendations: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """
        사용자에게 추천된 과제 카드 목록을 보여주고 선택하도록 합니다.
        """
        # CMD 창 활성화 (간단한 방법)
        try:
            subprocess.run('cmd /c echo', shell=True, capture_output=True)
        except:
            pass
        clear_screen()
        print_document_info(title, "추천 목록")
        return get_user_choice_from_recommendations(title, recommendations)

    def get_manual_task_card(self, title: str) -> Optional[str]:
        """
        사용자로부터 직접 과제 카드 이름을 입력받습니다.
        """
        # CMD 창 활성화 (간단한 방법)
        try:
            subprocess.run('cmd /c echo', shell=True, capture_output=True)
        except:
            pass
        clear_screen()
        print_document_info(title, "직접 입력")
        return get_manual_input(get_styled_input("과제 카드 이름: "))