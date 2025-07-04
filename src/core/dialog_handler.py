"""
사용자의 입력이 필요한 부분에 대한 제어.
"""

from typing import Dict, Tuple, List, Optional
from core.cmd_control import CmdControl


class DialogHandler:
    """과제카드 선택을 담당하는 클래스."""

    def __init__(self) -> None:
        """초기화 및 CMD 창 활성화."""
        self.cmd = CmdControl()
        self.ai = None

    def choose_task_card(self, card_data: Dict[str, str]) -> str:
        """
        사용자가 과제카드를 선택하도록 유도하는 함수.

        Args:
            card_data (Dict[str, str]): 선택할 수 있는 과제카드 목록.

        Returns:
            str: 선택된 과제카드의 이름.
        """
        self.cmd.activate()

        card_list = list(card_data.keys())

        sorted_card_list = sorted(card_list)

        for idx, card_name in enumerate(sorted_card_list):
            print(f"[{idx:02d}] {card_name}")

        print()
        return self._get_valid_input("번호를 선택하세요: ", sorted_card_list)

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

        # 담당자 선택
        print("\n[담당자 선택]")
        for idx, name in enumerate(approval_list):
            print(f"[{idx}] {name}")

        selected_approval = self._get_valid_input("번호를 선택하세요: ", approval_list)

        # 기본 공람 대상자 (공람 없음)
        selected_share = "공람없음"

        # 담당자가 특정 범위 내에 있으면 공람 대상자도 선택
        if approval_list.index(selected_approval) < 2:
            print("\n[공람자 선택]")
            print(" / ".join(f"[{idx}] {name}" for idx,
                  name in enumerate(share_list)))

            selected_share = self._get_valid_input("번호를 선택하세요: ", share_list)

        return selected_approval, selected_share

    @staticmethod
    def _get_valid_input(prompt: str, options: List[str]) -> str:
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

    def check_valid_sort(self, title: str, sort_info) -> bool:
        self.cmd.activate()
        print(f'{title} -> {sort_info}')
        confirm = input("분류 하시겠습니까?( Enter / n)")

        if confirm.lower() == 'n':
            return False

        return True

    def confirm_recommendation(self, title: str, recommended_task_title: str) -> bool:
        """
        사용자에게 추천된 taskTitle을 확인할지 묻습니다.
        """
        self.cmd.activate()
        print(f"공문 제목: {title}")
        print(f"추천 과제 카드: {recommended_task_title}")
        confirm = input("이 추천을 사용하시겠습니까? (Y/n): ")
        return confirm.lower() == 'y' or confirm == '' # Default to 'Y' if Enter is pressed

    def get_manual_task_card(self, title: str) -> str:
        """
        사용자로부터 taskTitle을 수동으로 입력받습니다.
        """
        self.cmd.activate()
        print(f"'{title}'에 대한 과제 카드를 찾거나 추천할 수 없습니다.")
        manual_input = input("과제 카드 이름을 직접 입력해주세요 (취소하려면 Enter): ")
        return manual_input.strip()

    def choose_from_predefined_list(self, title: str, card_list: List[str]) -> Optional[str]:
        """
        과제 카드를 추천할 수 없을 때, 미리 정의된 목록을 보여주고 사용자에게 선택하도록 합니다.
        """
        self.cmd.activate()
        print(f"\n'{title}'에 대한 과제 카드를 찾거나 추천할 수 없습니다. 다음 목록에서 선택해주세요.")
        
        for idx, card_name in enumerate(card_list):
            print(f"[{idx + 1:02d}] {card_name}")
        
        print("[00] 직접 입력")
        print()

        while True:
            try:
                selection = input("번호를 선택하거나 직접 입력하세요: ")
                if selection == '00':
                    return None # Indicates manual input is desired
                
                selected_index = int(selection) - 1
                if 0 <= selected_index < len(card_list):
                    return card_list[selected_index]
                else:
                    print("유효하지 않은 번호입니다. 다시 선택해주세요.")
            except ValueError:
                print("유효하지 않은 입력입니다. 번호를 입력하거나 '00'을 입력해주세요.")

    def choose_from_recommendations(self, title: str, recommendations: List[str]) -> Optional[str]:
        """
        사용자에게 추천된 과제 카드 목록을 보여주고 선택하도록 합니다.
        """
        self.cmd.activate()
        print(f"\n'{title}'에 대한 과제 카드 추천 목록입니다. 선택해주세요.")
        
        for idx, card_name in enumerate(recommendations):
            print(f"[{idx + 1:02d}] {card_name}")
        
        print("[00] 목록에 없음 (직접 입력)")
        print("[0] 추천 없음 (다음 단계로 이동)")
        print()

        while True:
            try:
                selection = input("번호를 선택하거나 '00' 또는 '0'을 입력하세요: ")
                if selection == '00':
                    return "MANUAL_INPUT" # Special signal for manual input
                elif selection == '0':
                    return None # No recommendation chosen, proceed to next step
                
                selected_index = int(selection) - 1
                if 0 <= selected_index < len(recommendations):
                    return recommendations[selected_index]
                else:
                    print("유효하지 않은 번호입니다. 다시 선택해주세요.")
            except ValueError:
                print("유효하지 않은 입력입니다. 번호를 입력하거나 '00' 또는 '0'을 입력해주세요.")