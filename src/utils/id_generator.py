"""
UUID 생성 및 해시 관련 유틸리티 모듈.
"""

import uuid
import hashlib


def generate_document_id(title: str, namespace: uuid.UUID = uuid.NAMESPACE_DNS) -> str:
    """
    문서 제목을 기반으로 일관된 UUID를 생성합니다.

    Args:
        title (str): 문서 제목.
        namespace (uuid.UUID): UUID 네임스페이스.

    Returns:
        str: 생성된 UUID 문자열.
    """
    return str(uuid.uuid5(namespace, title))


def generate_cache_key(text: str, encoding: str = 'utf-8') -> str:
    """
    텍스트를 기반으로 캐시 키용 해시를 생성합니다.

    Args:
        text (str): 해시할 텍스트.
        encoding (str): 텍스트 인코딩.

    Returns:
        str: SHA256 해시 문자열.
    """
    return hashlib.sha256(text.encode(encoding)).hexdigest()
