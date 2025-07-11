
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

            selected_approval = self._get_valid_input("번호를 선택하세요: ", approval_list)

        # 기본 공람 대상자 (공람 없음)
        selected_share = "공람없음"

        # 공람 대상자 선택은 항상 진행
        print("\n[공람자 선택]")
        print(" / ".join(f"[{idx}] {name}" for idx,
              name in enumerate(share_list)))

        selected_share = self._get_valid_input("번호를 선택하세요: ", share_list)

        return selected_approval, selected_share

    def _get_valid_input(self, prompt: str, options: List[str]) -> str:
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
        When task cards cannot be recommended, this method displays a predefined list for the user to choose from.
        """
        self.cmd.activate()
        print(f"\n다음 목록에서 선택해주세요.")

        for idx, card_name in enumerate(card_list):
            print(f"[{idx + 1:02d}] {card_name}")

        print("[0] 목록에 없음")
        print()

        while True:
            try:
                selection = input("번호를 선택하세요: ")
                if selection == '0':
                    return SelectionStatus.SKIPPED, None

                selected_index = int(selection) - 1
                if 0 <= selected_index < len(card_list):
                    return SelectionStatus.SELECTED, card_list[selected_index]
                else:
                    print("유효하지 않은 번호입니다. 다시 선택해주세요.")
            except ValueError:
                print("유효하지 않은 입력입니다. 번호를 입력해주세요.")

    def choose_from_full_list(self, title: str, card_list: List[str]) -> Tuple[SelectionStatus, Optional[str]]:
        """
        Displays the full list of task cards for the user to choose from.
        """
        self.cmd.activate()
        print(f"\n전체 목록에서 선택해주세요.")

        for idx, card_name in enumerate(card_list):
            print(f"[{idx + 1:02d}] {card_name}")

        print()

        while True:
            try:
                selection = input("번호를 선택하세요: ")
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

    def get_manual_task_card(self, title: str) -> Optional[str]:
        """
        사용자로부터 직접 과제 카드 이름을 입력받습니다.
        """
        self.cmd.activate()
        print(f"\n'{title}'에 대한 과제 카드를 직접 입력해주세요.")
        return input("과제 카드 이름: ")
