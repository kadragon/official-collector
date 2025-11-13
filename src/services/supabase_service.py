"""
Supabase 데이터베이스 서비스 클래스
벡터 유사도 검색, CRUD 연산, 배치 업데이트 기능 제공
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from supabase import create_client, Client
from dotenv import load_dotenv
from .openai_embedding_service import OpenAIEmbeddingService
from utils.performance_logger import log_execution_time, timer
from utils.config_manager import get_vector_similarity_threshold

# 환경변수 로드
load_dotenv()

logger = logging.getLogger(__name__)


class SupabaseService:
    """Supabase 데이터베이스 서비스"""

    def __init__(self, embedding_service: OpenAIEmbeddingService) -> None:
        """Supabase 클라이언트 초기화

        Args:
            embedding_service: OpenAI 임베딩 서비스 인스턴스 (의존성 주입)
        """
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL과 SUPABASE_KEY 환경변수가 필요합니다")

        self.client: Client = create_client(self.url, self.key)

        # 주입받은 임베딩 서비스 사용
        self.embedding_service = embedding_service

        # 벡터 유사도 임계값 설정
        self.similarity_threshold = get_vector_similarity_threshold()

        logger.info("Supabase 클라이언트 초기화 완료")

    def retrieve_reception_by_title(
        self, title: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """제목으로 접수 문서 매핑 조회"""
        try:
            result = (
                self.client.table("reception_mappings")
                .select("handler", "share_target")
                .eq("title", title)
                .execute()
            )
            if result.data:
                data = result.data[0]
                return data["handler"], data["share_target"]
            return None, None
        except Exception as e:
            logger.error("접수 문서 제목 조회 실패: %s", e)
            return None, None

    def recommend_reception(self, title: str, count: int = 3) -> List[Dict[str, Any]]:
        """벡터 유사도 기반 접수 문서 추천"""
        try:
            # 1. 쿼리 텍스트 임베딩 생성
            embedding_response = self.embedding_service.create_embedding(
                title, f"query_{title}"
            )
            if not embedding_response:
                logger.warning("임베딩 생성 실패: %s", title)
                return []

            query_embedding = embedding_response.embedding

            # 2. pgvector 코사인 유사도 검색 수행
            try:
                with timer(logger, "Supabase pgvector 검색 (접수)"):
                    result = self.client.rpc(
                        "search_reception_mappings",
                        {
                            "query_embedding": query_embedding,
                            "similarity_threshold": self.similarity_threshold,
                            "match_count": count,
                        },
                    ).execute()

                recommendations = []
                seen_combinations: dict[str, dict[str, Any]] = (
                    {}
                )  # 중복 제거를 위한 딕셔너리

                if result.data:
                    for item in result.data:
                        approval = item["handler"]
                        share = item["share_target"] or "공람없음"
                        similarity = item.get("similarity", 0)
                        item_title = item["title"]

                        # approval + share 조합을 키로 사용
                        combo_key = f"{approval}|{share}"

                        # 새로운 조합이거나 더 높은 유사도인 경우만 추가/업데이트
                        if (
                            combo_key not in seen_combinations
                            or seen_combinations[combo_key]["similarity"] < similarity
                        ):
                            seen_combinations[combo_key] = {
                                "approval": approval,
                                "share": share,
                                "similarity": similarity,
                                "title": item_title,
                            }

                    # 딕셔너리 값을 리스트로 변환하고 유사도 순으로 정렬
                    recommendations = sorted(
                        seen_combinations.values(),
                        key=lambda x: x["similarity"],
                        reverse=True,
                    )
                return recommendations

            except Exception as e:
                logger.error("벡터 검색 실패: %s", e)
                return []

        except Exception as e:
            logger.error("접수 문서 추천 실패: %s", e)
            return []

    def retrieve_card_by_title(self, title: str) -> Optional[str]:
        """제목으로 업무카드 매핑 조회"""
        try:
            result = (
                self.client.table("task_card_mappings")
                .select("task_title")
                .eq("title", title)
                .execute()
            )
            if result.data:
                return str(result.data[0]["task_title"])
            return None
        except Exception as e:
            logger.error("업무카드 제목 조회 실패: %s", e)
            return None

    def recommend_cards(self, title: str, count: int = 5) -> List[Dict[str, Any]]:
        """벡터 유사도 기반 업무카드 추천 (유사도 포함)"""
        try:
            # 1. 쿼리 텍스트 임베딩 생성
            embedding_response = self.embedding_service.create_embedding(
                title, f"query_{title}"
            )
            if not embedding_response:
                logger.warning("임베딩 생성 실패: %s", title)
                return []

            query_embedding = embedding_response.embedding

            # 2. pgvector 코사인 유사도 검색 수행
            try:
                with timer(logger, "Supabase pgvector 검색 (카드)"):
                    result = self.client.rpc(
                        "search_task_card_mappings",
                        {
                            "query_embedding": query_embedding,
                            "similarity_threshold": self.similarity_threshold,
                            "match_count": count,
                        },
                    ).execute()

                recommendations = []
                seen_cards: dict[str, float] = (
                    {}
                )  # 중복 제거를 위한 딕셔너리 (카드명 -> 최고 유사도)

                if result.data:
                    for item in result.data:
                        task_title = item["task_title"]
                        similarity = item.get("similarity", 0)

                        # 새로운 카드이거나 더 높은 유사도인 경우만 추가/업데이트
                        if (
                            task_title not in seen_cards
                            or seen_cards[task_title] < similarity
                        ):
                            seen_cards[task_title] = similarity

                    # 유사도 순으로 정렬하여 카드명과 유사도를 함께 반환
                    recommendations = [
                        {"task_title": card, "similarity": seen_cards[card]}
                        for card in sorted(
                            seen_cards.keys(), key=lambda x: seen_cards[x], reverse=True
                        )[:count]
                    ]

                logger.info(
                    "업무카드 추천 완료 (중복 제거 후): %d개", len(recommendations)
                )
                return recommendations

            except Exception as e:
                logger.error("벡터 검색 실패: %s", e)
                return []

        except Exception as e:
            logger.error("업무카드 추천 실패: %s", e)
            return []

    def upsert_reception_embedding(
        self, title: str, handler: str, share_target: str
    ) -> bool:
        """접수 문서 정규 매핑 (선택적 업데이트)"""
        try:
            embedding_response = self.embedding_service.create_embedding(
                title, f"reception_{title}"
            )
            embedding = embedding_response.embedding if embedding_response else None

            data = {
                "title": title,
                "handler": handler,
                "share_target": share_target,
                "embedding": embedding,
                "updated_at": datetime.utcnow().isoformat(),
            }

            (
                self.client.table("reception_mappings")
                .upsert(data, on_conflict="title")
                .execute()
            )
            logger.info(
                "접수 문서 정규 매핑: %s -> %s/%s", title, handler, share_target
            )
            return True
        except Exception as e:
            logger.error("접수 문서 정규 매핑 실패: %s", e)
            return False

    def upsert_card_embedding(self, title: str, task_title: str) -> bool:
        """업무카드 정규 매핑 (선택적 업데이트)"""
        try:
            embedding_response = self.embedding_service.create_embedding(
                title, f"task_card_{title}"
            )
            embedding = embedding_response.embedding if embedding_response else None

            data = {
                "title": title,
                "task_title": task_title,
                "embedding": embedding,
                "updated_at": datetime.utcnow().isoformat(),
            }

            (
                self.client.table("task_card_mappings")
                .upsert(data, on_conflict="title")
                .execute()
            )
            logger.info("업무카드 정규 매핑: %s -> %s", title, task_title)
            return True
        except Exception as e:
            logger.error("업무카드 정규 매핑 실패: %s", e)
            return False

    def get_document_count(self, table_type: str = "task_card") -> int:
        """문서 개수 조회"""
        try:
            table_name = (
                "task_card_mappings"
                if table_type == "task_card"
                else "reception_mappings"
            )
            result = (
                self.client.table(table_name)
                .select("*", count="exact")
                .limit(0)
                .execute()
            )
            return result.count if result.count is not None else 0
        except Exception as e:
            logger.error("문서 개수 조회 실패: %s", e)
            return 0

    # 유틸리티 메서드
    def get_connection_status(self) -> Dict[str, Any]:
        """연결 상태 확인"""
        try:
            # 간단한 쿼리로 연결 테스트 (새 테이블 구조 사용)
            result = (
                self.client.table("task_card_mappings")
                .select("count", count="exact")
                .limit(0)
                .execute()
            )
            return {
                "connected": True,
                "url": self.url,
                "tables": ["task_card_mappings", "reception_mappings"],
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def clear_all_data(self) -> bool:
        """모든 데이터 삭제 (개발/테스트용)"""
        # 프로덕션 환경에서는 데이터 삭제 금지
        if os.getenv("ENVIRONMENT", "development") == "production":
            logger.error("프로덕션 환경에서는 데이터 삭제를 수행할 수 없습니다")
            return False

        try:
            self.client.table("task_card_mappings").delete().neq("id", "").execute()
            self.client.table("reception_mappings").delete().neq("id", "").execute()
            logger.warning("모든 데이터 삭제 완료")
            return True
        except Exception as e:
            logger.error("데이터 삭제 실패: %s", e)
            return False

    # 삭제 인터페이스용 메서드들
    def list_all_cards(
        self, limit: int = 1000, offset: int = 0
    ) -> List[Tuple[str, str, str]]:
        """모든 업무카드 매핑 목록 조회 (title, task_title, created_at)"""
        try:
            result = (
                self.client.table("task_card_mappings")
                .select("title", "task_title", "created_at")
                .range(offset, offset + limit - 1)
                .execute()
            )
            return [
                (item["title"], item["task_title"], item["created_at"])
                for item in result.data
            ]
        except Exception as e:
            logger.error("업무카드 목록 조회 실패: %s", e)
            return []

    def list_all_receptions(
        self, limit: int = 1000, offset: int = 0
    ) -> List[Tuple[str, str, str, str]]:
        """모든 접수 문서 매핑 목록 조회 (title, handler, share_target, created_at)"""
        try:
            result = (
                self.client.table("reception_mappings")
                .select("title", "handler", "share_target", "created_at")
                .range(offset, offset + limit - 1)
                .execute()
            )
            return [
                (
                    item["title"],
                    item["handler"],
                    item["share_target"],
                    item["created_at"],
                )
                for item in result.data
            ]
        except Exception as e:
            logger.error("접수 문서 목록 조회 실패: %s", e)
            return []

    def bulk_delete_cards(self, titles: List[str]) -> int:
        """업무카드 일괄 삭제"""
        try:
            deleted_count = 0
            for title in titles:
                result = (
                    self.client.table("task_card_mappings")
                    .delete()
                    .eq("title", title)
                    .execute()
                )
                if result.data:
                    deleted_count += len(result.data)
            logger.info("업무카드 일괄 삭제 완료: %d개", deleted_count)
            return deleted_count
        except Exception as e:
            logger.error("업무카드 일괄 삭제 실패: %s", e)
            return 0

    def bulk_delete_receptions(self, titles: List[str]) -> int:
        """접수 문서 일괄 삭제"""
        try:
            deleted_count = 0
            for title in titles:
                result = (
                    self.client.table("reception_mappings")
                    .delete()
                    .eq("title", title)
                    .execute()
                )
                if result.data:
                    deleted_count += len(result.data)
            logger.info("접수 문서 일괄 삭제 완료: %d개", deleted_count)
            return deleted_count
        except Exception as e:
            logger.error("접수 문서 일괄 삭제 실패: %s", e)
            return 0

    def card_exists(self, title: str) -> bool:
        """업무카드 존재 여부 확인"""
        try:
            result = (
                self.client.table("task_card_mappings")
                .select("id")
                .eq("title", title)
                .execute()
            )
            return len(result.data) > 0
        except Exception as e:
            logger.error("업무카드 존재 확인 실패: %s", e)
            return False

    def reception_exists(self, title: str) -> bool:
        """접수 문서 존재 여부 확인"""
        try:
            result = (
                self.client.table("reception_mappings")
                .select("id")
                .eq("title", title)
                .execute()
            )
            return len(result.data) > 0
        except Exception as e:
            logger.error("접수 문서 존재 확인 실패: %s", e)
            return False

    def delete_card_by_title(self, title: str) -> bool:
        """제목으로 업무카드 삭제"""
        try:
            result = (
                self.client.table("task_card_mappings")
                .delete()
                .eq("title", title)
                .execute()
            )
            success = len(result.data) > 0
            if success:
                logger.info("업무카드 삭제 완료: %s", title)
            return success
        except Exception as e:
            logger.error("업무카드 삭제 실패: %s", e)
            return False

    def delete_reception_by_title(self, title: str) -> bool:
        """제목으로 접수 문서 삭제"""
        try:
            result = (
                self.client.table("reception_mappings")
                .delete()
                .eq("title", title)
                .execute()
            )
            success = len(result.data) > 0
            if success:
                logger.info("접수 문서 삭제 완료: %s", title)
            return success
        except Exception as e:
            logger.error("접수 문서 삭제 실패: %s", e)
            return False

    def delete_all_cards(self) -> int:
        """모든 업무카드 삭제"""
        # 프로덕션 환경에서는 삭제 금지
        if os.getenv("ENVIRONMENT", "development") == "production":
            logger.error("프로덕션 환경에서는 데이터 삭제를 수행할 수 없습니다")
            return 0

        try:
            result = (
                self.client.table("task_card_mappings").delete().neq("id", "").execute()
            )
            deleted_count = len(result.data) if result.data else 0
            logger.warning("모든 업무카드 삭제 완료: %d개", deleted_count)
            return deleted_count
        except Exception as e:
            logger.error("모든 업무카드 삭제 실패: %s", e)
            return 0

    def delete_all_receptions(self) -> int:
        """모든 접수 문서 삭제"""
        # 프로덕션 환경에서는 삭제 금지
        if os.getenv("ENVIRONMENT", "development") == "production":
            logger.error("프로덕션 환경에서는 데이터 삭제를 수행할 수 없습니다")
            return 0

        try:
            result = (
                self.client.table("reception_mappings").delete().neq("id", "").execute()
            )
            deleted_count = len(result.data) if result.data else 0
            logger.warning("모든 접수 문서 삭제 완료: %d개", deleted_count)
            return deleted_count
        except Exception as e:
            logger.error("모든 접수 문서 삭제 실패: %s", e)
            return 0
