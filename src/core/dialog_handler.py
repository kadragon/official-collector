"""
사용자의 입력이 필요한 부분에 대한 제어.
"""

from typing import Dict, Tuple, List
from pathlib import Path # Added import

from src.core.cmd_control import CmdControl
# from ai.ai_openai import card_picker # Removed old import

from src.config.config import PREFERRED_LLM_MODEL # Added import
from src.ai.llm_handler import LLMHandler # Added import


class DialogHandler:
    """과제카드 선택을 담당하는 클래스."""

    def __init__(self) -> None:
        """초기화 및 CMD 창 활성화."""
        self.cmd = CmdControl()
        # self.ai = None # Removed as per instruction

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
        if approval_list.index(selected_approval) < 2: # Assuming first two approval options might need '공람 대상자'
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

    def check_card_sort(self, title: str) -> str:
        self.cmd.activate()

        print(f"AI 분석 시작 ({PREFERRED_LLM_MODEL} 모델 사용): {title}")

        handler = LLMHandler() # Instantiated LLMHandler

        # Construct path to data/card_list.txt
        # Assuming this file (dialog_handler.py) is in src/core/
        # So parents[2] should give the project root.
        PROJECT_ROOT = Path(__file__).resolve().parents[2]
        DOCU_DATA_PATH = PROJECT_ROOT / "data" / "card_list.txt"
        
        docu_data_content: str
        try:
            with open(DOCU_DATA_PATH, "r", encoding="utf-8") as f:
                # The card_picker_langchain in LLMHandler expects a string of card names.
                # The formatting used in ai_openai.py and ai_gemini.py (before refactoring) was:
                # docu_data_content = "".join(f"- {line.strip()}\n" for line in f if line.strip())
                # Let's replicate this for consistency with how the prompt in LLMHandler was designed.
                docu_data_content = "".join(
                    f"- {line.strip()}\n" for line in f if line.strip()
                )
            if not docu_data_content.strip(): # Check if file is empty or only whitespace
                 print(f"Warning: card_list.txt at {DOCU_DATA_PATH} is empty or contains only whitespace.")
                 # Depending on desired behavior, could return '' or proceed with empty content
        except FileNotFoundError:
            print(f"Error: card_list.txt not found at {DOCU_DATA_PATH}")
            return '' # Return empty string, indicating an error or inability to proceed

        recommend = handler.card_picker_langchain(
            model_type=PREFERRED_LLM_MODEL,
            title=title,
            docu_data_content=docu_data_content
        )

        # Ensure recommend is a list, as expected by subsequent code.
        # card_picker_langchain returns List[str] or [] on error.
        if recommend is None: # Should not happen if card_picker_langchain returns [] on error
            recommend = [] 
            print("AI 분석 중 오류가 발생했거나 결과를 받지 못했습니다.")


        if not recommend: # If list is empty
            print("AI가 추천 과제카드를 찾지 못했습니다.")
            # User might still want to manually input or it might signify an issue.
            # For now, the original logic of returning '' if no selection is made will handle this.
            # No explicit 'return """ here, let the existing input logic proceed.

        for idx, recommend_card_name in enumerate(recommend):
            print(f"[{idx + 1:02d}] {recommend_card_name}")

        print()

        confirm = input("분류 하시겠습니까?( 1 ~ 5 / 취소(0))")
        if confirm == '0':
            return ''
        try:
            selected_index = int(confirm) - 1
            if 0 <= selected_index < len(recommend):
                return recommend[selected_index]
            else:
                print("잘못된 번호입니다. 추천 목록에서 선택해주세요.")
                return ''
        except ValueError:
            print("숫자로 입력해주세요.")
            return ''
        except IndexError: # Should be caught by the length check, but good practice
            print("선택한 번호가 추천 목록 범위를 벗어났습니다.")
            return ''
