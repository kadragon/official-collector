"""
문자열 처리 및 문서 제목 가공을 위한 유틸리티 모듈.
"""

import re
from typing import Optional


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


def normalize_text(text: str) -> str:
    """
    텍스트를 정규화합니다 (공백 정리, 특수문자 처리 등).

    Args:
        text (str): 정규화할 텍스트.

    Returns:
        str: 정규화된 텍스트.
    """
    if not text:
        return ""
    
    # 연속된 공백을 하나로 줄이고 앞뒤 공백 제거
    normalized = re.sub(r'\s+', ' ', text.strip())
    
    return normalized


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


def extract_document_type(title: str) -> str:
    """
    문서 제목에서 문서 유형을 추출합니다.

    Args:
        title (str): 문서 제목.

    Returns:
        str: 문서 유형 ('reception', 'approval', 'general').
    """
    if is_reception_document(title):
        return 'reception'
    elif is_approval_document(title):
        return 'approval'
    else:
        return 'general'


def format_option_display(options: list, separator: str = " / ") -> str:
    """
    옵션 목록을 표시용 문자열로 포맷팅합니다.

    Args:
        options (list): 옵션 목록.
        separator (str): 구분자.

    Returns:
        str: 포맷팅된 문자열.
    """
    return separator.join(f"[{idx}] {option}" for idx, option in enumerate(options))


def sanitize_filename(filename: str) -> str:
    """
    파일명에서 사용할 수 없는 문자를 제거합니다.

    Args:
        filename (str): 원본 파일명.

    Returns:
        str: 정리된 파일명.
    """
    # Windows에서 파일명에 사용할 수 없는 문자들 제거
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # 연속된 언더스코어를 하나로 줄이기
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # 앞뒤 언더스코어 및 공백 제거
    return sanitized.strip('_ ')


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    텍스트를 지정된 길이로 자릅니다.

    Args:
        text (str): 원본 텍스트.
        max_length (int): 최대 길이.
        suffix (str): 잘렸을 때 추가할 접미사.

    Returns:
        str: 잘린 텍스트.
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix