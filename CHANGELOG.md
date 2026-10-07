# CHANGELOG

## Unreleased

- [done] Org-chart approval line builder with predetermined order (ApprovalLineHandler + OfficialCollector.set_approval_line) (2026-10-07)
- [done] Offline vector backend FastEmbed + sqlite-vec behind VECTOR_BACKEND (2026-10-07) → docs/architecture.md
- [done] Remove dead langchain/chroma/ollama references, regen lockfile (2026-10-07)
- [done] Stabilize DocumentProcessor UX with bounded retries and dedup (2025-11-13)
- [done] Harden config validation, vector thresholds, destructive-op gating (2025-11-13) → docs/runbook.md
- [done] Complete Phase 3 instrumentation and log analysis script (2025-11-13)
- [done] Finalize Supabase deployment readiness with audit/monitor/quota (2025-11-13) → docs/runbook.md
- [done] Complete type hint coverage on UI modules (2025-11-13)
- [done] Complete ANSI removal, Rich-only deletion UI (2025-11-13)
- [done] Split official_service.py into 4 modular files (2025-11-13) → docs/architecture.md
- [done] Centralize timeout and UI configuration in config.py (2025-11-13)
- [done] Unify button click logic and centralize UI patterns (2025-11-13)
- [done] Instrument 7 Supabase I/O methods with @log_execution_time (2025-11-13)
- [done] Convert f-string logger calls to lazy %s format (2025-11-13) → docs/conventions.md
- [done] Inject embedding service into SupabaseService via constructor (2025-11-13) → docs/architecture.md
- [done] Remove Chroma legacy code after Supabase migration (2025-11-13)
- [done] Rich UI Phase 3: Tree status, Markdown reports, tracebacks (2025-11-11)
- [done] Rich UI Phase 2: Panel/Table/Progress/Prompt migration (2025-11-11)
- [done] Rich UI Phase 1: RichConsole singleton and theme (2025-11-11)
- [done] Harden exception handling flagged by Bandit B110/B112 (2025-11-11)
- [done] Fix Bandit B602 on console clear logic without shell=True (2025-11-11)
- [done] Performance logging rollout Phases 1-2, 40-50% throughput gain (2025-10-17)
- [done] Supabase and OpenAI migration Phases 1-3, 161 docs (2025-10-23) → docs/architecture.md
- [done] Paginate Supabase list APIs with iter_all generators batch 500 (2026-04-26)
- [done] Bootstrap SDD/TDD governance scaffolding (2025-11-11)
