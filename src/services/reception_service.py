"""'접수' 공문 처리 관련 모듈."""

import logging
from typing import List, Tuple, Optional, Any

from services.dialog_service import DialogHandler, SelectionStatus
from services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

class ReceptionService:
    """
    '접수' 공문을 처리하는 클래스.
    """
    def __init__(self, supabase_service: SupabaseService, dialog_handler: DialogHandler, approval_name_list: List[str], share_name_list: List[str]):
        self.supabase_service = supabase_service
        self.dialog = dialog_handler
        self.approval_name_list = approval_name_list
        self.share_name_list = share_name_list

    def handle_reception(self, title: str) -> Tuple[Optional[str], Optional[Any]]:
        """
        Handles the reception of official documents and returns the person in charge and the person to be shared with.
        """
        processed_title = title.replace("접수: ", '').strip()

        # 1. Exact match using Supabase
        approval, shared = self.supabase_service.retrieve_reception_by_title(processed_title)
        if approval:
            return approval, shared

        # 2. If no exact match, try recommendations, but only if there's a title to search for
        if processed_title:
            recommendations = self.supabase_service.recommend_reception(processed_title, count=3)
            print(f"match_reception_documents 결과: {recommendations}")
            if recommendations:
                recommendation_options = [f"{rec['approval']} (공람: {rec['share']})" for rec in recommendations]
                status, value = self.dialog.choose_from_recommendations(
                    processed_title,
                    recommendation_options
                )
                if status == SelectionStatus.SELECTED:
                    selected_index = recommendation_options.index(value)
                    selected_rec = recommendations[selected_index]
                    approval, shared = selected_rec['approval'], selected_rec['share']
                    self.supabase_service.upsert_reception_embedding(processed_title, approval, shared)
                    return approval, shared

        # 3. If no recommendation was chosen, offer full list
        status, value = self.dialog.choose_from_full_list(processed_title, self.approval_name_list)
        if status == SelectionStatus.SELECTED:
            approval = value
            # Select sharer
            _, shared = self.dialog.select_approval_and_share([approval], self.share_name_list)
            self.supabase_service.upsert_reception_embedding(processed_title, approval, shared)

        return approval, shared
