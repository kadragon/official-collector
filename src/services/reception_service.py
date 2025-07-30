"""'접수' 공문 처리 관련 모듈."""

from typing import List, Tuple, Optional, Any

from services.dialog_service import DialogHandler
from services.supabase_service import SupabaseService
from utils.input_validator import SelectionResult
from utils.string_processor import clean_document_title
from utils.error_handler import setup_logger

logger = setup_logger(__name__)

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
        접수 공문을 임베딩 기반 의미적 유사도로 처리하여 담당자와 공람 대상자를 반환합니다.
        1단계: 정확한 제목 매칭 시도
        2단계: 벡터 유사도 기반 담당자 추천
        3단계: 사용자 수동 선택
        """
        processed_title = clean_document_title(title)
        logger.info("임베딩 기반 접수 문서 처리 시작: %s", processed_title)

        # 1. 정확한 제목 매칭을 먼저 시도
        approval, shared = self.supabase_service.retrieve_reception_by_title(processed_title)
        if approval:
            logger.info("정확한 제목 매칭 발견: %s -> %s/%s", processed_title, approval, shared)
            return approval, shared

        # 2. 임베딩 기반 의미적 유사도로 담당자 추천
        if processed_title:
            recommendations = self.supabase_service.recommend_reception(processed_title, count=3)
            logger.info("벡터 유사도 기반 담당자 추천: %s", recommendations)

            if recommendations:
                recommendation_options = [f"{rec['approval']} (공람: {rec['share']})" for rec in recommendations]
                status, value = self.dialog.choose_from_recommendations(
                    processed_title,
                    recommendation_options
                )
                if status == SelectionResult.SELECTED:
                    selected_index = recommendation_options.index(value)
                    selected_rec = recommendations[selected_index]
                    approval, shared = selected_rec['approval'], selected_rec['share']
                    self.supabase_service.upsert_reception_embedding(processed_title, approval, shared)
                    logger.info("임베딩 추천 선택 완료: %s -> %s/%s", processed_title, approval, shared)
                    return approval, shared

        # 3. 추천이 선택되지 않은 경우 전체 담당자 목록 제공
        status, value = self.dialog.choose_from_full_list(processed_title, self.approval_name_list)
        if status == SelectionResult.SELECTED:
            approval = value
            # 공람자 선택
            _, shared = self.dialog.select_approval_and_share([approval], self.share_name_list)
            # 새로운 매칭을 벡터 데이터베이스에 학습 데이터로 추가
            self.supabase_service.upsert_reception_embedding(processed_title, approval, shared)
            logger.info("수동 선택 완료 및 학습: %s -> %s/%s", processed_title, approval, shared)

        return approval, shared
