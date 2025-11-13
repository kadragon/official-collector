<!-- Trace:
spec_id: SPEC-governance-doc-structure-1
task_id: TASK-001
-->
# Reusable Patterns

## Vector Similarity Workflow
- Normalize document metadata and embeddings before inserts to guarantee deterministic Supabase matches.
- Deduplicate query results in SQL using CTEs when possible; service-side deduplication is a fallback only.

## Batch Update Flush
- Accumulate Supabase mutations in memory during RPA flows, then call `flush_pending_updates()` once per batch to reduce latency and contention.
- Protect the flush with retries and transactional semantics once Supabase introduces them.

## Performance Instrumentation
- Wrap every I/O heavy function with `@log_execution_time` (APIs) or `tracked_timer` (context managers) so waits are observable.
- Store per-phase baselines (Phase 1..7) to compare improvements and regressions after each deployment.

## RPA Guard Rails
- Always verify target windows via helper functions (`_ensure_payment_info_window`) before interacting; log failures with actionable detail for debugging.
- Provide interactive CLI fallbacks with explicit timeout/backoff so automation does not hang on manual prompts.

## Exception Handling Patterns
- **Use specific exception types** instead of broad `except Exception` to improve debugging and error handling granularity.
- **Apply decorators for common patterns** to reduce boilerplate and ensure consistent error logging across the codebase.

### Available Decorators

#### @handle_supabase_error
Use for Supabase/database operations. Handles common database errors with specific error messages:
- `ConnectionError/TimeoutError`: Network connectivity issues
- `ValueError`: Invalid data or parameters
- `KeyError`: Missing required fields in response
- `AttributeError`: Attribute access errors
- `Exception`: Catch-all with full traceback logging

**Example:**
```python
@handle_supabase_error("접수 문서 제목 조회", logger, default_return=(None, None))
def retrieve_reception_by_title(self, title: str) -> Tuple[Optional[str], Optional[str]]:
    result = self.client.table("reception_mappings").select(...).eq("title", title).execute()
    if result.data:
        return result.data[0]["handler"], result.data[0]["share_target"]
    return None, None
```

#### @handle_pywinauto_error
Use for UI automation operations. Handles common pywinauto errors with retry logic:
- `AttributeError/RuntimeError`: UI element not found (with retry support)
- `TimeoutError`: Operation timeout
- `OSError`: System-level errors
- `Exception`: Catch-all with full traceback logging

**Parameters:**
- `max_retries`: Number of retry attempts for transient errors (default: 0)
- `retry_delay`: Delay between retries in seconds (default: 0.5)

**Example:**
```python
@handle_pywinauto_error("창 연결", logger, default_return=None, max_retries=3, retry_delay=0.5)
def connect_to_window(self, title_pattern: str) -> Any:
    return self.app.connect(title_re=title_pattern).top_window()
```

### Migration Strategy
This is an **incremental improvement task**. Focus on:
1. High-traffic code paths first (e.g., `SupabaseService` methods)
2. Methods with repetitive exception handling patterns
3. Critical paths where specific error types provide better debugging

### Benefits
- **Better diagnostics**: Specific exception types reveal root cause immediately
- **Reduced boilerplate**: Decorators eliminate repetitive try-except blocks
- **Consistent logging**: Standardized error messages and traceback handling
- **Retry logic**: Built-in retry support for transient failures
- **Maintainability**: Centralized exception handling logic in `utils/error_handler.py`

### Common Exception Types by Layer
- **Supabase/Database**: `ConnectionError`, `TimeoutError`, `ValueError`, `KeyError`
- **pywinauto/UI**: `AttributeError`, `RuntimeError`, `TimeoutError`, `OSError`
- **Application**: `ValueError`, `TypeError`, `KeyError`, `AttributeError`
