"""공문 자동 분류 및 처리를 위한 메인 모듈."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import time
import re
import logging
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path # Import Path

from core.collector import OfficialCollector
from core.json_handler import load_json, update_sort_data
from core.dialog_handler import DialogHandler
from ai.ai_supabase import SupabaseManager # Import SupabaseManager
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Main:
    """공문 자동 분류 및 처리를 위한 메인 클래스."""

    def __init__(self):

# Check for required environment variables
        required_env_vars = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.critical(error_msg)
            raise ValueError(error_msg)

        self.sort_data: Dict[str, List] = load_json("./data/sort_data.json")
        self.sorted_data: Dict[str, List[Dict[str, Any]]] = {"items": []}
        self.approval_name_list: List[str] = load_json(
            './data/base_data.json')['approval_names']
        self.share_name_list: List[str] = load_json(
            './data/base_data.json')['share_names']

        self.collector = OfficialCollector()
        self.dialog = DialogHandler()

        # Initialize SupabaseManager
        self.supabase_manager = SupabaseManager(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            supabase_url=os.environ.get("SUPABASE_URL"),
            supabase_key=os.environ.get("SUPABASE_KEY")
        )

        # Load predefined card list from file
        self.predefined_card_list: List[str] = self._load_predefined_card_list()

    def _load_predefined_card_list(self) -> List[str]:
        """data/card_list.txt 파일에서 미리 정의된 과제 카드 목록을 읽어옵니다."""
        PROJECT_ROOT = Path(__file__).resolve().parents[1]
        card_list_path = PROJECT_ROOT / "data" / "card_list.txt"
        try:
            with open(card_list_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            logger.error(f"Error: card_list.txt not found at {card_list_path}")
            return []

    def _check_sort(self, title: str) -> Optional[Tuple[str, int]]:
        """접수된 공문에 대해서 담당자 매칭 확인"""
        for approval in self.sort_data.keys():

            for item in self.sort_data[approval]:
                if re.match(item['title'], title) or item['title'] in title:
                    logger.info(
                        '%s으로 %s가 매칭 되었습니다.',
                        item['title'],
                        title
                    )
                    return approval, item['share']

        return None

    def _check_docu(self, title: str) -> str | None:
        """결재 완료된 공문에 대해서 과제 카드 매칭 확인"""
        # 1. Exact match using Supabase
        exact_match_task_title = self.supabase_manager.retrieve_card_by_title(title)
        if exact_match_task_title:
            return exact_match_task_title
        
        return None # No exact match

    def run(self) -> None:
        """ 메인 로직 """
        while True:
            if self.collector.check_end_collecting():
                break

            approval = shared = None

            title = self.collector.get_official_title()

            if title.startswith('접수'):
                checked = self._check_sort(title.replace("접수: ", ''))

                if checked is not None:
                    approval, shared = checked

                    if not self.dialog.check_valid_sort(title, checked):
                        approval = None

                if approval is None:
                    approval, shared = self.dialog.select_approval_and_share(
                        self.approval_name_list, self.share_name_list
                    )

                    self.sorted_data['items'].append({
                        "title": title.replace("접수: ", ''),
                        "approval": approval,
                        "shared": shared
                    })

                self.collector.approval(approval)
                if shared is not None and shared != '공람없음':
                    shared_as_str = str(shared)
                    self.collector.add_share(shared_as_str)

                print(
                    f"{title} -> {approval} / {shared}")

                self.collector.reception()

                if shared != '공람없음':
                    self.collector.dlg['확인2'].click()

                time.sleep(1)
            else:
                if title.startswith('전자결재:'):
                    # 정규 표현식을 사용하여 두 번째 ']' 뒤의 문자열 추출 시도
                    match = re.search(r'(?:[^]]*]){2}(.*)', title)
                    if match:
                        title = match.group(1).strip()
                    else:
                        # 패턴이 맞지 않으면 기존 방식(마지막 ']') 뒤) 사용
                        title = title.split("]")[-1].strip()
                
                card_name = self._check_docu(title)

                if card_name is None:
                    # If no exact match, try recommendations
                    recommendations = self.supabase_manager.recommend_cards(title, count=5)
                    if recommendations:
                        chosen_recommendation = self.dialog.choose_from_recommendations(title, recommendations)
                        if chosen_recommendation == "MANUAL_INPUT":
                            card_name = None # Trigger manual input
                        elif chosen_recommendation:
                            card_name = chosen_recommendation
                        else:
                            card_name = None # User chose '추천 없음' or no recommendation was chosen

                if card_name is None:
                    # If no recommendation was chosen or user opted for manual input from recommendations
                    # Offer predefined list
                    selected_from_list = self.dialog.choose_from_predefined_list(title, self.predefined_card_list)
                    if selected_from_list:
                        card_name = selected_from_list
                    else:
                        # If user chose manual input from predefined list, or no list was provided
                        manual_card_name = self.dialog.get_manual_task_card(title)
                        if manual_card_name:
                            card_name = manual_card_name
                        else:
                            logger.warning(f"No task card provided for title: {title}")
                            # Decide how to handle this case: skip, error, or loop back
                            # For now, we'll just skip document_sort if card_name is still None

                if card_name: # Only proceed if a card_name is determined
                    # Ensure the mapping is stored in Supabase for future use
                    self.supabase_manager.upsert_card_embedding(title, card_name)
                    self.collector.document_sort(card_name)
                else:
                    logger.warning(f"Skipping document sort for title: {title} due to no valid task card.")

                time.sleep(2)

        if len(self.sorted_data['items']) > 0:
            print("분류 기준을 갱신합니다.")
            update_sort_data(self.sort_data, self.sorted_data)

        print("완료되었습니다.")


if __name__ == '__main__':
    main = Main()
    main.run()