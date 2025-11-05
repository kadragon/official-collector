"""
통합 문서 처리기

접수 문서와 과제 카드 매칭을 통합 처리하는 서비스입니다.
기존의 ReceptionService와 TaskCardService를 하나로 통합하여
문서 처리 로직을 중앙화하고 코드 중복을 제거했습니다.
"""

from typing import List, Tuple, Optional, Any
from services.supabase_service import SupabaseService
from ui.console_interface import (
    SelectionResult,
    get_user_choice_from_list,
    get_user_choice_from_recommendations,
    ConsoleInterface,
    clear_screen,
    print_selection_menu,
    get_styled_input,
    get_valid_selection,
)
from utils.text_utils import clean_document_title
from utils.error_handler import setup_logger
from utils.performance_logger import log_execution_time

logger = setup_logger(__name__)


class DocumentProcessor:
    """
    통합 문서 처리기 클래스

    접수 문서 처리와 과제 카드 매칭을 통합하여 관리합니다.
    """

    def __init__(
        self,
        supabase_service: SupabaseService,
        approval_name_list: List[str],
        share_name_list: List[str],
        predefined_card_list: List[str],
    ):
        """
        초기화

        Args:
            supabase_service: Supabase 데이터베이스 서비스 (통합)
            approval_name_list: 담당자 목록
            share_name_list: 공람 대상자 목록
            predefined_card_list: 미리 정의된 카드 목록
        """
        self.supabase_service = supabase_service
        self.approval_name_list = approval_name_list
        self.share_name_list = share_name_list
        self.predefined_card_list = predefined_card_list

        # UI 인터페이스
        self.console_interface = ConsoleInterface()

        # 배치 업데이트를 위한 임시 저장소
        self.pending_reception_updates: list[dict[str, Any]] = []
        self.pending_card_updates: list[dict[str, Any]] = []

    # ============================================================================
    # 접수 문서 처리 (기존 ReceptionService)
    # ============================================================================

    @log_execution_time(logger)
    def process_reception_document(
        self, title: str
    ) -> Tuple[Optional[str], Optional[Any]]:
        """
        접수 공문을 임베딩 기반 의미적 유사도로 처리하여 담당자와 공람 대상자를 반환합니다.

        처리 단계:
        1. 정확한 제목 매칭 시도
        2. 벡터 유사도 기반 담당자 추천
        3. 사용자 수동 선택

        Args:
            title: 원본 문서 제목

        Returns:
            Tuple[담당자, 공람대상자]: (approval, shared)
        """
        processed_title = clean_document_title(title)
        logger.info("임베딩 기반 접수 문서 처리 시작: %s", processed_title)

        # 1. 정확한 제목 매칭을 먼저 시도
        approval, shared = self.supabase_service.retrieve_reception_by_title(
            processed_title
        )
        if approval:
            logger.info(
                "정확한 제목 매칭 발견: %s -> %s/%s", processed_title, approval, shared
            )
            return approval, shared

        # 2. OpenAI 임베딩 기반 의미적 유사도로 담당자 추천
        if processed_title:
            recommendations = self.supabase_service.recommend_reception(
                processed_title, count=3
            )
            logger.info("pgvector 유사도 기반 담당자 추천: %s", recommendations)

            if recommendations:
                recommendation_options = [
                    f"{rec['approval']} (공람: {rec['share']}, 유사도: {rec['similarity']:.1%})"
                    for rec in recommendations
                ]
                status, value = get_user_choice_from_recommendations(
                    title,  # 사용자에게는 원본 제목(숫자 포함) 표시
                    recommendation_options,
                )
                if status == SelectionResult.SELECTED:
                    assert value is not None
                    selected_recommendation = recommendations[
                        recommendation_options.index(value)
                    ]
                    approval = selected_recommendation["approval"]
                    shared = selected_recommendation["share"]
                    logger.info(
                        "임베딩 추천에서 선택: %s -> %s/%s",
                        processed_title,
                        approval,
                        shared,
                    )

                    # 성공한 매칭을 배치 업데이트 리스트에 추가
                    self._queue_reception_update(processed_title, approval, shared)
                    return approval, shared

        # 3. 수동 선택 단계
        logger.info("수동 선택 단계로 이동: %s", processed_title)
        approval, shared = self._manual_reception_selection(
            title
        )  # 사용자에게는 원본 제목 표시

        if approval and shared:
            # 성공한 매칭을 배치 업데이트 리스트에 추가
            self._queue_reception_update(processed_title, approval, shared)
            logger.info(
                "수동 선택 완료: %s -> %s/%s", processed_title, approval, shared
            )
            return approval, shared

        logger.warning("접수 문서 처리 실패: %s", processed_title)
        return None, None

    def _manual_reception_selection(
        self, title: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """수동으로 담당자와 공람 대상자를 선택합니다."""
        try:
            clear_screen()

            # 담당자 선택
            if len(self.approval_name_list) == 1:
                selected_approval = self.approval_name_list[0]
                print(f"담당자 자동 선택: {selected_approval}")
            else:
                print_selection_menu("담당자 선택", self.approval_name_list)
                while True:
                    try:
                        user_input = get_styled_input("번호를 선택하세요: ")
                        selected_approval = get_valid_selection(
                            user_input, self.approval_name_list
                        )
                        break
                    except ValueError as e:
                        print(str(e))

            # 공람자 선택
            print("\n" + "=" * 50)
            print_selection_menu("공람자 선택", self.share_name_list)
            while True:
                try:
                    user_input = get_styled_input("번호를 선택하세요: ")
                    selected_share = get_valid_selection(
                        user_input, self.share_name_list
                    )
                    break
                except ValueError as e:
                    print(str(e))

            return selected_approval, selected_share
        except Exception as e:
            logger.error("수동 선택 중 오류 발생: %s", e)
            return None, None

    # ============================================================================
    # 과제 카드 처리 (기존 TaskCardService)
    # ============================================================================

    @log_execution_time(logger)
    def process_task_card_matching(self, title: str) -> Optional[str]:
        """
        전자결재 문서에 대해 과제 카드를 매칭합니다.

        처리 단계:
        1. 동일한 문서명이 있다면 바로 처리
        2. 임베딩을 통해서 유사한 문서명을 추천하여 사용자가 선택
        3. 추천이 없으면 전체 문서카드 목록을 A->Z 순서로 정리해서 보여줌

        Args:
            title: 문서 제목

        Returns:
            Optional[str]: 매칭된 과제 카드명
        """
        logger.info("임베딩 기반 과제 카드 매칭 시작: %s", title)

        # 1. 정확한 제목 매칭을 먼저 시도
        card_name = self.supabase_service.retrieve_card_by_title(title)
        is_exact_match = card_name is not None

        if is_exact_match:
            logger.info("정확한 제목 매칭 발견: %s -> %s", title, card_name)
            return card_name

        # 2. OpenAI 임베딩 기반 의미적 유사도로 추천 생성
        recommendations = self.supabase_service.recommend_cards(title, count=5)
        if recommendations:
            logger.info("pgvector 유사도 기반 추천 과제 카드: %s", recommendations)
            # 유사도 포함한 문자열 리스트로 변환
            recommendation_options = [
                f"{rec['task_title']} (유사도: {rec['similarity']:.1%})"
                for rec in recommendations
            ]
            status, value = get_user_choice_from_recommendations(
                title, recommendation_options
            )  # 사용자에게는 원본 제목 표시
            logger.info(f"추천 선택 결과: status={status}, value={value}")
            if status == SelectionResult.SKIPPED:
                card_name = None  # 사용자가 '추천 없음' 선택
                logger.info("추천 없음 선택됨 - 다음 단계로 이동")
            elif status == SelectionResult.SELECTED:
                # 유사도 정보 제거하고 실제 카드명만 추출
                assert value is not None
                selected_index = recommendation_options.index(value)
                card_name = recommendations[selected_index]["task_title"]
                logger.info("임베딩 추천에서 선택: %s -> %s", title, card_name)

        # 3. 추천이 선택되지 않은 경우 미리 정의된 목록 제공
        logger.info(f"3단계 진입 전 card_name 상태: {card_name}")
        if card_name is None:
            logger.info("미리 정의된 목록 단계 시작")
            status, value = self.console_interface.choose_from_predefined_list(
                title, self.predefined_card_list
            )
            if status == SelectionResult.SELECTED:
                card_name = value
                logger.info("미리 정의된 목록에서 선택: %s -> %s", title, card_name)
            elif status == SelectionResult.SKIPPED:
                # 전체 정렬된 목록 제공
                logger.info("전체 목록 단계로 이동: %s", title)
                status, value = self.console_interface.choose_from_full_list(
                    title, self.predefined_card_list
                )
                if status == SelectionResult.SELECTED:
                    card_name = value
                    logger.info("전체 목록에서 선택: %s -> %s", title, card_name)

        # 성공한 매칭을 배치 업데이트 리스트에 추가
        if card_name:
            self._queue_card_update(title, card_name)
            logger.info("과제 카드 매칭 완료: %s -> %s", title, card_name)
            return card_name

        logger.warning("과제 카드 매칭 실패: %s", title)
        return None

    # ============================================================================
    # 공통 유틸리티 메서드
    # ============================================================================

    def get_reception_statistics(self) -> dict:
        """접수 처리 통계 정보 반환"""
        try:
            count = self.supabase_service.get_document_count("reception")
            return {
                "total_receptions": count,
                "approval_options": len(self.approval_name_list),
                "share_options": len(self.share_name_list),
            }
        except Exception as e:
            logger.error("접수 통계 조회 실패: %s", e)
            return {"error": str(e)}

    def get_task_card_statistics(self) -> dict:
        """과제 카드 통계 정보 반환"""
        try:
            count = self.supabase_service.get_document_count("task_card")
            return {
                "total_cards": count,
                "predefined_options": len(self.predefined_card_list),
            }
        except Exception as e:
            logger.error("과제 카드 통계 조회 실패: %s", e)
            return {"error": str(e)}

    def reload_configuration(
        self, approval_list: List[str], share_list: List[str], card_list: List[str]
    ) -> None:
        """런타임 중 설정 다시 로드"""
        self.approval_name_list = approval_list
        self.share_name_list = share_list
        self.predefined_card_list = card_list
        logger.info("문서 처리기 설정 다시 로드됨")

    # ============================================================================
    # 배치 업데이트 메서드들
    # ============================================================================

    def _queue_reception_update(self, title: str, approval: str, shared: Any) -> None:
        """접수 문서 업데이트를 큐에 추가"""
        self.pending_reception_updates.append(
            {"title": title, "approval": approval, "shared": shared}
        )
        logger.debug("접수 문서 업데이트 큐에 추가: %s", title)

    def _queue_card_update(self, title: str, card_name: str) -> None:
        """과제 카드 업데이트를 큐에 추가"""
        self.pending_card_updates.append({"title": title, "card_name": card_name})
        logger.debug("과제 카드 업데이트 큐에 추가: %s", title)

    @log_execution_time(logger)
    def flush_pending_updates(self) -> None:
        """대기 중인 모든 업데이트를 Supabase에 일괄 업로드"""
        reception_count = len(self.pending_reception_updates)
        card_count = len(self.pending_card_updates)

        if reception_count == 0 and card_count == 0:
            logger.debug("대기 중인 업데이트가 없습니다.")
            return

        logger.info(
            "배치 업데이트 시작 - 접수 문서: %d개, 과제 카드: %d개",
            reception_count,
            card_count,
        )

        # 접수 문서 배치 업데이트
        success_count = 0
        for update in self.pending_reception_updates:
            try:
                self.supabase_service.upsert_reception_embedding(
                    update["title"], update["approval"], update["shared"]
                )
                success_count += 1
            except Exception as e:
                logger.error(
                    "접수 문서 배치 업데이트 실패: %s - %s", update["title"], str(e)
                )

        logger.info(
            "접수 문서 배치 업데이트 완료: %d/%d", success_count, reception_count
        )

        # 과제 카드 배치 업데이트
        success_count = 0
        for update in self.pending_card_updates:
            try:
                self.supabase_service.upsert_card_embedding(
                    update["title"], update["card_name"]
                )
                success_count += 1
            except Exception as e:
                logger.error(
                    "과제 카드 배치 업데이트 실패: %s - %s", update["title"], str(e)
                )

        logger.info("과제 카드 배치 업데이트 완료: %d/%d", success_count, card_count)

        # 큐 초기화
        self.pending_reception_updates.clear()
        self.pending_card_updates.clear()

        logger.info("배치 업데이트 완료 - 모든 대기 중인 업데이트가 처리되었습니다.")

    def get_pending_updates_count(self) -> Tuple[int, int]:
        """대기 중인 업데이트 개수 반환 (접수 문서, 과제 카드)"""
        return len(self.pending_reception_updates), len(self.pending_card_updates)
