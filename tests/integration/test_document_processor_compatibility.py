"""
DocumentProcessor 호환성 테스트

기존 인터페이스가 새로운 SupabaseService와 호환되는지 검증
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.document_processor import DocumentProcessor
from services.supabase_service import SupabaseService
from ui.console_interface import SelectionResult


@pytest.fixture
def mock_supabase_service():
    """모킹된 SupabaseService 제공"""
    mock_service = MagicMock(spec=SupabaseService)

    # Mock 응답 설정
    mock_service.retrieve_reception_by_title.return_value = (None, None)
    mock_service.recommend_reception.return_value = []
    mock_service.retrieve_card_by_title.return_value = None
    mock_service.recommend_cards.return_value = []
    mock_service.upsert_reception_embedding.return_value = True
    mock_service.upsert_card_embedding.return_value = True
    mock_service.get_document_count.return_value = 0

    return mock_service


@pytest.fixture
def document_processor(mock_supabase_service):
    """DocumentProcessor 인스턴스 생성"""
    return DocumentProcessor(
        supabase_service=mock_supabase_service,
        approval_name_list=["김과장", "박대리"],
        share_name_list=["이과장", "최주임"],
        predefined_card_list=["공문관리", "예산관리", "인사관리"],
    )


class TestDocumentProcessorCompatibility:
    """DocumentProcessor 호환성 테스트"""

    def test_initialization(self, document_processor):
        """DocumentProcessor 초기화 테스트"""
        assert document_processor is not None
        assert document_processor.supabase_service is not None
        assert len(document_processor.approval_name_list) == 2
        assert len(document_processor.share_name_list) == 2
        assert len(document_processor.predefined_card_list) == 3

    def test_process_reception_document_interface(self, document_processor):
        """접수 문서 처리 인터페이스 호환성 테스트"""
        # Mock 사용자 선택을 설정
        with patch("ui.console_interface.get_valid_selection") as mock_selection:
            mock_selection.side_effect = ["김과장", "이과장"]

            result = document_processor.process_reception_document("테스트 공문")

            # 결과는 tuple (approval, shared) 형태여야 함
            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_process_task_card_matching_interface(
        self, document_processor, mock_supabase_service
    ):
        """과제 카드 매칭 인터페이스 호환성 테스트"""
        # Mock: 정확한 매칭이 있어서 사용자 입력이 필요 없는 경우
        mock_supabase_service.retrieve_card_by_title.return_value = "공문관리"

        result = document_processor.process_task_card_matching("테스트 문서")

        # 결과는 문자열이어야 함
        assert isinstance(result, str)
        assert result == "공문관리"

    def test_flush_pending_updates_interface(self, document_processor):
        """배치 업데이트 인터페이스 호환성 테스트"""
        # 인터페이스 호출 시 예외가 발생하지 않아야 함
        document_processor.flush_pending_updates()

        # Supabase service의 upsert 메서드들이 호출되지 않아야 함 (빈 큐)
        document_processor.supabase_service.upsert_reception_embedding.assert_not_called()
        document_processor.supabase_service.upsert_card_embedding.assert_not_called()

    def test_get_pending_updates_count_interface(self, document_processor):
        """대기 중인 업데이트 개수 조회 인터페이스 테스트"""
        result = document_processor.get_pending_updates_count()

        # 결과는 tuple (reception_count, card_count) 형태여야 함
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(count, int) for count in result)

    def test_statistics_interfaces(self, document_processor):
        """통계 정보 조회 인터페이스 테스트"""
        # 접수 통계
        reception_stats = document_processor.get_reception_statistics()
        assert isinstance(reception_stats, dict)

        # 과제 카드 통계
        card_stats = document_processor.get_task_card_statistics()
        assert isinstance(card_stats, dict)

    def test_reload_configuration_interface(self, document_processor):
        """설정 재로드 인터페이스 테스트"""
        new_approval = ["새담당자"]
        new_share = ["새공람자"]
        new_cards = ["새카드"]

        # 인터페이스 호출 시 예외가 발생하지 않아야 함
        document_processor.reload_configuration(new_approval, new_share, new_cards)

        # 설정이 업데이트되었는지 확인
        assert document_processor.approval_name_list == new_approval
        assert document_processor.share_name_list == new_share
        assert document_processor.predefined_card_list == new_cards

    @patch("services.document_processor.get_user_choice_from_recommendations")
    def test_batch_update_workflow(
        self,
        mock_get_choice,
        document_processor,
        mock_supabase_service,
    ):
        """배치 업데이트 워크플로우 테스트"""
        # Mock 설정: 정확한 매칭 없음 -> 추천으로 가서 사용자 선택 -> 큐에 추가
        mock_supabase_service.retrieve_reception_by_title.return_value = (None, None)
        mock_supabase_service.recommend_reception.return_value = [
            {"approval": "김과장", "share": "이과장", "similarity": 0.95}
        ]

        mock_supabase_service.retrieve_card_by_title.return_value = None
        mock_supabase_service.recommend_cards.return_value = [
            {"task_title": "공문관리", "similarity": 0.90}
        ]

        # 사용자가 첫 번째 추천을 선택 (두 번 호출됨: reception + card)
        mock_get_choice.side_effect = [
            (
                SelectionResult.SELECTED,
                "김과장 (공람: 이과장, 유사도: 95.0%)",
            ),  # reception
            (
                SelectionResult.SELECTED,
                "공문관리 (유사도: 90.0%)",
            ),  # card
        ]

        # 문서 처리 (큐에 추가됨)
        document_processor.process_reception_document("테스트 접수")
        document_processor.process_task_card_matching("테스트 과제")

        # 대기 중인 업데이트 확인
        reception_count, card_count = document_processor.get_pending_updates_count()
        assert reception_count == 1
        assert card_count == 1

        # 배치 업데이트 실행
        document_processor.flush_pending_updates()

        # Supabase service 호출 확인
        mock_supabase_service.upsert_reception_embedding.assert_called_once()
        mock_supabase_service.upsert_card_embedding.assert_called_once()

        # 큐가 비워졌는지 확인
        reception_count, card_count = document_processor.get_pending_updates_count()
        assert reception_count == 0
        assert card_count == 0


@pytest.mark.integration
class TestRealSupabaseIntegration:
    """실제 Supabase와의 통합 테스트 (환경변수 필요)"""

    @pytest.fixture
    def real_document_processor(self):
        """실제 SupabaseService를 사용하는 DocumentProcessor"""
        try:
            # 의존성 주입: embedding_service를 생성자에 전달
            from services.openai_embedding_service import OpenAIEmbeddingService

            embedding_service = OpenAIEmbeddingService()
            supabase_service = SupabaseService(embedding_service)
            return DocumentProcessor(
                supabase_service=supabase_service,
                approval_name_list=["테스트담당자"],
                share_name_list=["테스트공람자"],
                predefined_card_list=["테스트카드"],
            )
        except Exception as e:
            if "SUPABASE_URL" in str(e) or "SUPABASE_KEY" in str(e):
                pytest.skip("Supabase 환경변수가 설정되지 않음")
            raise

    def test_real_integration_workflow(self, real_document_processor):
        """실제 환경에서의 통합 워크플로우 테스트"""
        processor = real_document_processor

        # 통계 조회 (연결 테스트)
        stats = processor.get_reception_statistics()
        assert isinstance(stats, dict)

        # 배치 업데이트 시스템 테스트
        initial_count = processor.get_pending_updates_count()
        assert isinstance(initial_count, tuple)

        # 빈 플러시 (오류 없이 실행되어야 함)
        processor.flush_pending_updates()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
