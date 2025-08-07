"""
Integration tests for complete document processing workflows.

Tests end-to-end document processing including:
- Document ingestion and classification
- Vector similarity search 
- Task card matching
- User interaction workflows

These tests require external services (Ollama, Chroma) to be running.
"""

import pytest
import tempfile
import shutil
import time
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.chroma_service import ChromaService
from services.document_processor import DocumentProcessor
from ui.console_interface import ConsoleInterface, SelectionResult
from config import config
from tests.fixtures.sample_documents import SampleDocuments
from tests.fixtures.mock_responses import MockUserInterface


@pytest.mark.integration
class TestDocumentProcessingWorkflow:
    """Test complete document processing workflows."""
    
    @pytest.fixture(autouse=True)
    def setup_services(self):
        """Set up test services."""
        # Create temporary directories
        self.temp_dir_reception = tempfile.mkdtemp(prefix="test_reception_")
        self.temp_dir_tasks = tempfile.mkdtemp(prefix="test_tasks_")
        
        try:
            # Initialize services
            self.reception_service = ChromaService(
                ollama_base_url=config.ollama_base_url,
                ollama_model=config.ollama_model,
                chroma_persist_dir=self.temp_dir_reception,
                collection_name="test_receptions"
            )
            
            self.task_service = ChromaService(
                ollama_base_url=config.ollama_base_url,
                ollama_model=config.ollama_model,
                chroma_persist_dir=self.temp_dir_tasks,
                collection_name="test_tasks"
            )
            
            # Load test data
            self.sample_docs = SampleDocuments()
            self.test_data = self.sample_docs.RECEPTION_DOCUMENTS
            self.test_tasks = self.sample_docs.TASK_CARDS
            
            # Initialize document processor
            self.processor = DocumentProcessor(
                reception_chroma=self.reception_service,
                task_card_chroma=self.task_service,
                approval_name_list=[doc["expected_approval"] for doc in self.test_data],
                share_name_list=[doc["expected_share"] for doc in self.test_data],
                predefined_card_list=[card["title"] for card in self.test_tasks]
            )
            
            yield
            
        finally:
            # Cleanup
            for service in [self.reception_service, self.task_service]:
                if service:
                    try:
                        del service
                    except Exception:
                        pass
            
            for temp_dir in [self.temp_dir_reception, self.temp_dir_tasks]:
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass
    
    def test_reception_document_processing_workflow(self):
        """Test complete reception document processing workflow."""
        # 1. Add sample reception documents
        for i, doc in enumerate(self.test_data[:3]):
            success = self.reception_service.add_reception_document(
                title=doc["title"],
                approval=doc["expected_approval"],
                share=doc["expected_share"]
            )
            assert success, f"Failed to add document {i}: {doc['title']}"
        
        # 2. Process new reception document
        new_doc = self.test_data[0]  # Use first document as new incoming
        
        result = self.processor.process_reception_document(
            title=new_doc["title"]
        )
        
        # 3. Verify result
        assert result is not None
        assert "approval" in result
        assert "share" in result
        
        # Should match expected values or be reasonable alternatives
        assert result["approval"] in [doc["expected_approval"] for doc in self.test_data]
        assert result["share"] in [doc["expected_share"] for doc in self.test_data]
    
    def test_task_card_matching_workflow(self):
        """Test complete task card matching workflow."""
        # 1. Add sample task cards to database
        for i, card in enumerate(self.test_tasks):
            success = self.task_service.add_document(
                document_id=f"task_{i}",
                title=card["title"],
                metadata={"category": card["category"]}
            )
            assert success, f"Failed to add task card {i}: {card['title']}"
        
        # 2. Process document for task matching
        test_cases = self.sample_docs.DOCUMENT_MATCHING_CASES
        
        for case in test_cases[:2]:  # Test first 2 cases
            with patch.object(self.processor, '_get_user_selection') as mock_selection:
                # Mock user selecting first recommendation
                mock_selection.return_value = (SelectionResult.SELECTED, case["expected_task_card"])
                
                result = self.processor.process_task_card_matching(
                    title=case["document_title"]
                )
                
                assert result is not None
                assert result == case["expected_task_card"]
    
    @patch('ui.console_interface.activate_cmd_window')
    @patch('ui.console_interface.clear_screen')
    @patch('builtins.input')
    def test_user_interaction_workflow(self, mock_input, mock_clear, mock_activate):
        """Test user interaction workflow with mocked input."""
        # Setup mock user responses
        mock_input.side_effect = ["1", "2"]  # Select first approval, second share
        
        console = ConsoleInterface()
        
        approval_list = ["담당자1", "담당자2"]
        share_list = ["팀1", "팀2", "팀3"]
        
        approval, share = console.select_approval_and_share(approval_list, share_list)
        
        assert approval == "담당자1"
        assert share == "팀2"
        assert mock_clear.called
        assert mock_activate.called
    
    def test_similarity_search_accuracy(self):
        """Test accuracy of similarity search for document matching."""
        # Add test documents with known relationships
        related_documents = [
            ("2024년 예산 계획안", "예산관리 업무"),
            ("신입사원 채용 프로세스", "인사관리 업무"),
            ("사무실 시설 개선 방안", "시설관리 업무")
        ]
        
        # Add documents to task service
        for i, (doc_title, task_title) in enumerate(related_documents):
            self.task_service.add_document(
                document_id=f"related_{i}",
                title=task_title,
                metadata={"type": "task_card"}
            )
        
        # Test similarity search
        for doc_title, expected_task in related_documents:
            results = self.task_service.query_similar_documents(
                query=doc_title,
                limit=3
            )
            
            assert len(results) > 0, f"No results for query: {doc_title}"
            
            # Check if expected task is in top results
            result_titles = [r.get("title", "") for r in results]
            assert expected_task in result_titles, f"Expected {expected_task} not found in {result_titles}"
    
    def test_empty_database_handling(self):
        """Test handling of operations on empty databases."""
        # Query empty database
        results = self.task_service.query_similar_documents("임의의 쿼리", limit=5)
        assert results == []
        
        # Process document with empty database
        result = self.processor.process_task_document(
            title="새로운 문서",
            task_cards=[]
        )
        # Should handle gracefully, might return None or empty result
        assert result is None or isinstance(result, str)


@pytest.mark.integration
class TestPerformanceWorkflow:
    """Test performance aspects of document processing workflows."""
    
    @pytest.fixture(autouse=True)
    def setup_performance_test(self):
        """Set up performance test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="perf_test_")
        
        self.service = ChromaService(
            ollama_base_url=config.ollama_base_url,
            ollama_model=config.ollama_model,
            chroma_persist_dir=self.temp_dir,
            collection_name="perf_test"
        )
        
        yield
        
        # Cleanup
        try:
            del self.service
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass
    
    @pytest.mark.slow
    def test_bulk_document_processing_performance(self):
        """Test performance with bulk document processing."""
        # Generate test documents
        test_documents = []
        base_titles = [doc["title"] for doc in SampleDocuments.RECEPTION_DOCUMENTS]
        
        # Create variations
        for base_title in base_titles:
            for i in range(10):  # 10 variations per base document
                variant_title = f"{base_title} - 변형 {i+1}"
                test_documents.append({
                    "id": f"bulk_{len(test_documents)}",
                    "title": variant_title,
                    "metadata": {"variant": i+1}
                })
        
        # Measure bulk insertion performance
        start_time = time.time()
        
        success_count = 0
        for doc in test_documents:
            if self.service.add_document(
                document_id=doc["id"],
                title=doc["title"],
                metadata=doc["metadata"]
            ):
                success_count += 1
        
        insertion_time = time.time() - start_time
        
        # Performance assertions
        assert success_count == len(test_documents), f"Only {success_count}/{len(test_documents)} documents added"
        assert insertion_time < 60.0, f"Bulk insertion took too long: {insertion_time:.2f}s"
        
        # Measure query performance
        start_time = time.time()
        
        for i in range(20):  # 20 queries
            results = self.service.query_similar_documents(
                query=f"테스트 쿼리 {i+1}",
                limit=5
            )
            assert isinstance(results, list)
        
        query_time = time.time() - start_time
        assert query_time < 30.0, f"Bulk queries took too long: {query_time:.2f}s"
        
        # Average query time should be reasonable
        avg_query_time = query_time / 20
        assert avg_query_time < 2.0, f"Average query time too high: {avg_query_time:.3f}s"
    
    def test_memory_usage_stability(self):
        """Test memory usage remains stable during extended operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform many operations
        for i in range(100):
            # Add document
            self.service.add_document(
                document_id=f"mem_test_{i}",
                title=f"메모리 테스트 문서 {i}",
                metadata={"iteration": i}
            )
            
            # Query documents
            if i % 10 == 0:  # Query every 10th iteration
                results = self.service.query_similar_documents(
                    query=f"메모리 테스트 {i}",
                    limit=3
                )
                assert isinstance(results, list)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 500MB)
        assert memory_increase < 500, f"Memory increased too much: {memory_increase:.1f}MB"


@pytest.mark.integration 
class TestErrorHandlingWorkflow:
    """Test error handling in complete workflows."""
    
    @pytest.fixture(autouse=True)
    def setup_error_test(self):
        """Set up error handling test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="error_test_")
        
        self.service = ChromaService(
            ollama_base_url=config.ollama_base_url,
            ollama_model=config.ollama_model,
            chroma_persist_dir=self.temp_dir,
            collection_name="error_test"
        )
        
        yield
        
        # Cleanup
        try:
            del self.service
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass
    
    def test_network_error_handling(self):
        """Test handling of network errors during operations."""
        with patch('langchain_ollama.OllamaEmbeddings.embed_query') as mock_embed:
            # Simulate network error
            mock_embed.side_effect = ConnectionError("Connection refused")
            
            # Should handle error gracefully
            result = self.service.add_document(
                document_id="network_error_test",
                title="네트워크 에러 테스트 문서",
                metadata={}
            )
            
            # Should return False or handle gracefully without crashing
            assert result is False or result is None
    
    def test_invalid_input_handling(self):
        """Test handling of invalid inputs."""
        # Test with None inputs
        result = self.service.add_document(
            document_id=None,
            title=None,
            metadata=None
        )
        assert result is False
        
        # Test with empty strings
        result = self.service.add_document(
            document_id="",
            title="",
            metadata={}
        )
        # Should handle gracefully
        assert isinstance(result, bool)
        
        # Test query with invalid input
        results = self.service.query_similar_documents(
            query="",
            limit=-1
        )
        assert isinstance(results, list)
    
    def test_database_corruption_recovery(self):
        """Test recovery from database corruption scenarios."""
        # Add some valid documents first
        self.service.add_document("test1", "테스트 문서 1", {})
        
        # Simulate database issues by manipulating the collection
        with patch.object(self.service.collection, 'query') as mock_query:
            mock_query.side_effect = Exception("Database corruption")
            
            # Should handle database errors gracefully
            results = self.service.query_similar_documents("테스트", limit=5)
            
            # Should return empty list or None, not crash
            assert results == [] or results is None