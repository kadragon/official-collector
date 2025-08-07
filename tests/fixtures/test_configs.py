"""
Test configuration sets and utilities

This module provides different configuration sets for testing
various scenarios and edge cases.
"""

from typing import Dict, Any, List
import tempfile
import os


class TestConfigurations:
    """Pre-defined test configurations."""
    
    # 기본 테스트 설정
    DEFAULT_TEST_CONFIG = {
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "snowflake-arctic-embed", 
        "chroma_persist_dir": "./test_chroma_db",
        "reception_list": ["예산담당자", "인사담당자", "시설담당자", "교육담당자"],
        "share_list": ["기획팀", "총무팀", "관리팀", "인사팀"],
        "task_card_list": ["예산관리 업무", "인사관리 업무", "시설관리 업무", "교육기획 업무"]
    }
    
    # 최소 설정 (필수 항목만)
    MINIMAL_CONFIG = {
        "ollama_base_url": "http://localhost:11434", 
        "ollama_model": "snowflake-arctic-embed",
        "chroma_persist_dir": tempfile.mkdtemp(prefix="test_minimal_"),
        "reception_list": ["담당자1"],
        "share_list": ["팀1"], 
        "task_card_list": ["업무1"]
    }
    
    # 확장된 설정 (많은 옵션들)
    EXTENDED_CONFIG = {
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "snowflake-arctic-embed",
        "chroma_persist_dir": tempfile.mkdtemp(prefix="test_extended_"),
        "reception_list": [
            "예산담당자", "인사담당자", "시설담당자", "교육담당자", 
            "법무담당자", "기획담당자", "홍보담당자", "보안담당자"
        ],
        "share_list": [
            "기획팀", "총무팀", "관리팀", "인사팀", 
            "재무팀", "법무팀", "홍보팀", "보안팀"
        ],
        "task_card_list": [
            "예산관리 업무", "인사관리 업무", "시설관리 업무", "교육기획 업무",
            "법무검토 업무", "기획조정 업무", "홍보마케팅 업무", "정보보안 업무",
            "계약관리 업무", "감사업무", "고객서비스 업무", "품질관리 업무"
        ]
    }
    
    # 에러 케이스용 잘못된 설정
    INVALID_CONFIGS = {
        "empty_ollama_url": {
            "ollama_base_url": "",
            "ollama_model": "snowflake-arctic-embed",
            "chroma_persist_dir": "./test_chroma_db"
        },
        "invalid_ollama_url": {
            "ollama_base_url": "invalid-url",
            "ollama_model": "snowflake-arctic-embed", 
            "chroma_persist_dir": "./test_chroma_db"
        },
        "missing_model": {
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "",
            "chroma_persist_dir": "./test_chroma_db"
        },
        "invalid_chroma_dir": {
            "ollama_base_url": "http://localhost:11434",
            "ollama_model": "snowflake-arctic-embed",
            "chroma_persist_dir": "/invalid/path/that/does/not/exist"
        }
    }


class TestEnvironmentManager:
    """테스트 환경 설정 관리자."""
    
    def __init__(self, config_name: str = "default"):
        self.config_name = config_name
        self.temp_dirs = []
        self.original_env = {}
        
    def setup_environment(self) -> Dict[str, Any]:
        """테스트 환경을 설정합니다."""
        if self.config_name == "default":
            config = TestConfigurations.DEFAULT_TEST_CONFIG.copy()
        elif self.config_name == "minimal":
            config = TestConfigurations.MINIMAL_CONFIG.copy()
        elif self.config_name == "extended":
            config = TestConfigurations.EXTENDED_CONFIG.copy()
        else:
            raise ValueError(f"Unknown config: {self.config_name}")
        
        # 임시 디렉토리 생성 및 추적
        if not os.path.exists(config["chroma_persist_dir"]):
            temp_dir = tempfile.mkdtemp(prefix=f"test_{self.config_name}_")
            config["chroma_persist_dir"] = temp_dir
            self.temp_dirs.append(temp_dir)
            
        # 환경 변수 백업 및 설정
        env_vars = {
            "OLLAMA_BASE_URL": config["ollama_base_url"],
            "OLLAMA_MODEL": config["ollama_model"], 
            "CHROMA_PERSIST_DIR": config["chroma_persist_dir"]
        }
        
        for key, value in env_vars.items():
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = value
            
        return config
        
    def teardown_environment(self):
        """테스트 환경을 정리합니다."""
        # 환경 변수 복원
        for key, original_value in self.original_env.items():
            if original_value is not None:
                os.environ[key] = original_value
            elif key in os.environ:
                del os.environ[key]
                
        # 임시 디렉토리 정리
        import shutil
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass  # 정리 실패는 무시
                    
        self.temp_dirs.clear()
        self.original_env.clear()


class PerformanceTestConfig:
    """성능 테스트용 설정."""
    
    # 성능 테스트 시나리오별 설정
    SCENARIOS = {
        "small": {
            "document_count": 10,
            "task_card_count": 5,
            "query_count": 20,
            "expected_max_time": 5.0  # seconds
        },
        "medium": {
            "document_count": 100,
            "task_card_count": 20,
            "query_count": 100, 
            "expected_max_time": 30.0
        },
        "large": {
            "document_count": 1000,
            "task_card_count": 100,
            "query_count": 500,
            "expected_max_time": 120.0
        }
    }
    
    @staticmethod
    def get_scenario_config(scenario: str) -> Dict[str, Any]:
        """성능 테스트 시나리오 설정을 반환합니다."""
        if scenario not in PerformanceTestConfig.SCENARIOS:
            raise ValueError(f"Unknown performance scenario: {scenario}")
        return PerformanceTestConfig.SCENARIOS[scenario].copy()


class ErrorTestCases:
    """에러 테스트 케이스 모음."""
    
    # 네트워크 에러 시뮬레이션
    NETWORK_ERRORS = [
        {"error_type": "ConnectionError", "message": "Connection refused"},
        {"error_type": "TimeoutError", "message": "Request timeout"},
        {"error_type": "HTTPError", "message": "HTTP 500 Internal Server Error"}
    ]
    
    # 데이터 에러 케이스
    DATA_ERRORS = [
        {"input": None, "expected_error": "NullInputError"},
        {"input": "", "expected_error": "EmptyInputError"}, 
        {"input": " " * 1000, "expected_error": "TooLongInputError"},
        {"input": "특수문자테스트!@#$%^&*()", "expected_error": None}  # Should handle gracefully
    ]
    
    # 시스템 리소스 에러
    RESOURCE_ERRORS = [
        {"error_type": "MemoryError", "scenario": "large_document_processing"},
        {"error_type": "DiskSpaceError", "scenario": "database_full"},
        {"error_type": "PermissionError", "scenario": "readonly_database"}
    ]