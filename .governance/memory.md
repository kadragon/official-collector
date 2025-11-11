<!-- Trace:
spec_id: SPEC-governance-doc-structure-1
task_id: TASK-001
-->
# Persistent Memory

## System Snapshot
- Supabase + OpenAI embeddings fully replace the legacy Ollama/Chroma stack; three core tables (`reception_documents`, `task_cards`, `document_embeddings`) are live with HNSW indexes and RLS.
- DocumentProcessor orchestrates both reception and task-card flows, delegating similarity search to `SupabaseService` and falling back to CLI prompts when confidence drops.
- PerformanceLogger decorators wrap OpenAI calls, Supabase queries, RPA approval flows, and batch flushes, yielding ~40-50% faster throughput.

## Latest Session (2025-11-11)
- Migrated every legacy Markdown file into the `.spec/`, `.tasks/`, and `.governance/` structure with explicit Trace metadata.
- Seeded specs for core automation, Supabase migration, performance observability, and governance scaffolding.
- Captured backlog/current/done states plus coding-style, patterns, and environment references.

## Session Log (2025-11-11 Bandit hotfix)
- Completed TASK-007 (SPEC-core-automation-1) to make `clear_screen()` Bandit-compliant by invoking `cmd /c cls` or `clear` without `shell=True` while retaining the newline fallback.
- Updated `tests/unit/test_console_interface.py` so Windows/Unix expectations assert the safer subprocess arguments, then ran `pytest tests/unit/test_console_interface.py -k clear_screen`.
- Next session should resume TASK-002 (Supabase deployment readiness) from the backlog now that the hotfix is merged.
- Completed TASK-008 (SPEC-core-automation-1) by adding debug logging to `debug_manager.py`, `official_service.py`, and the console activation helper so no try/except blocks silently swallow errors; Bandit now only reports unrelated B404/B603/B607/B101 warnings.

## Risks & Constraints
- Configuration validation still references Ollama; Supabase credential checks plus similarity thresholds (0.3) must move into `config.py`.
- Supabase list APIs lack pagination, risking memory pressure once record counts grow beyond current 161 documents.
- Manual CLI selections can hang indefinitely; need timeout plus better exception handling instead of bare `assert` statements.
- Remaining instrumentation gaps: payment info window detection and circulation-dialog handling inside `official_service.py`.

## Next Session Targets
1. Promote Phase 6 deployment-readiness tasks (monitoring, auditing, cost tracking) from backlog.
2. Finish Phase 3 instrumentation work, focusing on payment info and circulation dialog flows.
3. Harden configuration and vector-threshold management so prod deployments do not require code edits.
