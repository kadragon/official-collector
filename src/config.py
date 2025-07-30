"""환경 변수 및 설정을 관리하는 모듈."""

import os
from dotenv import load_dotenv
from utils.error_handler import setup_logger

logger = setup_logger(__name__)

def load_environment_variables():
    """
    .env 파일에서 환경 변수를 로드하고 필수 변수가 설정되었는지 확인합니다.
    """
    load_dotenv()

    required_env_vars = ["OLLAMA_BASE_URL", "OLLAMA_MODEL"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.critical(error_msg)
        raise ValueError(error_msg)

class AppConfig:
    """
    애플리케이션 설정을 담는 클래스.
    """
    def __init__(self):
        load_environment_variables()
        # Legacy OpenAI support (optional for backward compatibility)
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        # Ollama configuration
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL")
        self.ollama_model = os.environ.get("OLLAMA_MODEL")
        # Chroma configuration
        self.chroma_persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
        # Legacy configurations (optional)
        self.qdrant_url = os.environ.get("QDRANT_URL")
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# 전역 설정 객체
config = AppConfig()
