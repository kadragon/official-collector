"""
Mock responses and service fixtures for testing

This module provides mocked responses for external services
to enable fast, isolated unit testing without dependencies.
"""

from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock


class MockOllamaService:
    """Mocked Ollama service for testing."""
    
    @staticmethod
    def mock_embedding_response(text: str) -> List[float]:
        """Generate a fake embedding based on text content."""
        # Simple hash-based fake embedding (consistent for same input)
        base_embedding = [0.1] * 768
        text_hash = hash(text) % 1000
        
        # Modify embedding based on text hash to make it deterministic
        for i in range(min(len(base_embedding), 10)):
            base_embedding[i] = (text_hash + i) / 1000.0
            
        return base_embedding
    
    @staticmethod
    def create_mock_ollama_embeddings():
        """Create a mock OllamaEmbeddings instance."""
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.side_effect = MockOllamaService.mock_embedding_response
        mock_embeddings.embed_documents.side_effect = lambda texts: [
            MockOllamaService.mock_embedding_response(text) for text in texts
        ]
        return mock_embeddings


class MockChromaService:
    """Mocked ChromaService for testing."""
    
    def __init__(self):
        self.stored_documents = {}  # id -> document mapping
        self.stored_embeddings = {}  # id -> embedding mapping
        self.call_count = {"add": 0, "query": 0, "delete": 0}
    
    def mock_add_document(self, document_id: str, title: str, metadata: Dict = None):
        """Mock document addition."""
        self.call_count["add"] += 1
        self.stored_documents[document_id] = {
            "title": title,
            "metadata": metadata or {}
        }
        self.stored_embeddings[document_id] = MockOllamaService.mock_embedding_response(title)
        return True
    
    def mock_query_similar(self, query: str, limit: int = 5) -> List[Dict]:
        """Mock similarity search."""
        self.call_count["query"] += 1
        
        # Simple text-based similarity (for testing)
        results = []
        query_lower = query.lower()
        
        for doc_id, doc_data in self.stored_documents.items():
            title = doc_data["title"].lower()
            # Simple similarity score based on common words
            common_words = len(set(query_lower.split()) & set(title.split()))
            similarity_score = common_words / max(len(query_lower.split()), 1)
            
            if similarity_score > 0:
                results.append({
                    "id": doc_id,
                    "title": doc_data["title"],
                    "metadata": doc_data["metadata"],
                    "similarity_score": similarity_score
                })
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:limit]
    
    def mock_delete_document(self, document_id: str) -> bool:
        """Mock document deletion."""
        self.call_count["delete"] += 1
        if document_id in self.stored_documents:
            del self.stored_documents[document_id]
            del self.stored_embeddings[document_id]
            return True
        return False
    
    def get_stats(self) -> Dict:
        """Get mock service statistics."""
        return {
            "document_count": len(self.stored_documents),
            "calls": self.call_count.copy()
        }


class MockUserInterface:
    """Mocked user interface responses for testing."""
    
    def __init__(self):
        self.responses = []  # Queue of responses to return
        self.interactions = []  # Log of interactions
    
    def set_responses(self, responses: List[Any]):
        """Set predefined responses for user interactions."""
        self.responses = responses.copy()
    
    def mock_user_choice(self, options: List[str], allow_skip: bool = False):
        """Mock user selection from options."""
        interaction = {
            "type": "choice",
            "options": options,
            "allow_skip": allow_skip
        }
        self.interactions.append(interaction)
        
        if self.responses:
            response = self.responses.pop(0)
            if isinstance(response, int):
                # Return selection result
                from ui.console_interface import SelectionResult
                if 0 <= response < len(options):
                    return SelectionResult.SELECTED, options[response]
                elif response == -1 and allow_skip:
                    return SelectionResult.SKIPPED, None
            return response
        
        # Default: select first option
        from ui.console_interface import SelectionResult
        return SelectionResult.SELECTED, options[0] if options else (SelectionResult.SKIPPED, None)
    
    def mock_confirmation(self, message: str, default_yes: bool = True) -> bool:
        """Mock user confirmation."""
        interaction = {
            "type": "confirmation",
            "message": message,
            "default_yes": default_yes
        }
        self.interactions.append(interaction)
        
        if self.responses:
            response = self.responses.pop(0)
            return bool(response)
        
        return default_yes  # Default response


class MockFileSystem:
    """Mocked file system operations for testing."""
    
    def __init__(self):
        self.files = {}  # path -> content mapping
        self.directories = set()
        
    def create_file(self, path: str, content: str = ""):
        """Create a mock file."""
        self.files[path] = content
        
    def create_directory(self, path: str):
        """Create a mock directory."""
        self.directories.add(path)
        
    def file_exists(self, path: str) -> bool:
        """Check if mock file exists."""
        return path in self.files
        
    def directory_exists(self, path: str) -> bool:
        """Check if mock directory exists."""
        return path in self.directories
        
    def read_file(self, path: str) -> Optional[str]:
        """Read mock file content."""
        return self.files.get(path)


class MockEnvironment:
    """Mocked environment variables for testing."""
    
    def __init__(self):
        self.variables = {
            "OLLAMA_BASE_URL": "http://localhost:11434",
            "OLLAMA_MODEL": "snowflake-arctic-embed",
            "CHROMA_PERSIST_DIR": "./test_chroma_db",
        }
    
    def set_variable(self, key: str, value: str):
        """Set environment variable."""
        self.variables[key] = value
        
    def get_variable(self, key: str, default: str = None) -> Optional[str]:
        """Get environment variable."""
        return self.variables.get(key, default)
        
    def unset_variable(self, key: str):
        """Unset environment variable."""
        self.variables.pop(key, None)