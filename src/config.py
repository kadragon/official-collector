"""
통합 설정 관리 모듈

환경 변수, 애플리케이션 설정, 데이터 구조를 중앙 집중식으로 관리합니다.
기존의 분산된 설정 파일들을 하나로 통합하여 단순화했습니다.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
from utils.error_handler import setup_logger

logger = setup_logger(__name__)


class UnifiedConfig:
    """
    통합된 애플리케이션 설정 클래스
    
    환경 변수, 기본 데이터, 경로 설정 등을 중앙 집중식으로 관리합니다.
    """
    
    def __init__(self):
        """설정 초기화 및 환경 변수 로드"""
        self._load_environment()
        self._setup_paths()
        self._load_base_data()
        self._setup_logging_config()
    
    def _load_environment(self):
        """환경 변수 로드 및 검증"""
        load_dotenv()
        
        # 필수 환경 변수
        required_vars = ["OLLAMA_BASE_URL", "OLLAMA_MODEL"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.critical(error_msg)
            raise ValueError(error_msg)
        
        # Ollama 설정
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL")
        self.ollama_model = os.environ.get("OLLAMA_MODEL")
        
        # Chroma 설정
        self.chroma_persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
        
        # 선택적 설정들 (기존 호환성)
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.qdrant_url = os.environ.get("QDRANT_URL")
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        self.supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    def _setup_paths(self):
        """경로 설정"""
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        self.cache_dir = self.project_root / ".cache"
        
        # 필요한 디렉토리 생성
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 주요 파일 경로
        self.base_data_file = self.data_dir / "base_data.json"
    
    def _load_base_data(self):
        """기본 데이터 로드"""
        try:
            with open(self.base_data_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # 필수 데이터 구조 검증
            required_keys = ['card_list', 'reception_list', 'share_list']
            missing_keys = [key for key in required_keys if key not in data]
            
            if missing_keys:
                raise ValueError(f"Missing required data keys: {', '.join(missing_keys)}")
            
            # 데이터 할당
            self.card_list: List[str] = data['card_list']
            self.reception_list: List[str] = data['reception_list']  
            self.share_list: List[str] = data['share_list']
            
            logger.info("Base data loaded successfully")
            logger.info(f"Loaded {len(self.card_list)} cards, {len(self.reception_list)} receptions, {len(self.share_list)} share options")
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Base data file not found: {self.base_data_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in base data file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading base data: {e}")
    
    def _setup_logging_config(self):
        """로깅 관련 설정"""
        # 간소화된 로깅 설정
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"
        
        # 로그 보관 정책 (간소화)
        self.log_retention_days = int(os.environ.get("LOG_RETENTION_DAYS", "7"))
    
    def get_chroma_collection_name(self, collection_type: str) -> str:
        """Chroma 컬렉션 이름 생성"""
        collection_names = {
            'reception': 'reception_documents',
            'task_card': 'documents',
            'default': 'documents'
        }
        return collection_names.get(collection_type, collection_names['default'])
    
    def reload_base_data(self):
        """기본 데이터 다시 로드 (런타임 중 변경 반영용)"""
        self._load_base_data()
        logger.info("Base data reloaded")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """설정 요약 정보 반환 (디버깅용)"""
        return {
            'ollama_base_url': self.ollama_base_url,
            'ollama_model': self.ollama_model,
            'chroma_persist_dir': self.chroma_persist_dir,
            'project_root': str(self.project_root),
            'data_counts': {
                'cards': len(self.card_list),
                'receptions': len(self.reception_list),
                'shares': len(self.share_list)
            },
            'debug_mode': self.debug_mode,
            'log_level': self.log_level
        }


# 전역 설정 객체 (싱글톤 패턴)
config = UnifiedConfig()


# 편의 함수들 (기존 호환성)
def get_config() -> UnifiedConfig:
    """설정 객체 반환"""
    return config


def reload_config():
    """설정 다시 로드"""
    global config
    config.reload_base_data()


# 백워드 호환성을 위한 별칭들
load_environment_variables = lambda: config._load_environment()  # 기존 함수와의 호환성
