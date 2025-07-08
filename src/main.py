"""공문 자동 분류 및 처리를 위한 메인 모듈."""

import time
import re
import logging
from typing import List, Dict, Any
from pathlib import Path

from config import config
from services.official_collector import OfficialCollector
from utils.json_handler import load_json, update_sort_data
from services.dialog_service import DialogHandler
from services.supabase_service import SupabaseService
from services.reception_service import ReceptionService
from services.task_card_service import TaskCardService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Main:
    """공문 자동 분류 및 처리를 위한 메인 클래스."""

    def __init__(self):
        self.sort_data: Dict[str, List] = load_json("./data/sort_data.json")
        self.sorted_data: Dict[str, List[Dict[str, Any]]] = {"items": []}
        self.approval_name_list: List[str] = load_json('./data/base_data.json')['approval_names']
        self.share_name_list: List[str] = load_json('./data/base_data.json')['share_names']

        self.collector = OfficialCollector()
        self.dialog = DialogHandler()

        self.supabase_service = SupabaseService(
            openai_api_key=config.openai_api_key,
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key
        )

        self.predefined_card_list: List[str] = self._load_predefined_card_list()

        self.reception_service = ReceptionService(
            self.sort_data, self.dialog, self.approval_name_list, self.share_name_list
        )
        self.task_card_service = TaskCardService(
            self.supabase_service, self.dialog, self.predefined_card_list
        )

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

    def run(self) -> None:
        """ 메인 로직 """
        while True:
            if self.collector.check_end_collecting():
                break

            title = self.collector.get_official_title()

            if title.startswith('접수'):
                approval, shared = self.reception_service.handle_reception(title)

                if approval:
                    self.sorted_data['items'].append({
                        "title": title.replace("접수: ", ''),
                        "approval": approval,
                        "shared": shared
                    })
                    self.collector.approval(approval)
                    if shared is not None and shared != '공람없음':
                        self.collector.add_share(str(shared))
                    
                    print(f"{title} -> {approval} / {shared}")
                    self.collector.reception()

                    if shared != '공람없음':
                        self.collector.dlg['확인2'].click()
                    time.sleep(1)
            else:
                if title.startswith('전자결재:'):
                    match = re.search(r'(?:[^]]*]){2}(.*)', title)
                    if match:
                        title = match.group(1).strip()
                    else:
                        title = title.split("]")[-1].strip()
                
                card_name = self.task_card_service.match_task_card(title)

                if card_name:
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
