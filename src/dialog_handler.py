"""
사용자의 입력이 필요한 부분에 대한 제어.
"""

from typing import Dict, Tuple, List
from src.cmd_control import CmdControl


class DialogHandler:
    """과제카드 선택을 담당하는 클래스."""

    def __init__(self) -> None:
        """초기화 및 CMD 창 활성화."""
        self.cmd = CmdControl()
        
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

        for idx, card_name in enumerate(card_list):
            print(f"[{idx:02d}] {card_name}")

        return self._get_valid_input("번호를 선택하세요: ", card_list)

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
        selected_share = "공람 없음"

        # 담당자가 특정 범위 내에 있으면 공람 대상자도 선택
        if approval_list.index(selected_approval) < 2:
            print("\n[공람자 선택]")
            print(" / ".join(f"[{idx}] {name}" for idx, name in enumerate(share_list)))

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