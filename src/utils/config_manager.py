"""
Configuration manager for centralized settings management
Provides helper functions to access configuration values

DEPRECATED: This module is being phased out. Use config.UnifiedConfig instead.
"""

import os
import logging
import warnings
from config import OpenAIPricingConfig, get_config

logger = logging.getLogger(__name__)


def get_vector_similarity_threshold() -> float:
    """
    Get the vector similarity threshold for recommendation filtering.

    .. deprecated:: 2025-11-13
        Use `config.UnifiedConfig.get_vector_similarity_threshold()` instead.

    Returns:
        float: Similarity threshold (0.0 to 1.0), defaults to 0.3
    """
    warnings.warn(
        "get_vector_similarity_threshold() is deprecated. "
        "Use config.UnifiedConfig.get_vector_similarity_threshold() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_config().get_vector_similarity_threshold()


def get_openai_embedding_price() -> float:
    """
    Get the OpenAI embedding price per 1K tokens.

    Returns:
        float: Price per 1K tokens, defaults to 0.00002 (text-embedding-3-small)
    """
    try:
        price_str = os.getenv(
            "OPENAI_EMBEDDING_PRICE_PER_1K",
            str(OpenAIPricingConfig.TEXT_EMBEDDING_3_SMALL_PRICE),
        )
        price = float(price_str)

        if price < 0:
            logger.warning("OpenAI 가격이 음수입니다, 기본값 사용")
            return OpenAIPricingConfig.TEXT_EMBEDDING_3_SMALL_PRICE

        return price
    except ValueError:
        logger.warning(
            "OpenAI 가격 설정 오류, 기본값 사용 (%.8f)",
            OpenAIPricingConfig.TEXT_EMBEDDING_3_SMALL_PRICE,
        )
        return OpenAIPricingConfig.TEXT_EMBEDDING_3_SMALL_PRICE


def is_production_environment() -> bool:
    """
    Check if the application is running in production environment.

    .. deprecated:: 2025-11-13
        Use `config.UnifiedConfig.allow_destructive_operations()` for operation gating.

    Returns:
        bool: True if ENVIRONMENT=production, False otherwise
    """
    return os.getenv("ENVIRONMENT", "development") == "production"


def is_development_environment() -> bool:
    """
    Check if the application is running in development environment.

    .. deprecated:: 2025-11-13
        Use `config.UnifiedConfig.allow_destructive_operations()` for operation gating.

    Returns:
        bool: True if ENVIRONMENT=development or not set, False otherwise
    """
    return not is_production_environment()
