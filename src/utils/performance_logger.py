import time
import functools
from typing import Callable, Any, Optional
from contextlib import contextmanager
import logging


def log_execution_time(logger: logging.Logger, operation_name: Optional[str] = None):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            func_name = operation_name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed_time = time.time() - start_time
                logger.info(f"⏱️ {func_name} 완료 (소요시간: {elapsed_time:.3f}초)")
                return result
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"⏱️ {func_name} 실패 (소요시간: {elapsed_time:.3f}초) - {e}")
                raise
        
        return wrapper
    return decorator


@contextmanager
def timer(logger: logging.Logger, operation_name: str):
    start_time = time.time()
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"⏱️ {operation_name} 완료 (소요시간: {elapsed_time:.3f}초)")


class PerformanceTracker:
    def __init__(self):
        self.metrics = {}
    
    def record(self, operation: str, duration: float):
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
    
    def get_stats(self, operation: str) -> dict:
        if operation not in self.metrics or not self.metrics[operation]:
            return {}
        
        durations = self.metrics[operation]
        return {
            'count': len(durations),
            'total': sum(durations),
            'avg': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations)
        }
    
    def get_all_stats(self) -> dict:
        return {op: self.get_stats(op) for op in self.metrics}


_global_tracker = PerformanceTracker()


def get_performance_tracker() -> PerformanceTracker:
    return _global_tracker


@contextmanager
def tracked_timer(logger: logging.Logger, operation_name: str, tracker: Optional[PerformanceTracker] = None):
    start_time = time.time()
    perf_tracker = tracker or _global_tracker
    
    try:
        yield
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"⏱️ {operation_name} 완료 (소요시간: {elapsed_time:.3f}초)")
        perf_tracker.record(operation_name, elapsed_time)
