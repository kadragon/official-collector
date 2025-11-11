"""
Configuration manager for centralized settings management
Provides helper functions to access configuration values
"""

import os
import logging

logger = logging.getLogger(__name__)

# Vector similarity threshold for recommendation filtering
DEFAULT_VECTOR_SIMILARITY_THRESHOLD = 0.3

# OpenAI model pricing (per 1K tokens)
OPENAI_EMBEDDING_PRICE_PER_1K = 0.00002


def get_vector_similarity_threshold() -> float:
    """
    Get the vector similarity threshold for recommendation filtering.

    Returns:
        float: Similarity threshold (0.0 to 1.0), defaults to 0.3
    """
    try:
        threshold_str = os.getenv(
            "VECTOR_SIMILARITY_THRESHOLD", str(DEFAULT_VECTOR_SIMILARITY_THRESHOLD)
        )
        threshold = float(threshold_str)

        if not 0.0 <= threshold <= 1.0:
            logger.warning("벡터 유사도 임계값 범위 초과 (%f), 기본값 사용", threshold)
            return DEFAULT_VECTOR_SIMILARITY_THRESHOLD

        return threshold
    except ValueError:
        logger.warning(
            "벡터 유사도 임계값 설정 오류, 기본값 사용 (%.1f)",
            DEFAULT_VECTOR_SIMILARITY_THRESHOLD,
        )
        return DEFAULT_VECTOR_SIMILARITY_THRESHOLD


def get_openai_embedding_price() -> float:
    """
    Get the OpenAI embedding price per 1K tokens.

    Returns:
        float: Price per 1K tokens, defaults to 0.00002 (text-embedding-3-small)
    """
    try:
        price_str = os.getenv(
            "OPENAI_EMBEDDING_PRICE_PER_1K", str(OPENAI_EMBEDDING_PRICE_PER_1K)
        )
        price = float(price_str)

        if price < 0:
            logger.warning("OpenAI 가격이 음수입니다, 기본값 사용")
            return OPENAI_EMBEDDING_PRICE_PER_1K

        return price
    except ValueError:
        logger.warning(
            "OpenAI 가격 설정 오류, 기본값 사용 (%.8f)", OPENAI_EMBEDDING_PRICE_PER_1K
        )
        return OPENAI_EMBEDDING_PRICE_PER_1K


def is_production_environment() -> bool:
    """
    Check if the application is running in production environment.

    Returns:
        bool: True if ENVIRONMENT=production, False otherwise
    """
    return os.getenv("ENVIRONMENT", "development") == "production"


def is_development_environment() -> bool:
    """
    Check if the application is running in development environment.

    Returns:
        bool: True if ENVIRONMENT=development or not set, False otherwise
    """
    return not is_production_environment()
