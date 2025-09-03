"""
에러 처리 및 로깅을 위한 유틸리티 모듈.
"""

import logging
import time
import functools
import os
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
from pathlib import Path


# Global variable to store the current execution's log file path
_current_log_file = None
_logger_initialized = False


def cleanup_old_logs(log_directory: str = "logs", keep_count: int = 5) -> None:
    """
    최근 로그 파일들만 유지하고 나머지를 삭제합니다.

    Args:
        log_directory (str): 로그 디렉토리 경로.
        keep_count (int): 유지할 로그 파일 개수.
    """
    if not os.path.exists(log_directory):
        return

    # .log 파일들을 찾아서 수정 시간으로 정렬
    log_files = []
    for filename in os.listdir(log_directory):
        if filename.endswith('.log'):
            file_path = os.path.join(log_directory, filename)
            try:
                mtime = os.path.getmtime(file_path)
                log_files.append((file_path, mtime, filename))
            except OSError:
                continue

    # 수정 시간으로 내림차순 정렬 (최신 파일이 먼저)
    log_files.sort(key=lambda x: x[1], reverse=True)

    # keep_count 개수를 초과하는 파일들을 삭제
    for file_path, _, filename in log_files[keep_count:]:
        try:
            os.remove(file_path)
            print(f"삭제된 오래된 로그 파일: {filename}")
        except OSError:
            continue


def initialize_execution_logger() -> str:
    """
    메인 실행을 위한 로그 파일을 초기화하고 오래된 로그를 정리합니다.

    Returns:
        str: 생성된 로그 파일 경로.
    """
    global _current_log_file, _logger_initialized

    if not _logger_initialized:
        # 오래된 로그 파일 정리
        cleanup_old_logs()

        # 현재 실행을 위한 로그 파일 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _current_log_file = f"logs/app_{timestamp}.log"

        # logs 디렉토리가 없으면 생성
        log_path = Path(_current_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        _logger_initialized = True

    return _current_log_file


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    console_output: bool = False
) -> logging.Logger:
    """
    로거를 설정합니다.

    Args:
        name (str): 로거 이름.
        level (int): 로깅 레벨.
        log_file (Optional[str]): 로그 파일 경로.
        format_string (Optional[str]): 로그 포맷 문자열.
        console_output (bool): 콘솔 출력 여부.

    Returns:
        logging.Logger: 설정된 로거.
    """
    logger = logging.getLogger(name)

    if logger.handlers:  # 이미 설정된 로거인 경우 반환
        return logger

    logger.setLevel(level)

    # 기본 포맷 설정
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    formatter = logging.Formatter(format_string)

    # 로그 파일이 지정되지 않았다면 실행별 로그 파일 사용
    if log_file is None:
        log_file = initialize_execution_logger()

    # logs 디렉토리가 없으면 생성
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 파일 핸들러 추가
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 콘솔 핸들러 추가 (선택적)
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def handle_connection_error(
    operation_name: str,
    logger: logging.Logger,
    max_attempts: int = 10,
    wait_time: int = 5
) -> Callable:
    """
    연결 에러를 처리하는 데코레이터.

    Args:
        operation_name (str): 작업 이름.
        logger (logging.Logger): 사용할 로거.
        max_attempts (int): 최대 시도 횟수.
        wait_time (int): 대기 시간(초).

    Returns:
        Callable: 데코레이터 함수.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.critical("%s 연결 실패 (최대 시도 횟수 초과): %s", operation_name, e)
                        raise

                    logger.info(
                        "%s 연결 실패. 재시도 중... (시도 %d/%d)", 
                        operation_name, attempt + 1, max_attempts
                    )
                    time.sleep(wait_time)

            return None
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    default_return: Any = None,
    logger: Optional[logging.Logger] = None,
    error_message: Optional[str] = None
) -> Any:
    """
    함수를 안전하게 실행하고 예외 발생 시 기본값을 반환합니다.

    Args:
        func (Callable): 실행할 함수.
        default_return (Any): 예외 발생 시 반환할 기본값.
        logger (Optional[logging.Logger]): 사용할 로거.
        error_message (Optional[str]): 에러 메시지.

    Returns:
        Any: 함수 실행 결과 또는 기본값.
    """
    try:
        return func()
    except Exception as e:
        if logger:
            message = error_message or f"함수 실행 중 오류 발생: {e}"
            logger.exception(message)
        return default_return
