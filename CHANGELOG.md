# CHANGELOG

## Unreleased

- [done] Reuse verified task-card capture and unify confirmation body fast pass (2026-10-11) → docs/runbook.md
- [done] Split dialog discovery and text extraction from workflow orchestration (2026-10-11) → docs/architecture.md
- [fix] Bind final processing to original document, verify reception success and retain failed learning for retry (2026-10-11)
- [fix] Resolve stored reception handlers across departments; constrain manual org-chart picks only and reset per document (2026-10-08)

- [feat] Final-handler consent, DB card suggestions and client unit-card capture; verify information save/final approval before learning (2026-10-08)

- [fix] Use exact control selectors for review-path buttons and approval tab; avoid toolbar combo expansion during best-match lookup (2026-10-08)

- [fix] Submitted drafts with own review/approval role require consent; acknowledge line-save completion on retained window handles (2026-10-08)

- [fix] Stop unverified document stages before task-card/completion processing; a superior row alone does not prove completion (2026-10-08)

- [fix] Focus the owning console via win32console before timed input; retain title fallback and warn on activation failure (2026-10-08)
- [fix] Review confirmation: accept an already-visible next-document result; inspect body text and log failed observations (2026-10-07)
- [fix] Wait for next-document loading after Yes before capturing review title; retain changed-document consent guard (2026-10-07)
- [fix] Follow-up confirmation: read UIA child text without exists(); recognize screenshot's next-document prompt and Yes caption (2026-10-07)
- [fix] Review approval: confirm known prompt, verify transition and continue per-document review; native line input for Korean operator names (2026-10-07)
- [feat] Other-handler documents require review consent before approval-button click; bypass task cards and approval-line changes (2026-10-07)
- [fix] Approval dialog: verify closure on the original HWND wrapper instead of resolving the closed window by title (2026-10-07)
- [fix] Approval role probe: use bounded WM_CLOSE instead of Escape; retain abort when dialog stays visible (2026-10-07)
- [done] Approval decision memory: wire local reuse in both backends, org-chart reception fallback, 60s capture and failure-safe learning (2026-10-07)

- [done] Approval decision memory foundations: ordered local store, atomic vector updates, KNN reuse, org-chart readers and homonym rejection (2026-10-07)

- [done] Now sprint: stage splitter, polling-except narrowing, env centralization, wait helpers, local threshold 0.5 (2026-10-07) → docs/runbook.md
- [analysis] Document 3-stage routing (reception / assigned-to-me / post-approval) + backlog items for classify_stage() split (2026-10-07) → docs/design/document-stages.md
- [done] Verify stage-2 live signals: List1 [직위, 직급, 결재방법, 결재자] rows 접수+업무담당자, 과제카드ComboBox empty in 결재정보 (2026-10-07) → docs/design/document-stages.md

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
