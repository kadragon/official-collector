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
from rich.logging import RichHandler


# Global variable to store the current execution's log file path
_current_log_file: Optional[str] = None
_logger_initialized = False


def cleanup_old_logs(
    log_directory: str = "logs", retention_days: int = 7
) -> tuple[int, list[str]]:
    """
    오래된 로그 파일들을 삭제합니다.

    이 함수는 순수한 로직만 수행하고, UI 출력은 호출하는 쪽에서 담당합니다.
    관심사의 분리(Separation of Concerns) 원칙을 따릅니다.

    Args:
        log_directory (str): 로그 디렉토리 경로.
        retention_days (int): 보관 기간 (일).

    Returns:
        tuple[int, list[str]]: (삭제된 파일 수, 삭제된 파일명 리스트)
    """
    if not os.path.exists(log_directory):
        return 0, []

    cutoff_time = datetime.now() - timedelta(days=retention_days)
    deleted_files: list[str] = []

    for filename in os.listdir(log_directory):
        if filename.endswith(".log"):
            file_path = os.path.join(log_directory, filename)
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
                    deleted_files.append(filename)
            except (OSError, ValueError):
                continue

    return len(deleted_files), deleted_files


def initialize_execution_logger() -> str:
    """
    메인 실행을 위한 로그 파일을 초기화하고 오래된 로그를 정리합니다.

    Returns:
        str: 생성된 로그 파일 경로.
    """
    global _current_log_file, _logger_initialized

    if not _logger_initialized:
        # 오래된 로그 파일 정리
        deleted_count, deleted_files = cleanup_old_logs()

        # UI 출력 (선택적 - 삭제된 파일이 있을 때만)
        if deleted_count > 0:
            try:
                from ui.rich_console import RichConsole

                console = RichConsole()
                for filename in deleted_files:
                    console.print_info(f"오래된 로그 파일 삭제: {filename}")
                console.print_success(
                    f"총 {deleted_count}개의 오래된 로그 파일이 삭제되었습니다."
                )
            except ImportError:
                # RichConsole을 사용할 수 없는 환경에서는 무시
                pass

        # 현재 실행을 위한 로그 파일 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _current_log_file = f"logs/app_{timestamp}.log"

        # logs 디렉토리가 없으면 생성
        log_path = Path(_current_log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        _logger_initialized = True

    # Explicit error handling instead of bare assertion
    if _current_log_file is None:
        raise RuntimeError(
            "Log file initialization failed. _current_log_file is None after initialization."
        )

    return _current_log_file


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    console_output: bool = True,
) -> logging.Logger:
    """
    Create (or retrieve) a configured logger instance.

    Args:
        name (str): Logger name.
        level (int): Logging level.
        log_file (Optional[str]): Explicit log file path.
        format_string (Optional[str]): Log formatting template.
        console_output (bool): Whether to attach a console handler.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    if not logger.handlers:
        if log_file is None:
            log_file = initialize_execution_logger()

        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
        except OSError as error:
            logging.getLogger(name).warning(
                "Unable to open log file %s: %s", log_file, error
            )
        else:
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    if console_output and not any(
        isinstance(handler, (logging.StreamHandler, RichHandler))
        for handler in logger.handlers
    ):
        # Use RichHandler for better console output
        console_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=False,  # Time already in format string
            show_path=False,  # Keep logs concise
        )
        console_handler.setLevel(level)
        # RichHandler has its own formatting
        logger.addHandler(console_handler)

    logger.propagate = False
    return logger


def handle_connection_error(
    operation_name: str,
    logger: logging.Logger,
    max_attempts: int = 10,
    wait_time: int = 5,
) -> Callable[[Callable], Callable]:
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
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.critical(
                            "%s 연결 실패 (최대 시도 횟수 초과): %s", operation_name, e
                        )
                        raise

                    logger.info(
                        "%s 연결 실패. 재시도 중... (시도 %d/%d)",
                        operation_name,
                        attempt + 1,
                        max_attempts,
                    )
                    time.sleep(wait_time)

            return None

        return wrapper

    return decorator


def safe_execute(
    func: Callable,
    default_return: Any = None,
    logger: Optional[logging.Logger] = None,
    error_message: Optional[str] = None,
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


def handle_supabase_error(
    operation_name: str,
    logger: logging.Logger,
    default_return: Any = None,
    raise_on_auth_error: bool = True,
    default_factory: Optional[Callable[[], Any]] = None,
) -> Callable[[Callable], Callable]:
    """
    Supabase 데이터베이스 오류를 처리하는 데코레이터.

    일반적인 Supabase/PostgreSQL 오류를 구체적으로 처리하고 로깅합니다.

    Args:
        operation_name: 작업 이름 (로깅용)
        logger: 사용할 로거
        default_return: 오류 발생 시 반환할 기본값
        raise_on_auth_error: 인증 오류 시 예외를 재발생시킬지 여부

    Returns:
        Callable: 데코레이터 함수

    Handles:
        - APIError: General Supabase API errors
        - ConnectionError/TimeoutError: Network issues
        - ValueError: Invalid data/parameters
        - KeyError: Missing required fields
        - Exception: Catch-all for unexpected errors
    """

    def _default() -> Any:
        return default_factory() if default_factory is not None else default_return

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                logger.error("%s 실패 - 네트워크 연결 오류: %s", operation_name, str(e))
                return _default()
            except ValueError as e:
                logger.error("%s 실패 - 잘못된 데이터: %s", operation_name, str(e))
                return _default()
            except KeyError as e:
                logger.error("%s 실패 - 필수 필드 누락: %s", operation_name, str(e))
                return _default()
            except AttributeError as e:
                logger.error("%s 실패 - 속성 접근 오류: %s", operation_name, str(e))
                return _default()
            except Exception as e:
                logger.exception(
                    "%s 실패 - 예상치 못한 오류: %s", operation_name, str(e)
                )
                return _default()

        return wrapper

    return decorator


def handle_pywinauto_error(
    operation_name: str,
    logger: logging.Logger,
    default_return: Any = None,
    max_retries: int = 0,
    retry_delay: float = 0.5,
) -> Callable[[Callable], Callable]:
    """
    pywinauto UI 자동화 오류를 처리하는 데코레이터.

    일반적인 pywinauto 오류를 구체적으로 처리하고 재시도 로직을 제공합니다.

    Args:
        operation_name: 작업 이름 (로깅용)
        logger: 사용할 로거
        default_return: 오류 발생 시 반환할 기본값
        max_retries: 최대 재시도 횟수
        retry_delay: 재시도 간 대기 시간 (초)

    Returns:
        Callable: 데코레이터 함수

    Handles:
        - ElementNotFoundError: UI element not found
        - TimeoutError: Operation timeout
        - RuntimeError: General runtime errors
        - OSError: System-level errors
        - Exception: Catch-all for unexpected errors
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: (
                AttributeError
                | RuntimeError
                | TimeoutError
                | OSError
                | Exception
                | None
            ) = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (
                    AttributeError,
                    RuntimeError,
                ) as e:  # ElementNotFoundError typically manifests as these
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "%s 실패 - UI 요소 미발견 (재시도 %d/%d): %s",
                            operation_name,
                            attempt + 1,
                            max_retries,
                            str(e),
                        )
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(
                            "%s 실패 - UI 요소 미발견 (최대 재시도 초과): %s",
                            operation_name,
                            str(e),
                        )
                        return default_return
                except TimeoutError as e:
                    last_exception = e
                    logger.error("%s 실패 - 작업 타임아웃: %s", operation_name, str(e))
                    return default_return
                except OSError as e:
                    last_exception = e
                    logger.error(
                        "%s 실패 - 시스템 레벨 오류: %s", operation_name, str(e)
                    )
                    return default_return
                except Exception as e:
                    last_exception = e
                    logger.exception(
                        "%s 실패 - 예상치 못한 오류: %s", operation_name, str(e)
                    )
                    return default_return

            # Should not reach here, but just in case
            if last_exception:
                logger.error(
                    "%s 실패 - 모든 재시도 실패: %s",
                    operation_name,
                    str(last_exception),
                )
            return default_return

        return wrapper

    return decorator
