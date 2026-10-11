"""
통합 문서 처리기

접수 문서와 과제 카드 매칭을 통합 처리하는 서비스입니다.
기존의 ReceptionService와 TaskCardService를 하나로 통합하여
문서 처리 로직을 중앙화하고 코드 중복을 제거했습니다.
"""

# Trace: backlog.md - Classification safety and learning retries

from typing import List, Tuple, Optional, Any, Union, cast, Callable
from config import VectorConfig
from services.supabase_service import SupabaseService
from services.local_vector_service import LocalVectorService
from ui.console_interface import (
    SelectionResult,
    get_user_choice_from_recommendations,
    ConsoleInterface,
)
from ui.rich_console import RichConsole
from utils.text_utils import clean_document_title
from utils.error_handler import setup_logger
from utils.performance_logger import log_execution_time
from utils.timed_input import choose_timed_option

logger = setup_logger(__name__)
console = RichConsole()


class DocumentProcessor:
    """
    통합 문서 처리기 클래스

    접수 문서 처리와 과제 카드 매칭을 통합하여 관리합니다.
    """

    def __init__(
        self,
        supabase_service: Union[SupabaseService, LocalVectorService],
        approval_name_list: List[str],
        share_name_list: List[str],
        predefined_card_list: List[str],
        *,
        approval_store: Optional[LocalVectorService] = None,
        reception_member_provider: Optional[Callable[[], List[str]]] = None,
    ):
        """
        초기화

        Args:
            supabase_service: 벡터 저장소 서비스 (Supabase 또는 Local, 통합)
            approval_name_list: 담당자 목록
            share_name_list: 공람 대상자 목록
            predefined_card_list: 미리 정의된 카드 목록
        """
        self.supabase_service = supabase_service
        self.approval_name_list = approval_name_list
        self.share_name_list = share_name_list
        self.predefined_card_list = predefined_card_list
        self.approval_store = approval_store
        self.reception_member_provider = reception_member_provider

        # UI 인터페이스
        self.console_interface = ConsoleInterface()

        # 배치 업데이트를 위한 임시 저장소
        self.pending_reception_updates: list[dict[str, Any]] = []
        self.pending_card_updates: list[dict[str, Any]] = []

    # ============================================================================
    # 접수 문서 처리 (기존 ReceptionService)
    # ============================================================================

    @log_execution_time(logger)
    def process_assigned_document(
        self,
        title: str,
        apply_line: Callable[[List[str]], bool],
        capture_line: Callable[[], Optional[List[str]]],
    ) -> bool:
        """Reuse a local line or capture a manually verified one; learn after success."""
        store = self.approval_store
        if store is None or not title.strip():
            logger.warning("Approval memory unavailable or empty title: %s", title)
            return False
        exact = store.retrieve_approval_line_by_title(title)
        if exact and apply_line(exact):
            return True
        response = store.embedding_service.create_embedding(
            title, f"approval_line_{title}"
        )
        vector = response.embedding if response else None
        recommendations = (
            store.recommend_approval_lines_with_embedding(vector)
            if vector is not None
            else []
        )
        selected = None
        if recommendations:
            if (
                recommendations[0]["similarity"]
                >= VectorConfig.AUTO_SELECTION_SIMILARITY_THRESHOLD
            ):
                selected = recommendations[0]["approvers"]
            else:
                options = [
                    f"{item['similarity']:.1%} | {' → '.join(item['approvers'])}"
                    for item in recommendations
                ]
                choice = choose_timed_option(title, options, allow_manual=True)
                if choice is None:
                    return False
                if choice:
                    selected = recommendations[options.index(choice)]["approvers"]
        if selected is not None and apply_line(selected):
            names = selected
        else:
            if selected is not None:
                logger.warning(
                    "Stored approval line failed to apply; requesting manual capture: %s",
                    title,
                )
            names = capture_line()
        if (
            not names
            or any(not name.strip() for name in names)
            or len(set(names)) != len(names)
        ):
            logger.warning("Approval line not captured/applied: %s", title)
            return False
        if not store.upsert_approval_line_embedding(title, names, vector):
            logger.warning("Approval line applied but memory save failed: %s", title)
        return True

    @log_execution_time(logger)
    def process_reception_document(
        self, title: str
    ) -> Tuple[Optional[str], Optional[Any]]:
        """Reuse handlers or select from the org chart with bounded input."""
        processed_title = clean_document_title(title)
        if not processed_title:
            return None, None
        approval, shared = self.supabase_service.retrieve_reception_by_title(
            processed_title
        )
        if approval:
            return approval, shared
        response = self.supabase_service.embedding_service.create_embedding(
            processed_title, f"reception_{processed_title}"
        )
        vector = response.embedding if response else None
        recommendations = (
            self.supabase_service.recommend_reception_with_embedding(vector, count=3)
            if vector is not None
            else []
        )
        selected = None
        if recommendations:
            if (
                recommendations[0]["similarity"]
                >= VectorConfig.AUTO_SELECTION_SIMILARITY_THRESHOLD
            ):
                selected = recommendations[0]
            else:
                options = [
                    f"{item['similarity']:.1%} | {item['approval']} | {item['share']}"
                    for item in recommendations
                ]
                choice = choose_timed_option(title, options, allow_manual=True)
                if choice is None:
                    return None, None
                if choice:
                    selected = recommendations[options.index(choice)]
        if selected is not None:
            approval, shared = selected["approval"], selected["share"]
        else:
            approval, shared = self._manual_reception_selection(title)
        if not approval or shared is None:
            logger.warning("Reception selection unavailable: %s", processed_title)
            return None, None
        self._queue_reception_update(processed_title, approval, shared, vector)
        return approval, shared

    def _manual_reception_selection(
        self, title: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Display full member node text and reject ambiguous name-only application."""
        members = (
            self.reception_member_provider()
            if self.reception_member_provider is not None
            else self.approval_name_list
        )
        if not members:
            logger.warning("No reception members available: %s", title)
            return None, None
        selected = choose_timed_option("담당자 선택", members)
        if not selected or not selected.split():
            return None, None
        name = selected.split()[0]
        if (
            sum(
                bool(member.split()) and member.split()[0] == name for member in members
            )
            != 1
        ):
            logger.warning("Reception handler name is ambiguous: %s", name)
            return None, None
        shared = choose_timed_option("공람자 선택", self.share_name_list)
        return (name, shared) if shared is not None else (None, None)

    # ============================================================================
    # 과제 카드 처리 (기존 TaskCardService)
    # ============================================================================

    @log_execution_time(logger)
    def process_task_card_matching(
        self,
        title: str,
        manual_selection: Optional[Callable[[Optional[str]], Optional[str]]] = None,
    ) -> Optional[str]:
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
        if manual_selection is not None:
            return self._match_live_task_card(title, manual_selection)

        # 1. 정확한 제목 매칭을 먼저 시도
        card_name = self.supabase_service.retrieve_card_by_title(title)
        is_exact_match = card_name is not None

        if is_exact_match:
            logger.info("정확한 제목 매칭 발견: %s -> %s", title, card_name)
            return cast(str, card_name)  # is_exact_match ensures card_name is not None

        # 2. OpenAI 임베딩 기반 의미적 유사도로 추천 생성
        # 임베딩 재사용: 1회만 생성하여 검색과 저장에 모두 사용
        embedding_response = self.supabase_service.embedding_service.create_embedding(
            title, f"task_card_{title}"
        )
        if not embedding_response:
            logger.warning("임베딩 생성 실패: %s", title)
            card_name = None
        else:
            # 생성된 임베딩으로 검색
            recommendations = self.supabase_service.recommend_cards_with_embedding(
                embedding_response.embedding, count=5
            )
            if recommendations:
                logger.info("pgvector 유사도 기반 추천 과제 카드: %s", recommendations)

                # 최고 유사도가 85% 이상이면 자동 선택
                top_similarity = recommendations[0]["similarity"]
                if top_similarity >= VectorConfig.AUTO_SELECTION_SIMILARITY_THRESHOLD:
                    card_name = cast(str, recommendations[0]["task_title"])
                    logger.info(
                        "유사도 %.1f%% ≥ 85%% - 자동 선택: %s -> %s",
                        top_similarity * 100,
                        title,
                        card_name,
                    )
                    console.print_success(
                        f"유사도 {top_similarity:.1%} - 자동 선택: {card_name}"
                    )
                    # 성공한 매칭을 배치 업데이트 리스트에 추가 (임베딩 재사용)
                    self._queue_card_update(
                        title, card_name, embedding_response.embedding
                    )
                    return card_name

                # 유사도 포함한 문자열 리스트로 변환
                recommendation_options = [
                    f"{rec['similarity']:.1%} | {rec['task_title']}"
                    for rec in recommendations
                ]
                status, value = get_user_choice_from_recommendations(
                    title, recommendation_options
                )  # 사용자에게는 원본 제목 표시
                logger.info("추천 선택 결과: status=%s, value=%s", status, value)
                if status == SelectionResult.SKIPPED:
                    card_name = None  # 사용자가 '추천 없음' 선택
                    logger.info("추천 없음 선택됨 - 다음 단계로 이동")
                elif status == SelectionResult.SELECTED:
                    # 유사도 정보 제거하고 실제 카드명만 추출
                    if value is None:
                        raise ValueError("추천 선택 결과가 None입니다")
                    selected_index = recommendation_options.index(value)
                    card_name = cast(str, recommendations[selected_index]["task_title"])
                    logger.info("임베딩 추천에서 선택: %s -> %s", title, card_name)

        # 3. 추천이 선택되지 않은 경우 미리 정의된 목록 제공
        logger.info("3단계 진입 전 card_name 상태: %s", card_name)
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

        # 성공한 매칭을 배치 업데이트 리스트에 추가 (임베딩 재사용)
        if card_name:
            # 임베딩이 생성되었으면 전달, 아니면 None
            embedding = embedding_response.embedding if embedding_response else None
            self._queue_card_update(title, card_name, embedding)
            logger.info("과제 카드 매칭 완료: %s -> %s", title, card_name)
            return cast(str, card_name)  # if check ensures card_name is not None

        logger.warning("과제 카드 매칭 실패: %s", title)
        return None

    def _match_live_task_card(
        self, title: str, capture: Callable[[Optional[str]], Optional[str]]
    ) -> Optional[str]:
        """Recommend from DB, then learn the actual verified client selection."""
        suggestion = self.supabase_service.retrieve_card_by_title(title)
        embedding = None
        if suggestion is None:
            response = self.supabase_service.embedding_service.create_embedding(
                title, f"task_card_{title}"
            )
            if response:
                embedding = response.embedding
                recommendations = self.supabase_service.recommend_cards_with_embedding(
                    embedding, count=5
                )
                options = [
                    f"{r['similarity']:.1%} | {r['task_title']}"
                    for r in recommendations
                ]
                if options:
                    status, value = get_user_choice_from_recommendations(title, options)
                    if status == SelectionResult.SELECTED and value in options:
                        suggestion = str(
                            recommendations[options.index(value)]["task_title"]
                        )
        selected = capture(suggestion)
        if not selected or not selected.strip():
            return None
        selected = selected.strip()
        self._queue_card_update(title, selected, embedding)
        return selected

    def discard_card_update(self, title: str) -> None:
        """Do not learn a card for a document whose completion was unverified."""
        self.pending_card_updates = [
            r for r in self.pending_card_updates if r["title"] != title
        ]

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

    def discard_reception_update(self, title: str) -> None:
        """Do not learn a handler when live approval-line application failed."""
        processed_title = clean_document_title(title)
        self.pending_reception_updates = [
            update
            for update in self.pending_reception_updates
            if update["title"] != processed_title
        ]

    # ============================================================================
    # 배치 업데이트 메서드들
    # ============================================================================

    def _queue_reception_update(
        self,
        title: str,
        approval: str,
        shared: Any,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """접수 문서 업데이트를 큐에 추가 (임베딩 포함)"""
        self.pending_reception_updates.append(
            {
                "title": title,
                "approval": approval,
                "shared": shared,
                "embedding": embedding,
            }
        )
        logger.debug("접수 문서 업데이트 큐에 추가: %s", title)

    def _queue_card_update(
        self, title: str, card_name: str, embedding: Optional[List[float]] = None
    ) -> None:
        """과제 카드 업데이트를 큐에 추가 (임베딩 포함)"""
        self.pending_card_updates.append(
            {"title": title, "card_name": card_name, "embedding": embedding}
        )
        logger.debug("과제 카드 업데이트 큐에 추가: %s", title)

    @log_execution_time(logger)
    def flush_pending_updates(self) -> None:
        """
        대기 중인 모든 업데이트를 Supabase에 일괄 업로드합니다.

        Upstream deduplication을 수행하여 동일한 title에 대한 중복 업데이트를
        제거하고 가장 최근 값만 유지합니다.
        """
        reception_count_original = len(self.pending_reception_updates)
        card_count_original = len(self.pending_card_updates)

        if reception_count_original == 0 and card_count_original == 0:
            logger.debug("대기 중인 업데이트가 없습니다.")
            return

        logger.info(
            "배치 업데이트 시작 (deduplication 전) - 접수 문서: %d개, 과제 카드: %d개",
            reception_count_original,
            card_count_original,
        )

        # Deduplication: 동일한 title의 경우 가장 최근 값만 유지
        deduplicated_receptions = self._deduplicate_updates(
            self.pending_reception_updates, key="title"
        )
        deduplicated_cards = self._deduplicate_updates(
            self.pending_card_updates, key="title"
        )

        reception_count = len(deduplicated_receptions)
        card_count = len(deduplicated_cards)

        if reception_count < reception_count_original:
            logger.info(
                "접수 문서 중복 제거: %d개 → %d개 (중복 %d개 제거)",
                reception_count_original,
                reception_count,
                reception_count_original - reception_count,
            )

        if card_count < card_count_original:
            logger.info(
                "과제 카드 중복 제거: %d개 → %d개 (중복 %d개 제거)",
                card_count_original,
                card_count,
                card_count_original - card_count,
            )

        # 접수 문서 배치 업데이트 (임베딩 재사용)
        success_count = 0
        failed_receptions = []
        for update in deduplicated_receptions:
            try:
                # 임베딩이 있으면 재사용, 없으면 기존 메서드 사용
                if update.get("embedding") is not None:
                    saved = self.supabase_service.upsert_reception_with_embedding(
                        update["title"],
                        update["approval"],
                        update["shared"],
                        update["embedding"],
                    )
                else:
                    saved = self.supabase_service.upsert_reception_embedding(
                        update["title"], update["approval"], update["shared"]
                    )
                if saved:
                    success_count += 1
                else:
                    failed_receptions.append(update)
                    logger.warning(
                        "Reception memory save rejected: %s", update["title"]
                    )
            except Exception as e:
                failed_receptions.append(update)
                logger.error(
                    "접수 문서 배치 업데이트 실패: %s - %s", update["title"], str(e)
                )

        logger.info(
            "접수 문서 배치 업데이트 완료: %d/%d", success_count, reception_count
        )

        # 과제 카드 배치 업데이트 (임베딩 재사용)
        success_count = 0
        failed_cards = []
        for update in deduplicated_cards:
            try:
                # 임베딩이 있으면 재사용, 없으면 기존 메서드 사용
                if update.get("embedding") is not None:
                    saved = self.supabase_service.upsert_card_with_embedding(
                        update["title"], update["card_name"], update["embedding"]
                    )
                else:
                    saved = self.supabase_service.upsert_card_embedding(
                        update["title"], update["card_name"]
                    )
                if saved:
                    success_count += 1
                else:
                    failed_cards.append(update)
                    logger.warning("Card memory save rejected: %s", update["title"])
            except Exception as e:
                failed_cards.append(update)
                logger.error(
                    "과제 카드 배치 업데이트 실패: %s - %s", update["title"], str(e)
                )

        logger.info("과제 카드 배치 업데이트 완료: %d/%d", success_count, card_count)

        # Retain only failed latest mappings for the next flush in this process.
        self.pending_reception_updates = failed_receptions
        self.pending_card_updates = failed_cards

        logger.info(
            "Memory flush finished; retained failures: %d receptions, %d cards",
            len(failed_receptions),
            len(failed_cards),
        )

    def _deduplicate_updates(
        self, updates: list[dict[str, Any]], key: str
    ) -> list[dict[str, Any]]:
        """
        업데이트 리스트를 중복 제거합니다.

        동일한 키 값을 가진 항목이 여러 개 있을 경우, 가장 마지막(최근) 항목만 유지합니다.

        Args:
            updates: 업데이트 리스트
            key: 중복 제거에 사용할 키

        Returns:
            list[dict[str, Any]]: 중복 제거된 업데이트 리스트
        """
        seen = {}
        for idx, update in enumerate(updates):
            key_value = update.get(key)
            if key_value:
                # 동일한 키의 경우 가장 마지막 인덱스 저장 (최신 값 우선)
                seen[key_value] = idx

        # seen에 있는 인덱스만 유지
        deduplicated = [updates[idx] for idx in sorted(seen.values())]
        return deduplicated

    def get_pending_updates_count(self) -> Tuple[int, int]:
        """대기 중인 업데이트 개수 반환 (접수 문서, 과제 카드)"""
        return len(self.pending_reception_updates), len(self.pending_card_updates)
