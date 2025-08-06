"""
User Interaction Manager

사용자와의 상호작용을 담당하는 UI 컴포넌트들을 제공합니다.
과제카드 선택, 추천 확인 등의 사용자 인터페이스 기능을 담당합니다.
"""

from .terminal_ui import (
    clear_screen,
    print_document_info,
    print_selection_menu,
    print_recommendation_menu,
    get_styled_input,
    print_success,
    draw_separator
)
from utils.input_validator import (
    SelectionResult,
    get_valid_selection,
    get_user_choice_from_list,
    get_user_choice_from_recommendations,
    get_manual_input,
    confirm_choice
)
from typing import Tuple, List, Optional
from services.command_service import CommandExecutor
from utils.error_handler import setup_logger

logger = setup_logger(__name__)


class UserInteractionManager:
    """사용자 상호작용을 담당하는 클래스."""

    def __init__(self) -> None:
        """초기화 및 CMD 창 활성화."""
        self.cmd = CommandExecutor()

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
        self.cmd.activate()
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
        self.cmd.activate()
        clear_screen()
        print_recommendation_menu(title, recommended_task_title)
        return confirm_choice(get_styled_input("이 추천을 사용하시겠습니까? (Y/n): "), default_yes=True)

    def choose_from_predefined_list(self, title: str, card_list: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """
        When task cards cannot be recommended, this method displays a predefined list for the user to choose from.
        """
        self.cmd.activate()
        clear_screen()
        print_document_info(title, "과제 카드 선택")
        return get_user_choice_from_list(title, card_list, allow_skip=True)

    def choose_from_full_list(self, title: str, card_list: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """
        Displays the full list of task cards for the user to choose from.
        """
        self.cmd.activate()
        clear_screen()
        print_document_info(title, "전체 목록에서 선택")
        sorted_card_list = sorted(card_list)
        return get_user_choice_from_list(title, sorted_card_list, allow_skip=False)

    def choose_from_recommendations(self, title: str, recommendations: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """
        사용자에게 추천된 과제 카드 목록을 보여주고 선택하도록 합니다.
        """
        self.cmd.activate()
        clear_screen()
        print_document_info(title, "추천 목록")
        return get_user_choice_from_recommendations(title, recommendations)

    def get_manual_task_card(self, title: str) -> Optional[str]:
        """
        사용자로부터 직접 과제 카드 이름을 입력받습니다.
        """
        self.cmd.activate()
        clear_screen()
        print_document_info(title, "직접 입력")
        return get_manual_input(get_styled_input("과제 카드 이름: "))