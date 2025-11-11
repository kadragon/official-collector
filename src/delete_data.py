#!/usr/bin/env python3
"""
Chroma에 저장된 분류된 문서와 과제카드 데이터를 삭제하는 독립 실행 스크립트
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리를 Python path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import from main module now that deletion is integrated
from main import run_deletion_interface
from ui.console_interface import clear_screen, print_success, print_error
from utils.error_handler import setup_logger


def main() -> None:
    """메인 실행 함수"""
    # 환경 변수 로드
    load_dotenv()

    # 필수 환경 변수 확인
    required_env_vars = ["OLLAMA_BASE_URL", "OLLAMA_MODEL"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        print_error(f"필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        print_error("'.env' 파일을 확인해주세요.")
        sys.exit(1)

    try:
        logger = setup_logger(__name__)
        logger.info("Chroma 데이터 삭제 도구 시작")

        clear_screen()
        print_success("=== Chroma 데이터 삭제 도구 ===")
        print("이 도구를 사용하여 분류된 문서와 과제카드 데이터를 삭제할 수 있습니다.")
        print()

        # 통합된 삭제 인터페이스 실행
        run_deletion_interface()

    except KeyboardInterrupt:
        print_success("\n작업이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print_error(f"예기치 않은 오류가 발생했습니다: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
