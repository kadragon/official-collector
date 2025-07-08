"""과제 카드 매칭 관련 모듈."""

import logging
from typing import List, Optional

from services.dialog_service import DialogHandler, SelectionStatus
from services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

class TaskCardService:
    """
    과제 카드를 매칭하는 클래스.
    """
    def __init__(self, supabase_service: SupabaseService, dialog_handler: DialogHandler, predefined_card_list: List[str]):
        self.supabase_service = supabase_service
        self.dialog = dialog_handler
        self.predefined_card_list = predefined_card_list

    def match_task_card(self, title: str) -> Optional[str]:
        """
        결재 완료된 공문에 대해 과제 카드를 매칭합니다.
        """
        # 1. Exact match using Supabase
        card_name = self.supabase_service.retrieve_card_by_title(title)
        is_exact_match = card_name is not None

        if not is_exact_match:
            # If no exact match, try recommendations
            recommendations = self.supabase_service.recommend_cards(title, count=5)
            if recommendations:
                status, value = self.dialog.choose_from_recommendations(title, recommendations)
                if status == SelectionStatus.SKIPPED:
                    card_name = None  # User chose '추천 없음'
                elif status == SelectionStatus.SELECTED:
                    card_name = value
                elif status == SelectionStatus.MANUAL_INPUT:
                    card_name = None  # Trigger manual input

            if card_name is None:
                # If no recommendation was chosen or user opted for manual input from recommendations
                # Offer predefined list
                status, value = self.dialog.choose_from_predefined_list(title, self.predefined_card_list)
                if status == SelectionStatus.SELECTED:
                    card_name = value
                elif status == SelectionStatus.MANUAL_INPUT:
                    manual_card_name = self.dialog.get_manual_task_card(title)
                    if manual_card_name:
                        card_name = manual_card_name
                    else:
                        logger.warning(f"No task card provided for title: {title}")

        if card_name and not is_exact_match:
            self.supabase_service.upsert_card_embedding(title, card_name)
        
        return card_name
