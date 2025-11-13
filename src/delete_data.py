#!/usr/bin/env python3
"""
Supabase에 저장된 분류된 문서와 과제카드 데이터를 삭제하는 독립 실행 스크립트
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
from ui.rich_console import RichConsole
from utils.error_handler import setup_logger


def main() -> None:
    """메인 실행 함수"""
    # 환경 변수 로드
    load_dotenv()

    console = RichConsole()

    try:
        logger = setup_logger(__name__)
        logger.info("Supabase 데이터 삭제 도구 시작")

        console.clear()
        console.print_header("Supabase 데이터 삭제 도구")
        console.print_info(
            "이 도구를 사용하여 분류된 문서와 과제카드 데이터를 삭제할 수 있습니다."
        )
        console.print("")

        # 통합된 삭제 인터페이스 실행
        run_deletion_interface()

    except KeyboardInterrupt:
        console.print_success("\n작업이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        console.print_error(f"예기치 않은 오류가 발생했습니다: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
