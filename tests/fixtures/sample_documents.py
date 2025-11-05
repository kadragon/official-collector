"""
Sample Korean document data for testing

This module provides realistic Korean document samples for testing
document processing, classification, and matching functionality.
"""

from typing import List, Dict, Any


class SampleDocuments:
    """Korean document samples for testing."""

    # 접수 문서 샘플
    RECEPTION_DOCUMENTS = [
        {
            "title": "2024년 예산안 검토 요청 공문",
            "content": "귀하의 건승을 기원하며, 2024년도 예산안에 대한 검토를 요청드립니다.",
            "expected_approval": "예산담당자",
            "expected_share": "기획팀",
        },
        {
            "title": "신입사원 채용계획 승인 요청",
            "content": "2024년 하반기 신입사원 채용계획에 대한 승인을 요청드립니다.",
            "expected_approval": "인사담당자",
            "expected_share": "총무팀",
        },
        {
            "title": "시설 보수공사 계획서",
            "content": "노후화된 사무실 시설 보수공사 계획서를 제출합니다.",
            "expected_approval": "시설담당자",
            "expected_share": "관리팀",
        },
        {
            "title": "교육훈련 프로그램 운영 계획",
            "content": "직원 역량강화를 위한 교육훈련 프로그램 운영계획을 제출합니다.",
            "expected_approval": "교육담당자",
            "expected_share": "인사팀",
        },
    ]

    # 과제 카드 샘플
    TASK_CARDS = [
        {
            "title": "예산관리 업무",
            "description": "연간 예산 수립 및 집행 관리",
            "category": "재정관리",
        },
        {
            "title": "인사관리 업무",
            "description": "직원 채용, 교육, 평가 등 인사업무 전반",
            "category": "인사관리",
        },
        {
            "title": "시설관리 업무",
            "description": "사무실 시설 유지보수 및 관리",
            "category": "시설관리",
        },
        {
            "title": "교육기획 업무",
            "description": "직원교육 프로그램 기획 및 운영",
            "category": "교육관리",
        },
        {
            "title": "정보보안 업무",
            "description": "조직 정보보안 정책 수립 및 관리",
            "category": "보안관리",
        },
    ]

    # 문서 매칭 테스트 케이스
    DOCUMENT_MATCHING_CASES = [
        {
            "document_title": "2024년 예산안 검토 요청 공문",
            "expected_task_card": "예산관리 업무",
            "similarity_threshold": 0.7,
        },
        {
            "document_title": "신입사원 채용계획 승인 요청",
            "expected_task_card": "인사관리 업무",
            "similarity_threshold": 0.6,
        },
        {
            "document_title": "시설 보수공사 계획서",
            "expected_task_card": "시설관리 업무",
            "similarity_threshold": 0.8,
        },
        {
            "document_title": "직원 보안교육 계획서",
            "expected_matches": ["교육기획 업무", "정보보안 업무"],
            "similarity_threshold": 0.5,
        },
    ]

    # 에지 케이스 테스트 데이터
    EDGE_CASES = [
        {"title": "", "content": "", "expected_error": "EmptyTitleError"},  # 빈 제목
        {"title": "매우 짧은 제목", "content": "내용", "expected_behavior": "no_match"},
        {
            "title": "특수문자가 포함된 제목!@#$%^&*()",
            "content": "특수문자 처리 테스트용 문서입니다.",
            "expected_behavior": "cleaned_processing",
        },
        {
            "title": "아주 " * 50 + "긴 제목입니다",  # 매우 긴 제목
            "content": "긴 제목 처리 테스트",
            "expected_behavior": "truncated_processing",
        },
    ]

    @staticmethod
    def get_sample_reception_document(index: int = 0) -> Dict[str, Any]:
        """접수 문서 샘플을 반환합니다."""
        return SampleDocuments.RECEPTION_DOCUMENTS[
            index % len(SampleDocuments.RECEPTION_DOCUMENTS)
        ]

    @staticmethod
    def get_sample_task_card(index: int = 0) -> Dict[str, Any]:
        """과제 카드 샘플을 반환합니다."""
        return SampleDocuments.TASK_CARDS[index % len(SampleDocuments.TASK_CARDS)]

    @staticmethod
    def get_all_document_titles() -> List[str]:
        """모든 문서 제목 목록을 반환합니다."""
        return [doc["title"] for doc in SampleDocuments.RECEPTION_DOCUMENTS]

    @staticmethod
    def get_all_task_card_titles() -> List[str]:
        """모든 과제 카드 제목 목록을 반환합니다."""
        return [card["title"] for card in SampleDocuments.TASK_CARDS]


class TestDataGenerator:
    """테스트 데이터 생성 유틸리티."""

    @staticmethod
    def generate_document_variants(base_title: str, count: int = 5) -> List[str]:
        """기본 제목을 기반으로 변형된 문서 제목들을 생성합니다."""
        variations = [
            f"{base_title} (수정안)",
            f"{base_title} - 1차",
            f"긴급: {base_title}",
            f"{base_title} 관련 추가 자료",
            f"[참고] {base_title}",
        ]
        return variations[:count]

    @staticmethod
    def create_similar_titles(base_title: str) -> List[str]:
        """유사한 제목들을 생성하여 유사도 테스트에 사용합니다."""
        words = base_title.split()
        if len(words) < 2:
            return [base_title]

        # 단어 순서 변경, 일부 단어 추가/제거 등
        similar_titles = [
            " ".join(words[::-1]),  # 단어 순서 뒤바꿈
            " ".join(words[1:]),  # 첫 단어 제거
            f"추가 {base_title}",  # 앞에 단어 추가
            f"{base_title} 보고서",  # 뒤에 단어 추가
        ]
        return similar_titles
