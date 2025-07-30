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

    required_env_vars = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
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
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# 전역 설정 객체
config = AppConfig()
