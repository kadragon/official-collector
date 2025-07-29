"""
UUID 생성 및 해시 관련 유틸리티 모듈.
"""

import uuid
import hashlib
from typing import Union


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


def generate_reception_id(title: str) -> str:
    """
    접수 문서용 ID를 생성합니다.

    Args:
        title (str): 접수 문서 제목.

    Returns:
        str: 생성된 ID.
    """
    return generate_document_id(title)


def generate_task_card_id(title: str) -> str:
    """
    과제 카드용 ID를 생성합니다.

    Args:
        title (str): 과제 카드 제목.

    Returns:
        str: 생성된 ID.
    """
    return generate_document_id(title)


def generate_session_id() -> str:
    """
    세션용 고유 ID를 생성합니다.

    Returns:
        str: 생성된 세션 ID.
    """
    return str(uuid.uuid4())




def validate_uuid(uuid_string: str) -> bool:
    """
    UUID 문자열이 유효한지 검증합니다.

    Args:
        uuid_string (str): 검증할 UUID 문자열.

    Returns:
        bool: 유효하면 True, 아니면 False.
    """
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False


def create_composite_id(*components: Union[str, int]) -> str:
    """
    여러 구성 요소를 조합하여 복합 ID를 생성합니다.

    Args:
        *components: ID 구성 요소들.

    Returns:
        str: 생성된 복합 ID.
    """
    combined = "_".join(str(component) for component in components)
    return generate_cache_key(combined)


def generate_hash_from_dict(data: dict) -> str:
    """
    딕셔너리 데이터를 기반으로 해시를 생성합니다.

    Args:
        data (dict): 해시할 딕셔너리 데이터.

    Returns:
        str: 생성된 해시.
    """
    # 딕셔너리를 정렬된 문자열로 변환하여 일관된 해시 생성
    sorted_items = sorted(data.items())
    data_string = str(sorted_items)
    return generate_cache_key(data_string)