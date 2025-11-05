"""
OpenAI 임베딩 서비스 클래스
텍스트 임베딩 생성, 배치 처리, 에러 핸들링, 비용 추적 기능 제공
"""

import os
import logging
import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

import openai
from dotenv import load_dotenv
from utils.performance_logger import log_execution_time

# 환경변수 로드
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingRequest:
    """임베딩 요청 데이터"""

    text: str
    identifier: str  # 문서 ID 또는 고유 식별자
    metadata: Dict[str, Any] | None = None


@dataclass
class EmbeddingResponse:
    """임베딩 응답 데이터"""

    identifier: str
    embedding: List[float]
    text: str
    token_count: int
    metadata: Dict[str, Any] | None = None


@dataclass
class CostTracker:
    """비용 추적기"""

    total_tokens: int = 0
    total_requests: int = 0
    total_cost: float = 0.0
    start_time: datetime | None = None

    def add_request(self, token_count: int) -> None:
        """요청 추가"""
        if self.start_time is None:
            self.start_time = datetime.now()

        self.total_tokens += token_count
        self.total_requests += 1
        # text-embedding-3-small 가격: $0.00002 per 1K tokens
        self.total_cost += (token_count / 1000) * 0.00002


class OpenAIEmbeddingService:
    """OpenAI 임베딩 서비스"""

    def __init__(self, model: str = "text-embedding-3-small", max_retry: int = 3):
        """OpenAI 임베딩 서비스 초기화"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 필요합니다")

        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)

        self.model = model
        self.max_retry = max_retry
        self.cost_tracker = CostTracker()

        # 모델별 차원 수
        self.model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

        logger.info(f"OpenAI 임베딩 서비스 초기화 완료 - 모델: {self.model}")

    def get_embedding_dimension(self) -> int:
        """현재 모델의 임베딩 차원 수 반환"""
        return self.model_dimensions.get(self.model, 1536)

    @log_execution_time(logger, "OpenAI 임베딩 생성")
    def create_embedding(
        self,
        text: str,
        identifier: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Optional[EmbeddingResponse]:
        """단일 텍스트 임베딩 생성"""
        if not text or not text.strip():
            logger.warning("빈 텍스트에 대한 임베딩 요청")
            return None

        for attempt in range(self.max_retry):
            try:
                response = self.client.embeddings.create(
                    model=self.model, input=text.strip(), encoding_format="float"
                )

                embedding_data = response.data[0]
                token_count = response.usage.total_tokens

                # 비용 추적
                self.cost_tracker.add_request(token_count)

                result = EmbeddingResponse(
                    identifier=identifier or f"embed_{int(time.time())}",
                    embedding=embedding_data.embedding,
                    text=text,
                    token_count=token_count,
                    metadata=metadata or {},
                )

                logger.debug(f"임베딩 생성 완료: {identifier}, 토큰: {token_count}")
                return result

            except openai.RateLimitError as e:
                wait_time = 2**attempt
                logger.warning(
                    f"Rate limit 초과, {wait_time}초 대기 중... (시도 {attempt + 1}/{self.max_retry})"
                )
                time.sleep(wait_time)

            except openai.APIError as e:
                logger.error(
                    f"OpenAI API 오류 (시도 {attempt + 1}/{self.max_retry}): {e}"
                )
                if attempt == self.max_retry - 1:
                    raise
                time.sleep(1)

            except Exception as e:
                logger.error(f"임베딩 생성 중 예상치 못한 오류: {e}")
                if attempt == self.max_retry - 1:
                    raise
                time.sleep(1)

        return None

    def create_embeddings_batch(
        self, requests: List[EmbeddingRequest], batch_size: int = 100
    ) -> List[EmbeddingResponse]:
        """Creates embeddings in batches with retry handling."""
        results: List[EmbeddingResponse] = []
        if not requests:
            return results

        total_batches = (len(requests) + batch_size - 1) // batch_size
        logger.info(
            "Batch embedding start: %d requests across %d batches",
            len(requests),
            total_batches,
        )

        index = 0
        while index < len(requests):
            batch = requests[index : index + batch_size]
            batch_num = index // batch_size + 1
            logger.info(
                "Processing batch %d/%d (%d items)",
                batch_num,
                total_batches,
                len(batch),
            )

            valid_items = [
                (req, req.text.strip())
                for req in batch
                if req.text and req.text.strip()
            ]

            if not valid_items:
                logger.warning("Batch %d had no valid text inputs", batch_num)
                index += len(batch)
                continue

            attempts = 0
            while True:
                try:
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=[text for _, text in valid_items],
                        encoding_format="float",
                    )

                    avg_tokens = 0
                    if response.usage and response.usage.total_tokens:
                        avg_tokens = response.usage.total_tokens // max(
                            len(valid_items), 1
                        )
                        self.cost_tracker.add_request(response.usage.total_tokens)

                    for (req, original_text), embedding_data in zip(
                        valid_items, response.data
                    ):
                        results.append(
                            EmbeddingResponse(
                                identifier=req.identifier,
                                embedding=embedding_data.embedding,
                                text=req.text,
                                token_count=avg_tokens,
                                metadata=req.metadata or {},
                            )
                        )

                    if batch_num < total_batches:
                        time.sleep(0.1)

                    index += len(batch)
                    break

                except openai.RateLimitError as error:
                    attempts += 1
                    wait_time = min(60, 2**attempts)
                    logger.warning(
                        "Batch %d rate limited (attempt %d/%d): %s",
                        batch_num,
                        attempts,
                        self.max_retry,
                        error,
                    )
                    if attempts >= self.max_retry:
                        logger.error(
                            "Batch %d exceeded retry limits; falling back to per-request processing",
                            batch_num,
                        )
                        for req, _ in valid_items:
                            individual_result = self.create_embedding(
                                req.text, req.identifier, req.metadata
                            )
                            if individual_result:
                                results.append(individual_result)
                        index += len(batch)
                        break

                    time.sleep(wait_time)

                except openai.APIError as error:
                    attempts += 1
                    logger.error(
                        "OpenAI API error for batch %d (attempt %d/%d): %s",
                        batch_num,
                        attempts,
                        self.max_retry,
                        error,
                    )
                    if attempts >= self.max_retry:
                        raise
                    time.sleep(1)

                except Exception as error:
                    logger.error(f"Batch {batch_num} processing failed: {error}")
                    for req, _ in valid_items:
                        individual_result = self.create_embedding(
                            req.text, req.identifier, req.metadata
                        )
                        if individual_result:
                            results.append(individual_result)
                    index += len(batch)
                    break

        logger.info("Batch embedding complete: %d embeddings generated", len(results))
        return results

    def create_embeddings_from_texts(
        self,
        texts: List[str],
        identifiers: List[str] | None = None,
        batch_size: int = 100,
    ) -> List[EmbeddingResponse]:
        """텍스트 목록에서 임베딩 생성"""
        if not texts:
            return []

        # EmbeddingRequest 객체 생성
        requests = []
        for i, text in enumerate(texts):
            identifier = (
                identifiers[i] if identifiers and i < len(identifiers) else f"text_{i}"
            )
            requests.append(EmbeddingRequest(text=text, identifier=identifier))

        return self.create_embeddings_batch(requests, batch_size)

    def similarity_search(
        self,
        query_text: str,
        embeddings: List[List[float]],
        texts: List[str] | None = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """임베딩 기반 유사도 검색"""
        query_embedding_response = self.create_embedding(query_text, "query")
        if not query_embedding_response:
            return []

        query_embedding = query_embedding_response.embedding

        # 코사인 유사도 계산
        similarities = []
        for i, embedding in enumerate(embeddings):
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities.append(
                {
                    "index": i,
                    "similarity": similarity,
                    "text": texts[i] if texts and i < len(texts) else None,
                }
            )

        # 유사도 기준 정렬
        similarities.sort(key=lambda x: x["similarity"], reverse=True)  # type: ignore[arg-type,return-value]

        return similarities[:top_k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def get_cost_summary(self) -> Dict[str, Any]:
        """비용 요약 정보 반환"""
        duration = None
        if self.cost_tracker.start_time:
            duration = datetime.now() - self.cost_tracker.start_time

        return {
            "model": self.model,
            "total_requests": self.cost_tracker.total_requests,
            "total_tokens": self.cost_tracker.total_tokens,
            "total_cost_usd": round(self.cost_tracker.total_cost, 6),
            "average_tokens_per_request": (
                self.cost_tracker.total_tokens // self.cost_tracker.total_requests
                if self.cost_tracker.total_requests > 0
                else 0
            ),
            "duration_seconds": duration.total_seconds() if duration else 0,
            "start_time": (
                self.cost_tracker.start_time.isoformat()
                if self.cost_tracker.start_time
                else None
            ),
        }

    def reset_cost_tracker(self) -> None:
        """비용 추적기 재설정"""
        self.cost_tracker = CostTracker()
        logger.info("비용 추적기가 재설정되었습니다")

    def validate_api_key(self) -> bool:
        """API 키 유효성 검사"""
        try:
            response = self.client.embeddings.create(
                model=self.model, input="test", encoding_format="float"
            )
            return True
        except Exception as e:
            logger.error(f"API 키 검증 실패: {e}")
            return False

    def get_supported_models(self) -> List[str]:
        """지원되는 모델 목록 반환"""
        return list(self.model_dimensions.keys())

    def estimate_cost(self, text_length: int) -> float:
        """텍스트 길이 기반 비용 추정 (매우 대략적)"""
        # 대략 4글자 = 1토큰으로 추정
        estimated_tokens = text_length // 4
        # text-embedding-3-small 가격: $0.00002 per 1K tokens
        estimated_cost = (estimated_tokens / 1000) * 0.00002
        return estimated_cost
