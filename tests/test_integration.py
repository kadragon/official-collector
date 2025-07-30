"""
Pytest-based integration tests for Ollama and Chroma
Run with: pytest tests/test_integration.py -v
"""

import pytest
import tempfile
import shutil
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.chroma_service import ChromaService
from config import config
from langchain_ollama import OllamaEmbeddings


@pytest.fixture
def temp_chroma_service():
    """Create a temporary ChromaService for testing"""
    temp_dir = tempfile.mkdtemp()
    
    service = ChromaService(
        ollama_base_url=config.ollama_base_url,
        ollama_model=config.ollama_model,
        chroma_persist_dir=temp_dir,
        collection_name="pytest_test"
    )
    
    yield service
    
    # Cleanup
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass


@pytest.fixture
def persistent_chroma_service():
    """Create a ChromaService for testing with cleanup after test completion"""
    persist_dir = "./chroma_db_test"
    
    # Clean up any existing test database first
    try:
        shutil.rmtree(persist_dir)
    except Exception:
        pass
    
    service = ChromaService(
        ollama_base_url=config.ollama_base_url,
        ollama_model=config.ollama_model,
        chroma_persist_dir=persist_dir,
        collection_name="pytest_persistent"
    )
    
    yield service
    
    # Cleanup test database after test
    try:
        # Close any connections by explicitly deleting the service
        if 'service' in locals():
            del service
        import time
        import gc
        gc.collect()  # Force garbage collection
        time.sleep(0.1)  # Brief wait for file handles to be released
        
        # Note: Actual cleanup is handled by conftest.py session fixture
        # This is just a best-effort immediate cleanup
        try:
            shutil.rmtree(persist_dir)
        except Exception:
            # Expected on Windows - conftest.py will handle final cleanup
            pass
    except Exception:
        pass


class TestEnvironmentConfig:
    """Test environment configuration"""
    
    def test_required_env_vars_exist(self):
        """Test that required environment variables are set"""
        assert config.ollama_base_url is not None, "OLLAMA_BASE_URL not set"
        assert config.ollama_model is not None, "OLLAMA_MODEL not set"
        assert config.chroma_persist_dir is not None, "CHROMA_PERSIST_DIR not set"
    
    def test_ollama_config_format(self):
        """Test that Ollama configuration has correct format"""
        assert config.ollama_base_url.startswith("http"), "OLLAMA_BASE_URL should start with http"
        assert len(config.ollama_model) > 0, "OLLAMA_MODEL should not be empty"


class TestOllamaIntegration:
    """Test Ollama embedding functionality"""
    
    def test_ollama_connection(self):
        """Test basic Ollama connection"""
        embeddings = OllamaEmbeddings(
            base_url=config.ollama_base_url,
            model=config.ollama_model
        )
        
        # This will raise an exception if Ollama is not accessible
        result = embeddings.embed_query("test")
        
        assert isinstance(result, list), "Embedding should return a list"
        assert len(result) > 0, "Embedding should not be empty"
        assert all(isinstance(x, (int, float)) for x in result), "Embedding should contain numbers"
    
    def test_korean_text_embedding(self):
        """Test embedding Korean text"""
        embeddings = OllamaEmbeddings(
            base_url=config.ollama_base_url,
            model=config.ollama_model
        )
        
        korean_text = "안녕하세요"
        result = embeddings.embed_query(korean_text)
        
        assert len(result) > 0, "Korean text embedding should work"
    
    def test_embedding_consistency(self):
        """Test that same input produces same embedding"""
        embeddings = OllamaEmbeddings(
            base_url=config.ollama_base_url,
            model=config.ollama_model
        )
        
        text = "consistency test"
        result1 = embeddings.embed_query(text)
        result2 = embeddings.embed_query(text)
        
        assert result1 == result2, "Same input should produce same embedding"


class TestChromaService:
    """Test ChromaService functionality"""
    
    def test_service_initialization(self, temp_chroma_service):
        """Test that ChromaService initializes correctly"""
        assert temp_chroma_service is not None
        assert temp_chroma_service.vector_store is not None
    
    def test_card_operations(self, temp_chroma_service):
        """Test basic card CRUD operations"""
        service = temp_chroma_service
        
        # Test upsert
        service.upsert_card_embedding("테스트 문서", "테스트 카드")
        
        # Test retrieve
        result = service.retrieve_card_by_title("테스트 문서")
        assert result == "테스트 카드", f"Expected '테스트 카드', got '{result}'"
        
        # Test exists
        assert service.card_exists("테스트 문서"), "Card should exist"
        assert not service.card_exists("존재하지 않는 문서"), "Non-existent card should not exist"
        
        # Test delete
        assert service.delete_card_by_title("테스트 문서"), "Card deletion should succeed"
        assert not service.card_exists("테스트 문서"), "Card should not exist after deletion"
    
    def test_reception_operations(self, temp_chroma_service):
        """Test basic reception CRUD operations"""
        service = temp_chroma_service
        
        # Test upsert
        service.upsert_reception_embedding("민원 접수", "김과장", "이대리,박사원")
        
        # Test retrieve
        approval, share = service.retrieve_reception_by_title("민원 접수")
        assert approval == "김과장", f"Expected '김과장', got '{approval}'"
        assert share == "이대리,박사원", f"Expected '이대리,박사원', got '{share}'"
        
        # Test exists
        assert service.reception_exists("민원 접수"), "Reception should exist"
        assert not service.reception_exists("존재하지 않는 접수"), "Non-existent reception should not exist"
        
        # Test delete
        assert service.delete_reception_by_title("민원 접수"), "Reception deletion should succeed"
        assert not service.reception_exists("민원 접수"), "Reception should not exist after deletion"
    
    def test_similarity_search(self, temp_chroma_service):
        """Test similarity search functionality"""
        service = temp_chroma_service
        
        # Add test data
        test_cards = [
            ("공문 작성 요청", "공문관리"),
            ("예산 승인 요청", "예산관리"),
            ("인사발령 통지", "인사관리")
        ]
        
        for title, task_title in test_cards:
            service.upsert_card_embedding(title, task_title)
        
        # Test similarity search
        recommendations = service.recommend_cards("공문 관련 업무", count=2)
        assert len(recommendations) > 0, "Should return recommendations"
        assert "공문관리" in recommendations, "Should recommend related cards"
    
    def test_list_operations(self, temp_chroma_service):
        """Test list all operations"""
        service = temp_chroma_service
        
        # Add test data
        service.upsert_card_embedding("카드1", "작업1")
        service.upsert_card_embedding("카드2", "작업2")
        service.upsert_reception_embedding("접수1", "담당자1", "공람1")
        service.upsert_reception_embedding("접수2", "담당자2", "공람2")
        
        # Test list operations
        cards = service.list_all_cards()
        receptions = service.list_all_receptions()
        
        assert len(cards) == 2, f"Expected 2 cards, got {len(cards)}"
        assert len(receptions) == 2, f"Expected 2 receptions, got {len(receptions)}"
        
        # Check data structure
        assert all(len(card) == 3 for card in cards), "Cards should have 3 fields"
        assert all(len(reception) == 4 for reception in receptions), "Receptions should have 4 fields"
    
    def test_bulk_operations(self, temp_chroma_service):
        """Test bulk delete operations"""
        service = temp_chroma_service
        
        # Add multiple test items
        card_titles = ["카드1", "카드2", "카드3"]
        reception_titles = ["접수1", "접수2", "접수3"]
        
        for title in card_titles:
            service.upsert_card_embedding(title, f"작업_{title}")
        
        for title in reception_titles:
            service.upsert_reception_embedding(title, f"담당_{title}", "공람")
        
        # Test bulk delete
        deleted_cards = service.bulk_delete_cards(card_titles)
        deleted_receptions = service.bulk_delete_receptions(reception_titles)
        
        assert deleted_cards == len(card_titles), f"Expected {len(card_titles)} deleted, got {deleted_cards}"
        assert deleted_receptions == len(reception_titles), f"Expected {len(reception_titles)} deleted, got {deleted_receptions}"
        
        # Verify deletion
        assert len(service.list_all_cards()) == 0, "All cards should be deleted"
        assert len(service.list_all_receptions()) == 0, "All receptions should be deleted"


@pytest.mark.integration
class TestFullIntegration:
    """Full integration tests"""
    
    def test_end_to_end_workflow(self, temp_chroma_service):
        """Test complete workflow from embedding to retrieval"""
        service = temp_chroma_service
        
        # Simulate real usage workflow
        # 1. Add some historical data
        service.upsert_card_embedding("예산 계획서 작성", "예산관리")
        service.upsert_card_embedding("인사 발령장 작성", "인사관리")
        
        # 2. New document comes in
        new_document = "내년도 예산안 검토"
        
        # 3. Try exact match first (should fail)
        exact_match = service.retrieve_card_by_title(new_document)
        assert exact_match is None, "Should not find exact match for new document"
        
        # 4. Get recommendations
        recommendations = service.recommend_cards(new_document, count=3)
        assert len(recommendations) > 0, "Should get recommendations"
        assert "예산관리" in recommendations, "Should recommend budget-related card"
        
        # 5. User selects recommendation and system learns
        selected_card = "예산관리"
        service.upsert_card_embedding(new_document, selected_card)
        
        # 6. Next time, exact match should work
        exact_match = service.retrieve_card_by_title(new_document)
        assert exact_match == selected_card, "Should now have exact match after learning"

    def test_persistent_database_inspection(self, persistent_chroma_service):
        """Test with persistent database that survives test completion"""
        service = persistent_chroma_service
        
        # Add some sample data for inspection
        service.upsert_card_embedding("공문 작성 요청", "공문관리")
        service.upsert_card_embedding("예산 검토 요청", "예산관리")
        service.upsert_reception_embedding("민원 처리", "김대리", "이과장,박주임")
        
        # Verify data was added
        cards = service.list_all_cards()
        receptions = service.list_all_receptions()
        
        assert len(cards) >= 2, "Should have at least 2 cards"
        assert len(receptions) >= 1, "Should have at least 1 reception"
        
        print(f"\n=== Database inspection ===")
        print(f"Database location: ./chroma_db_test")
        print(f"Cards stored: {len(cards)}")
        print(f"Receptions stored: {len(receptions)}")
        print("Database will be cleaned up after test completion")


if __name__ == "__main__":
    # Allow running directly with python
    pytest.main([__file__, "-v"])