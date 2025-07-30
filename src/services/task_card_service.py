"""과제 카드 매칭 관련 모듈."""

from typing import List, Optional

from services.dialog_service import DialogHandler
from services.chroma_service import ChromaService
from utils.input_validator import SelectionResult
from utils.error_handler import setup_logger

logger = setup_logger(__name__)

class TaskCardService:
    """
    과제 카드를 매칭하는 클래스.
    """
    def __init__(self, chroma_service: ChromaService, dialog_handler: DialogHandler, predefined_card_list: List[str]):
        self.chroma_service = chroma_service
        self.dialog = dialog_handler
        self.predefined_card_list = predefined_card_list

    def match_task_card(self, title: str) -> Optional[str]:
        """
        전자결재 문서에 대해 과제 카드를 매칭합니다.
        1순위: 동일한 문서명이 있다면 바로 처리
        2순위: 임베딩을 통해서 유사한 문서명을 추천하여 사용자가 선택
        3순위: 2순위에서 사용자가 목록에 없음을 선택하면 문서카드 목록 전체를 A->Z 순서로 정리해서 보여줌
        """
        logger.info("임베딩 기반 과제 카드 매칭 시작: %s", title)

        # 1. 정확한 제목 매칭을 먼저 시도
        card_name = self.chroma_service.retrieve_card_by_title(title)
        is_exact_match = card_name is not None

        if is_exact_match:
            logger.info("정확한 제목 매칭 발견: %s -> %s", title, card_name)
            return card_name

        # 2. 임베딩 기반 의미적 유사도로 추천 생성
        recommendations = self.chroma_service.recommend_cards(title, count=5)
        if recommendations:
            logger.info("벡터 유사도 기반 추천 과제 카드: %s", recommendations)
            status, value = self.dialog.choose_from_recommendations(title, recommendations)
            if status == SelectionResult.SKIPPED:
                card_name = None  # 사용자가 '추천 없음' 선택
            elif status == SelectionResult.SELECTED:
                card_name = value
                logger.info("임베딩 추천에서 선택: %s -> %s", title, card_name)

        # 3. 추천이 선택되지 않은 경우 미리 정의된 목록 제공
        if card_name is None:
            status, value = self.dialog.choose_from_predefined_list(title, self.predefined_card_list)
            if status == SelectionResult.SELECTED:
                card_name = value
                logger.info("미리 정의된 목록에서 선택: %s -> %s", title, card_name)
            elif status == SelectionResult.SKIPPED:
                # 3순위: 전체 문서카드 목록 A->Z 순서로 정렬하여 제공
                logger.info("미리 정의된 목록에서 선택되지 않음 - 전체 목록 제공")
                status, value = self.dialog.choose_from_full_list(title, self.predefined_card_list)
                if status == SelectionResult.SELECTED:
                    card_name = value
                    logger.info("전체 목록에서 선택: %s -> %s", title, card_name)
                elif status == SelectionResult.SKIPPED:
                    # 최후 수단: 수동 입력 요청
                    manual_card_name = self.dialog.get_manual_task_card(title)
                    if manual_card_name:
                        card_name = manual_card_name
                        logger.info("수동 입력: %s -> %s", title, card_name)
                    else:
                        logger.warning("과제 카드가 제공되지 않음: %s", title)

        # 4. 새로운 매칭이 발견된 경우 임베딩으로 학습 데이터에 추가
        if card_name and not is_exact_match:
            self.chroma_service.upsert_card_embedding(title, card_name)
            logger.info("새로운 매칭을 벡터 데이터베이스에 학습: %s -> %s", title, card_name)

        return card_name
