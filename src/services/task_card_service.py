"""과제 카드 매칭 관련 모듈."""

from typing import List, Optional

from services.dialog_service import DialogHandler
from services.supabase_service import SupabaseService
from utils.input_validator import SelectionResult
from utils.error_handler import setup_logger

logger = setup_logger(__name__)

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
        결재 완료된 공문에 대해 임베딩 기반 의미적 유사도로 과제 카드를 매칭합니다.
        1단계: 정확한 제목 매칭 시도
        2단계: 벡터 유사도 기반 추천 제시
        3단계: 사용자 수동 선택
        """
        logger.info(f"임베딩 기반 과제 카드 매칭 시작: {title}")
        
        # 1. 정확한 제목 매칭을 먼저 시도
        card_name = self.supabase_service.retrieve_card_by_title(title)
        is_exact_match = card_name is not None

        if is_exact_match:
            logger.info(f"정확한 제목 매칭 발견: {title} -> {card_name}")
            return card_name

        # 2. 임베딩 기반 의미적 유사도로 추천 생성
        recommendations = self.supabase_service.recommend_cards(title, count=5)
        if recommendations:
            logger.info(f"벡터 유사도 기반 추천 과제 카드: {recommendations}")
            status, value = self.dialog.choose_from_recommendations(title, recommendations)
            if status == SelectionResult.SKIPPED:
                card_name = None  # 사용자가 '추천 없음' 선택
            elif status == SelectionResult.SELECTED:
                card_name = value
                logger.info(f"임베딩 추천에서 선택: {title} -> {card_name}")

        # 3. 추천이 선택되지 않은 경우 미리 정의된 목록 제공
        if card_name is None:
            status, value = self.dialog.choose_from_predefined_list(title, self.predefined_card_list)
            if status == SelectionResult.SELECTED:
                card_name = value
                logger.info(f"미리 정의된 목록에서 선택: {title} -> {card_name}")
            elif status == SelectionResult.SKIPPED:
                # 수동 입력 요청
                manual_card_name = self.dialog.get_manual_task_card(title)
                if manual_card_name:
                    card_name = manual_card_name
                    logger.info(f"수동 입력: {title} -> {card_name}")
                else:
                    logger.warning(f"과제 카드가 제공되지 않음: {title}")

        # 4. 새로운 매칭이 발견된 경우 임베딩으로 학습 데이터에 추가  
        if card_name and not is_exact_match:
            self.supabase_service.upsert_card_embedding(title, card_name)
            logger.info(f"새로운 매칭을 벡터 데이터베이스에 학습: {title} -> {card_name}")
        
        return card_name
