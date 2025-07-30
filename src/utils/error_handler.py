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


def cleanup_old_logs(log_directory: str = "logs", days_to_keep: int = 7) -> None:
    """
    지정된 일수보다 오래된 로그 파일들을 삭제합니다.

    Args:
        log_directory (str): 로그 디렉토리 경로.
        days_to_keep (int): 보관할 일수.
    """
    if not os.path.exists(log_directory):
        return

    cutoff_time = datetime.now() - timedelta(days=days_to_keep)

    for filename in os.listdir(log_directory):
        if filename.endswith('.log'):
            file_path = os.path.join(log_directory, filename)
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
                    print(f"삭제된 오래된 로그 파일: {filename}")
            except (OSError, ValueError):
                # 파일 접근 오류나 시간 변환 오류는 무시
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


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    지수 백오프와 함께 재시도를 수행하는 데코레이터.

    Args:
        max_attempts (int): 최대 시도 횟수.
        initial_delay (float): 초기 지연 시간(초).
        backoff_factor (float): 백오프 배수.
        exceptions (tuple): 재시도할 예외 타입들.

    Returns:
        Callable: 데코레이터 함수.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(func.__module__)
            delay = initial_delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.error("함수 %s 실행 실패 (최대 시도 횟수 초과): %s", func.__name__, e)
                        raise

                    logger.warning(
                        "함수 %s 실행 실패 (시도 %d/%d): %s", 
                        func.__name__, attempt + 1, max_attempts, e
                    )
                    logger.info("%s초 후 재시도...", delay)
                    time.sleep(delay)
                    delay *= backoff_factor

            return None
        return wrapper
    return decorator


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


def log_execution_time(logger: Optional[logging.Logger] = None) -> Callable:
    """
    함수 실행 시간을 로깅하는 데코레이터.

    Args:
        logger (Optional[logging.Logger]): 사용할 로거.

    Returns:
        Callable: 데코레이터 함수.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info("함수 %s 실행 완료 (소요시간: %.2f초)", func.__name__, execution_time)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error("함수 %s 실행 실패 (소요시간: %.2f초): %s", func.__name__, execution_time, e)
                raise
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


def validate_required_params(**required_params) -> None:
    """
    필수 매개변수들이 제공되었는지 검증합니다.

    Args:
        **required_params: 검증할 매개변수들.

    Raises:
        ValueError: 필수 매개변수가 누락된 경우.
    """
    missing_params = [param for param, value in required_params.items() if value is None]
    if missing_params:
        raise ValueError(f"필수 매개변수가 누락되었습니다: {', '.join(missing_params)}")


def create_error_context(operation: str, **context) -> dict:
    """
    에러 컨텍스트 정보를 생성합니다.

    Args:
        operation (str): 작업 이름.
        **context: 컨텍스트 정보.

    Returns:
        dict: 에러 컨텍스트.
    """
    return {
        'operation': operation,
        'timestamp': time.time(),
        **context
    }


def log_and_reraise(
    exception: Exception,
    logger: logging.Logger,
    context: Optional[dict] = None,
    level: int = logging.ERROR
) -> None:
    """
    예외를 로깅하고 다시 발생시킵니다.

    Args:
        exception (Exception): 발생한 예외.
        logger (logging.Logger): 사용할 로거.
        context (Optional[dict]): 추가 컨텍스트 정보.
        level (int): 로깅 레벨.

    Raises:
        Exception: 입력받은 예외를 다시 발생.
    """
    message = f"예외 발생: {str(exception)}"
    if context:
        message += f" (컨텍스트: {context})"

    logger.log(level, message, exc_info=True)
    raise exception
