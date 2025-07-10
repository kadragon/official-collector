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
        접수 공문을 처리하고, 담당자와 공람자를 반환합니다.
        """
        processed_title = title.replace("접수: ", '')
        
        # 1. Exact match using Supabase
        approval, shared = self.supabase_service.retrieve_reception_by_title(processed_title)
        is_exact_match = approval is not None

        if not is_exact_match:
            # If no exact match, try recommendations
            recommendations = self.supabase_service.recommend_reception(processed_title, count=3)
            if recommendations:
                status, value = self.dialog.choose_from_recommendations(
                    processed_title, 
                    [f"{rec['approval']} (공람: {rec['share']})" for rec in recommendations]
                )
                if status == SelectionStatus.SELECTED:
                    selected_rec = recommendations[value]
                    approval, shared = selected_rec['approval'], selected_rec['share']
                elif status == SelectionStatus.SKIPPED:
                    approval, shared = None, None # User chose '추천 없음'

        if approval is None:
            # If no recommendation was chosen or user opted for manual input from recommendations
            # Offer predefined list
            status, value = self.dialog.choose_from_predefined_list(processed_title, self.approval_name_list)
            if status == SelectionStatus.SELECTED:
                approval = value
                # 공람자 선택
                _, shared = self.dialog.select_approval_and_share([approval], self.share_name_list)

            elif status == SelectionStatus.MANUAL_INPUT:
                approval, shared = self.dialog.select_approval_and_share(
                    self.approval_name_list, self.share_name_list
                )

        if approval and not is_exact_match:
            self.supabase_service.upsert_reception_embedding(processed_title, approval, shared)

        return approval, shared
