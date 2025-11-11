"""
Unit tests for text_utils module

Tests Korean text processing, ID generation, and document title cleaning functionality.
These tests run fast without external dependencies.
"""

import pytest
import uuid
from datetime import datetime

# Add src to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.text_utils import (
    clean_document_title,
    generate_document_id,
    generate_cache_key,
    is_reception_document,
    extract_title_from_approval,
    normalize_text,
    truncate_text,
    extract_keywords,
)


class TestCleanDocumentTitle:
    """Tests for document title cleaning functionality."""

    def test_basic_cleaning(self):
        """Test basic title cleaning."""
        # 기본 정리
        assert clean_document_title("  제목 앞뒤 공백  ") == "제목 앞뒤 공백"
        assert clean_document_title("\n\t제목\n\t") == "제목"

    def test_korean_text_handling(self):
        """Test Korean text is preserved properly."""
        korean_title = "2024년 예산안 검토 요청 공문"
        assert clean_document_title(korean_title) == korean_title

        mixed_title = "Budget 2024년 예산안 Review"
        assert clean_document_title(mixed_title) == mixed_title

    def test_special_character_removal(self):
        """Test removal of problematic special characters."""
        # 파일명에 사용할 수 없는 문자들
        title_with_special = '제목<>:"/\\|?*'
        cleaned = clean_document_title(title_with_special)
        assert "<" not in cleaned
        assert ">" not in cleaned
        assert ":" not in cleaned
        assert '"' not in cleaned
        assert "/" not in cleaned
        assert "\\" not in cleaned
        assert "|" not in cleaned
        assert "?" not in cleaned
        assert "*" not in cleaned

    def test_empty_and_whitespace_inputs(self):
        """Test handling of empty and whitespace-only inputs."""
        assert clean_document_title("") == ""
        assert clean_document_title("   ") == ""
        assert clean_document_title("\n\t\r") == ""

    def test_length_handling(self):
        """Test handling of very long titles."""
        long_title = "매우 " * 100 + "긴 제목입니다"
        cleaned = clean_document_title(long_title)
        assert isinstance(cleaned, str)
        assert len(cleaned) > 0

    def test_unicode_handling(self):
        """Test proper Unicode handling."""
        unicode_title = "제목에 이모지 😀 포함"
        cleaned = clean_document_title(unicode_title)
        assert "제목에" in cleaned
        # 이모지 처리는 구현에 따라 달라질 수 있음

    @pytest.mark.parametrize(
        "input_title,expected",
        [
            ("공문: 예산안 검토", "공문 예산안 검토"),  # 콜론 제거
            ("제목(부제목)", "제목(부제목)"),  # 괄호는 유지
            ("제목 - 세부사항", "제목 - 세부사항"),  # 하이픈은 유지
            ("제목.txt", "제목.txt"),  # 점은 유지
        ],
    )
    def test_specific_character_handling(self, input_title, expected):
        """Test specific character handling rules."""
        assert clean_document_title(input_title) == expected


class TestGenerateDocumentId:
    """Tests for document ID generation functionality."""

    def test_document_id_format(self):
        """Test document ID format is valid UUID."""
        title = "테스트 문서 제목"
        generated_id = generate_document_id(title)

        # UUID 형식 검증
        assert isinstance(generated_id, str)
        assert len(generated_id) == 36  # UUID는 36자
        assert generated_id.count("-") == 4  # UUID는 4개의 하이픈 포함

        # UUID 객체로 파싱 가능한지 확인
        uuid_obj = uuid.UUID(generated_id)
        assert str(uuid_obj) == generated_id

    def test_document_id_consistency(self):
        """Test that same title generates same ID."""
        title = "동일한 제목"
        id1 = generate_document_id(title)
        id2 = generate_document_id(title)

        # 같은 제목은 같은 ID 생성
        assert id1 == id2

    def test_document_id_uniqueness(self):
        """Test that different titles generate different IDs."""
        titles = [f"제목 {i}" for i in range(100)]
        ids = [generate_document_id(title) for title in titles]

        # 모든 ID가 고유한지 확인
        assert len(set(ids)) == len(ids)

    def test_document_id_version(self):
        """Test document ID version (should be version 5)."""
        generated_id = generate_document_id("테스트")
        uuid_obj = uuid.UUID(generated_id)

        # UUID5 여부 확인 (generate_document_id uses uuid5)
        assert uuid_obj.version == 5


class TestGenerateCacheKey:
    """Tests for cache key generation."""

    def test_cache_key_format(self):
        """Test cache key is a valid hash."""
        text = "캐시 키 테스트"
        cache_key = generate_cache_key(text)

        assert isinstance(cache_key, str)
        assert len(cache_key) == 64  # SHA256 hash length

        # Should be hexadecimal
        assert all(c in "0123456789abcdef" for c in cache_key)

    def test_cache_key_consistency(self):
        """Test same text generates same cache key."""
        text = "동일한 텍스트"
        key1 = generate_cache_key(text)
        key2 = generate_cache_key(text)

        assert key1 == key2

    def test_cache_key_uniqueness(self):
        """Test different texts generate different cache keys."""
        texts = [f"텍스트 {i}" for i in range(50)]
        keys = [generate_cache_key(text) for text in texts]

        assert len(set(keys)) == len(keys)


class TestIsReceptionDocument:
    """Tests for reception document detection."""

    @pytest.mark.parametrize(
        "title,expected",
        [
            ("접수: 예산안 검토 요청", True),
            ("접수 - 신입사원 채용계획", True),
            ("접수문서: 시설보수공사", True),
            ("예산안 검토 요청", False),
            ("신입사원 채용계획", False),
            ("접수처리 완료", False),  # "접수"가 포함되어 있지만 접수 문서가 아님
        ],
    )
    def test_reception_document_detection(self, title, expected):
        """Test reception document pattern detection."""
        assert is_reception_document(title) == expected

    def test_case_insensitive_detection(self):
        """Test case insensitive detection."""
        # 한글은 대소문자가 없지만, 영문이 섞여있는 경우 테스트
        assert is_reception_document("접수: BUDGET REQUEST") == True
        assert is_reception_document("접수: Budget Request") == True

    def test_empty_and_invalid_inputs(self):
        """Test handling of empty and invalid inputs."""
        assert is_reception_document("") == False
        assert is_reception_document(" ") == False
        assert is_reception_document(None) == False  # None 처리

    def test_partial_matches(self):
        """Test partial matches are handled correctly."""
        # "접수"가 단어의 일부인 경우
        assert is_reception_document("접수처") == False
        assert is_reception_document("민원접수") == False
        assert is_reception_document("접수함") == False


class TestExtractTitleFromApproval:
    """Tests for title extraction from approval context."""

    @pytest.mark.parametrize(
        "approval_text,expected_title",
        [
            ("결재요청: 2024년 예산안 검토 요청 공문", "2024년 예산안 검토 요청 공문"),
            ("승인요청 - 신입사원 채용계획", "신입사원 채용계획"),
            ("[결재] 시설 보수공사 계획서", "시설 보수공사 계획서"),
            ("제목: 교육훈련 프로그램 운영 계획", "교육훈련 프로그램 운영 계획"),
            (
                "전자결재: [ 보안등급 : ] [ 붙임 : ] 년도 중앙행정기관",
                "년도 중앙행정기관",
            ),
            ("전자결재: [ 태그1 : ] [ 태그2 : ] 실제 문서 제목", "실제 문서 제목"),
            ("전자결재: [ 태그 : ] 한 개만 있는 경우", "한 개만 있는 경우"),
        ],
    )
    def test_title_extraction_patterns(self, approval_text, expected_title):
        """Test various title extraction patterns."""
        extracted = extract_title_from_approval(approval_text)
        assert extracted == expected_title

    def test_no_pattern_match(self):
        """Test when no extraction pattern matches."""
        # 패턴이 매치되지 않는 경우 원본 반환
        original_text = "일반 문서 제목"
        extracted = extract_title_from_approval(original_text)
        assert extracted == original_text

    def test_multiple_patterns_in_text(self):
        """Test when multiple patterns exist in text."""
        # 여러 패턴이 있는 경우 첫 번째 매치 사용
        text = "결재요청: 제목1 - 승인요청: 제목2"
        extracted = extract_title_from_approval(text)
        # 구현에 따라 어떤 것이 추출되는지 확인
        assert "제목" in extracted

    def test_edge_cases(self):
        """Test edge cases."""
        # 빈 문자열
        assert extract_title_from_approval("") == ""

        # 공백만 있는 경우
        assert extract_title_from_approval("   ") == "   "

        # 패턴은 있지만 제목이 없는 경우
        result = extract_title_from_approval("결재요청:")
        assert result is not None  # 에러가 발생하지 않아야 함

    def test_korean_and_mixed_content(self):
        """Test Korean and mixed language content."""
        korean_text = "결재요청: 한글 제목입니다"
        extracted = extract_title_from_approval(korean_text)
        assert extracted == "한글 제목입니다"

        mixed_text = "결재요청: Korean 한글 English Mixed"
        extracted = extract_title_from_approval(mixed_text)
        assert extracted == "Korean 한글 English Mixed"


class TestTextUtilsIntegration:
    """Integration tests for text_utils functions working together."""

    def test_full_document_processing_pipeline(self):
        """Test complete document processing pipeline."""
        # 실제 문서 처리 시나리오를 시뮬레이션
        raw_approval_text = "  결재요청: 2024년 예산안 검토 요청 공문!@#  "

        # 1. 제목 추출
        extracted_title = extract_title_from_approval(raw_approval_text)
        assert extracted_title == "2024년 예산안 검토 요청 공문!@#  "

        # 2. 제목 정리
        cleaned_title = clean_document_title(extracted_title)
        assert cleaned_title == "2024년 예산안 검토 요청 공문"

        # 3. Document ID 생성
        document_id = generate_document_id(cleaned_title)
        assert len(document_id) == 36

        # 4. 접수 문서 여부 확인
        is_reception = is_reception_document(raw_approval_text)
        assert is_reception == False  # "결재요청"은 접수 문서가 아님

    def test_reception_document_full_pipeline(self):
        """Test reception document processing pipeline."""
        raw_text = "접수: 신입사원 채용계획 승인 요청!!!"

        # 접수 문서 감지
        assert is_reception_document(raw_text) == True

        # 제목 추출 및 정리
        extracted = extract_title_from_approval(raw_text)
        cleaned = clean_document_title(extracted)

        assert "신입사원 채용계획" in cleaned
        assert "!" not in cleaned

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "input": "결재요청: 매우!!중요한## 문서$$$",
                "expected_clean": "매우중요한 문서",
                "is_reception": False,
            },
            {
                "input": "접수: 일반적인 문서 제목",
                "expected_clean": "일반적인 문서 제목",
                "is_reception": True,
            },
        ],
    )
    def test_parameterized_full_pipeline(self, test_case):
        """Test parameterized full processing pipeline."""
        input_text = test_case["input"]

        # 처리 파이프라인
        extracted = extract_title_from_approval(input_text)
        cleaned = clean_document_title(extracted)
        is_reception = is_reception_document(input_text)
        doc_id = generate_document_id(cleaned)

        # 검증
        assert cleaned == test_case["expected_clean"]
        assert is_reception == test_case["is_reception"]
        assert len(doc_id) == 36
