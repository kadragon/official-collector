"""
통합된 텍스트 및 ID 처리 유틸리티 모듈.

이 모듈은 기존의 id_generator.py와 string_processor.py를 통합하여
텍스트 처리, 문서 제목 가공, UUID 생성, 해시 생성 기능을 제공합니다.
"""

import re
import uuid
import hashlib
from typing import List


# ============================================================================
# ID 생성 및 해시 관련 함수 (기존 id_generator.py)
# ============================================================================

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


# ============================================================================
# 문자열 처리 및 문서 제목 가공 함수 (기존 string_processor.py)
# ============================================================================

def clean_document_title(title: str) -> str:
    """
    문서 제목에서 불필요한 접두사를 제거하고 정리합니다.

    Args:
        title (str): 원본 문서 제목.

    Returns:
        str: 정리된 문서 제목.
    """
    if not title:
        return ""

    # 접수 문서 처리
    if title.startswith('접수'):
        return title.replace("접수: ", '').strip()

    return title.strip()


def extract_title_from_approval(title: str) -> str:
    """
    전자결재 제목에서 실제 문서 제목을 추출합니다.

    Args:
        title (str): 전자결재 형식의 제목.

    Returns:
        str: 추출된 문서 제목.
    """
    if not title.startswith('전자결재:'):
        return title.strip()

    # 정규식을 사용하여 대괄호 부분을 제거하고 실제 제목 추출
    match = re.search(r'(?:[^]]*]){2}(.*)', title)
    if match:
        return match.group(1).strip()
    else:
        # 정규식 매칭이 실패한 경우 마지막 ] 이후의 내용을 반환
        return title.split("]")[-1].strip()


def is_reception_document(title: str) -> bool:
    """
    제목이 접수 문서인지 확인합니다.

    Args:
        title (str): 확인할 제목.

    Returns:
        bool: 접수 문서이면 True, 아니면 False.
    """
    return title.startswith('접수')


def is_approval_document(title: str) -> bool:
    """
    제목이 전자결재 문서인지 확인합니다.

    Args:
        title (str): 확인할 제목.

    Returns:
        bool: 전자결재 문서이면 True, 아니면 False.
    """
    return title.startswith('전자결재:')


def format_option_display(options: List[str], separator: str = " / ") -> str:
    """
    옵션 목록을 표시용 문자열로 포맷팅합니다.

    Args:
        options (List[str]): 옵션 목록.
        separator (str): 구분자.

    Returns:
        str: 포맷팅된 문자열.
    """
    return separator.join(f"[{idx}] {option}" for idx, option in enumerate(options))


# ============================================================================
# 추가 텍스트 처리 유틸리티 함수들
# ============================================================================

def normalize_text(text: str) -> str:
    """
    텍스트를 정규화합니다 (공백 제거, 소문자 변환 등).

    Args:
        text (str): 정규화할 텍스트.

    Returns:
        str: 정규화된 텍스트.
    """
    if not text:
        return ""
    
    return re.sub(r'\s+', ' ', text.strip())


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    텍스트를 지정된 길이로 자릅니다.

    Args:
        text (str): 자를 텍스트.
        max_length (int): 최대 길이.
        suffix (str): 생략 표시.

    Returns:
        str: 잘린 텍스트.
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def extract_keywords(text: str, min_length: int = 2) -> List[str]:
    """
    텍스트에서 키워드를 추출합니다.

    Args:
        text (str): 키워드를 추출할 텍스트.
        min_length (int): 최소 키워드 길이.

    Returns:
        List[str]: 추출된 키워드 목록.
    """
    if not text:
        return []
    
    # 한글, 영문, 숫자만 추출
    words = re.findall(r'[가-힣a-zA-Z0-9]+', text)
    
    # 최소 길이 이상의 단어만 반환
    return [word for word in words if len(word) >= min_length]


def remove_numbers_from_title(title: str) -> str:
    """
    제목에서 숫자를 제거합니다.

    Args:
        title (str): 원본 제목.

    Returns:
        str: 숫자가 제거된 제목.
    """
    if not title:
        return ""
    
    # 숫자를 제거하고 연속된 공백을 하나로 정리
    title_without_numbers = re.sub(r'\d+', '', title)
    return re.sub(r'\s+', ' ', title_without_numbers).strip()


def format_numbered_list(items: List[str], start_num: int = 1, zero_padded: bool = True) -> List[str]:
    """
    항목 목록을 번호가 매겨진 형태로 포맷팅합니다.

    Args:
        items (List[str]): 포맷팅할 항목 목록.
        start_num (int): 시작 번호.
        zero_padded (bool): 0으로 패딩할지 여부.

    Returns:
        List[str]: 번호가 매겨진 항목 목록.
    """
    if not items:
        return []
    
    format_str = f"[{{:0{len(str(len(items) + start_num - 1))}d}}] {{}}" if zero_padded else "[{}] {}"
    
    return [
        format_str.format(i + start_num, item) 
        for i, item in enumerate(items)
    ]