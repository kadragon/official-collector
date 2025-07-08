"""
사용자의 입력이 필요한 부분에 대한 제어.
"""

from enum import Enum, auto
from typing import Dict, Tuple, List, Optional
from services.command_executor import CommandExecutor


class SelectionStatus(Enum):
    """Dialog ahanlder의 선택 상태를 나타내는 Enum."""
    SELECTED = auto()
    SKIPPED = auto()
    MANUAL_INPUT = auto()


class DialogHandler:
    """과제카드 선택을 담당하는 클래스."""

    def __init__(self) -> None:
        """초기화 및 CMD 창 활성화."""
        self.cmd = CommandExecutor()
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

        num_columns = 3
        col_width = 40  # Adjust this width as needed

        for i in range(0, len(sorted_card_list), num_columns):
            row_str = ""
            for j in range(num_columns):
                idx = i + j
                if idx < len(sorted_card_list):
                    item_str = f"[{idx:02d}] {sorted_card_list[idx]}"
                    row_str += item_str.ljust(col_width)
            print(row_str)

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

    def choose_from_predefined_list(self, title: str, card_list: List[str]) -> Tuple[SelectionStatus, Optional[str]]:
        """
        과제 카드를 추천할 수 없을 때, 미리 정의된 목록을 보여주고 사용자에게 선택하도록 합니다.
        """
        self.cmd.activate()
        print(f"\n'{title}'에 대한 과제 카드를 찾거나 추천할 수 없을 때, 다음 목록에서 선택해주세요.")

        for idx, card_name in enumerate(card_list):
            print(f"[{idx + 1:02d}] {card_name}")

        print("[0] 직접 입력")
        print()

        while True:
            try:
                selection = input("번호를 선택하세요: ")
                if selection == '0':
                    return SelectionStatus.MANUAL_INPUT, None

                selected_index = int(selection) - 1
                if 0 <= selected_index < len(card_list):
                    return SelectionStatus.SELECTED, card_list[selected_index]
                else:
                    print("유효하지 않은 번호입니다. 다시 선택해주세요.")
            except ValueError:
                print("유효하지 않은 입력입니다. 번호를 입력해주세요.")

    def choose_from_recommendations(self, title: str, recommendations: List[str]) -> Tuple[SelectionStatus, Optional[str]]:
        """
        사용자에게 추천된 과제 카드 목록을 보여주고 선택하도록 합니다.
        """
        self.cmd.activate()
        print(f"\n'{title}'에 대한 과제 카드 추천 목록입니다. 선택해주세요.")

        for idx, card_name in enumerate(recommendations):
            print(f"[{idx + 1:02d}] {card_name}")

        print("[0] 추천 없음 (다음 단계로 이동)")
        print()

        while True:
            try:
                selection = input("번호를 선택하세요: ")
                if selection == "0":
                    return SelectionStatus.SKIPPED, None  # No recommendation chosen, proceed to next step

                selected_index = int(selection) - 1
                if 0 <= selected_index < len(recommendations):
                    return SelectionStatus.SELECTED, recommendations[selected_index]
                else:
                    print("유효하지 않은 번호입니다. 다시 선택해주세요.")
            except ValueError:
                print("유효하지 않은 입력입니다. 번호를 입력해주세요.")