"""
사용자 입력 검증 및 선택 메뉴를 위한 유틸리티 모듈.
"""

from typing import List, Optional, Tuple
from enum import Enum, auto


class SelectionResult(Enum):
    """선택 결과를 나타내는 Enum."""
    SELECTED = auto()
    SKIPPED = auto()
    MANUAL_INPUT = auto()


def get_valid_selection(prompt: str, options: List[str]) -> str:
    """
    사용자에게 유효한 입력을 받을 때까지 반복 요청합니다.

    Args:
        prompt (str): 입력 프롬프트 메시지.
        options (List[str]): 선택 가능한 옵션 리스트.

    Returns:
        str: 사용자가 선택한 옵션.
    """
    while True:
        try:
            selection = int(input(prompt))
            if 0 <= selection < len(options):
                return options[selection]
            print("유효하지 않은 번호입니다. 다시 선택해주세요.")
        except ValueError:
            print("숫자를 입력해주세요.")


def display_numbered_options(options: List[str], start_index: int = 1, show_skip_option: bool = False) -> None:
    """
    번호가 매겨진 옵션 목록을 표시합니다.

    Args:
        options (List[str]): 표시할 옵션 목록.
        start_index (int): 시작 번호 (기본값: 1).
        show_skip_option (bool): "목록에 없음" 옵션을 표시할지 여부.
    """
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
    print(f"\n목록에서 선택해주세요.")
    display_numbered_options(options, show_skip_option=allow_skip)
    print()

    while True:
        try:
            selection = input("번호를 선택하세요: ")
            
            if allow_skip and selection == '0':
                return SelectionResult.SKIPPED, None

            selected_index = int(selection) - 1
            if 0 <= selected_index < len(options):
                return SelectionResult.SELECTED, options[selected_index]
            else:
                print("유효하지 않은 번호입니다. 다시 선택해주세요.")
        except ValueError:
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
    print(f"\n'{title}'에 대한 추천 목록입니다. 선택해주세요.")
    display_numbered_options(recommendations)
    print("[0] 추천 없음 (다음 단계로 이동)")
    print()

    while True:
        try:
            selection = input("번호를 선택하세요: ")
            if selection == "0":
                return SelectionResult.SKIPPED, None

            selected_index = int(selection) - 1
            if 0 <= selected_index < len(recommendations):
                return SelectionResult.SELECTED, recommendations[selected_index]
            else:
                print("유효하지 않은 번호입니다. 다시 선택해주세요.")
        except ValueError:
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