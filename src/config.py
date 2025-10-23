"""
통합 설정 관리 모듈

환경 변수, 애플리케이션 설정, 데이터 구조를 중앙 집중식으로 관리합니다.
기존의 분산된 설정 파일들을 하나로 통합하여 단순화했습니다.
"""

import os
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

        # 필수 환경 변수 (OpenAI/Supabase)
        required_vars = ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]

        if missing_vars:
            error_msg = (
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
            logger.critical(error_msg)
            raise ValueError(error_msg)

        # OpenAI/Supabase 설정
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
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
        self.card_list_file = self.data_dir / "card_list.txt"
        self.reception_list_file = self.data_dir / "reception_list.txt"
        self.share_list_file = self.data_dir / "share_list.txt"

    def _load_base_data(self):
        """기본 데이터 로드"""
        try:
            # 각 TXT 파일에서 데이터 로드
            self.card_list = self._load_txt_file(self.card_list_file)
            self.reception_list = self._load_txt_file(self.reception_list_file)
            self.share_list = self._load_txt_file(self.share_list_file)

            logger.info("Base data loaded successfully")
            logger.info(
                f"Loaded {len(self.card_list)} cards, {len(self.reception_list)} receptions, {len(self.share_list)} share options"
            )

        except FileNotFoundError as e:
            raise FileNotFoundError(f"Base data file not found: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading base data: {e}")

    def _load_txt_file(self, file_path: Path) -> List[str]:
        """TXT 파일에서 목록 데이터 로드"""
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.read().strip().split("\n")
            # 빈 줄과 공백 제거
            return [line.strip() for line in lines if line.strip()]

    def _setup_logging_config(self):
        """로깅 관련 설정"""
        # 간소화된 로깅 설정
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        self.debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"

        # 로그 보관 정책 (간소화)
        self.log_retention_days = int(os.environ.get("LOG_RETENTION_DAYS", "7"))

    def reload_base_data(self):
        """기본 데이터 다시 로드 (런타임 중 변경 반영용)"""
        self._load_base_data()
        logger.info("Base data reloaded")

    def get_config_summary(self) -> Dict[str, Any]:
        """설정 요약 정보 반환 (디버깅용)"""
        return {
            "openai_api_key": "***" if self.openai_api_key else None,
            "supabase_url": self.supabase_url,
            "supabase_key": "***" if self.supabase_key else None,
            "project_root": str(self.project_root),
            "data_counts": {
                "cards": len(self.card_list),
                "receptions": len(self.reception_list),
                "shares": len(self.share_list),
            },
            "debug_mode": self.debug_mode,
            "log_level": self.log_level,
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
