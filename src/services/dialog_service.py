
"""
사용자의 입력이 필요한 부분에 대한 제어.
"""

from typing import Dict, Tuple, List, Optional
from services.command_executor import CommandExecutor
from utils.input_validator import (
    SelectionResult, 
    get_valid_selection, 
    get_user_choice_from_list,
    get_user_choice_from_recommendations,
    get_manual_input,
    confirm_choice
)
from utils.string_processor import format_option_display


class DialogHandler:
    """과제카드 선택을 담당하는 클래스."""

    def __init__(self) -> None:
        """초기화 및 CMD 창 활성화."""
        self.cmd = CommandExecutor()

    

    def select_approval_and_share(self, approval_list: List[str], share_list: List[str]) -> Tuple[str, str]:
        """
        사용자에게 담당자와 공람대상자를 선택하도록 요청합니다.

        Args:
            approval_list (List[str]): 선택 가능한 담당자 목록.
            share_list (List[str]): 선택 가능한 공람 대상자 목록.

        Returns:
            Tuple[str, str]: (선택된 담당자, 선택된 공람 대상자)
        """
        self.cmd.activate()

        if len(approval_list) == 1:
            selected_approval = approval_list[0]
        else:
            # 담당자 선택
            print("\n[담당자 선택]")
            for idx, name in enumerate(approval_list):
                print(f"[{idx}] {name}")

            selected_approval = get_valid_selection("번호를 선택하세요: ", approval_list)

        # 공람 대상자 선택
        print("\n[공람자 선택]")
        print(format_option_display(share_list))

        selected_share = get_valid_selection("번호를 선택하세요: ", share_list)

        return selected_approval, selected_share


    def confirm_recommendation(self, title: str, recommended_task_title: str) -> bool:
        """
        사용자에게 추천된 taskTitle을 확인할지 묻습니다.
        """
        self.cmd.activate()
        print(f"공문 제목: {title}")
        print(f"추천 과제 카드: {recommended_task_title}")
        return confirm_choice("이 추천을 사용하시겠습니까?", default_yes=True)

    def choose_from_predefined_list(self, title: str, card_list: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """
        When task cards cannot be recommended, this method displays a predefined list for the user to choose from.
        """
        self.cmd.activate()
        return get_user_choice_from_list(title, card_list, allow_skip=True)

    def choose_from_full_list(self, title: str, card_list: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """
        Displays the full list of task cards for the user to choose from.
        """
        self.cmd.activate()
        return get_user_choice_from_list(title, card_list, allow_skip=False)

    def choose_from_recommendations(self, title: str, recommendations: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """
        사용자에게 추천된 과제 카드 목록을 보여주고 선택하도록 합니다.
        """
        self.cmd.activate()
        return get_user_choice_from_recommendations(title, recommendations)

    def get_manual_task_card(self, title: str) -> Optional[str]:
        """
        사용자로부터 직접 과제 카드 이름을 입력받습니다.
        """
        self.cmd.activate()
        print(f"\n'{title}'에 대한 과제 카드를 직접 입력해주세요.")
        return get_manual_input("과제 카드 이름: ")
