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
