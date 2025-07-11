"""공문 자동 분류 및 처리를 위한 메인 모듈."""

import time
import re
import logging
from typing import List, Dict, Any
from pathlib import Path

from config import config
from services.official_collector import OfficialCollector
from utils.json_handler import load_json
from services.dialog_service import DialogHandler
from services.supabase_service import SupabaseService
from services.reception_service import ReceptionService
from services.task_card_service import TaskCardService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Main:
    """공문 자동 분류 및 처리를 위한 메인 클래스."""

    def __init__(self):
        base_data = self._load_base_data()
        self.approval_name_list: List[str] = base_data["reception_list"]
        self.share_name_list: List[str] = base_data["share_list"]

        self.collector = OfficialCollector()
        self.dialog = DialogHandler()

        # Reception을 위한 Supabase 서비스
        reception_supabase_service = SupabaseService(
            openai_api_key=config.openai_api_key,
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key,
            table_name="reception_documents",
            query_name="match_reception_documents"
        )

        # Task Card를 위한 Supabase 서비스
        task_card_supabase_service = SupabaseService(
            openai_api_key=config.openai_api_key,
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key,
            table_name="documents",
            query_name="match_documents"
        )

        self.predefined_card_list: List[str] = base_data["card_list"]

        self.reception_service = ReceptionService(
            reception_supabase_service, self.dialog, self.approval_name_list, self.share_name_list
        )
        self.task_card_service = TaskCardService(
            task_card_supabase_service, self.dialog, self.predefined_card_list
        )

    def _load_base_data(self) -> Dict[str, List[str]]:
        """data/base_data.json 파일에서 기본 데이터를 읽어옵니다."""
        PROJECT_ROOT = Path(__file__).resolve().parents[1]
        file_path = PROJECT_ROOT / "data" / "base_data.json"
        try:
            return load_json(str(file_path))
        except FileNotFoundError:
            logger.error(f"Error: base_data.json not found at {file_path}")
            return {"card_list": [], "reception_list": [], "share_list": []}

    def run(self) -> None:
        """ 메인 로직 """
        while True:
            if self.collector.check_end_collecting():
                break

            title = self.collector.get_official_title()

            if title.startswith('접수'):
                approval, shared = self.reception_service.handle_reception(title)

                if approval:
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

        print("완료되었습니다.")

if __name__ == '__main__':
    main = Main()
    main.run()
