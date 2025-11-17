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

## Session Log (2025-11-11 Rich UI Planning)
- Created SPEC-rich-ui-enhancement-1 with comprehensive 3-phase migration plan from ANSI codes to Rich library.
- Added TASK-009 (Phase 1: Core Infrastructure), TASK-010 (Phase 2: UI Components), TASK-011 (Phase 3: Advanced Features) to backlog.
- Documented detailed implementation plan in `.spec/rich-ui-enhancement/implementation-plan.md` with 705 LOC migration strategy.
- Key insight: Rich library (v14.1.0) already installed; feature flag approach enables gradual rollout with zero-risk rollback.
- Expected benefits: ~20% LOC reduction, improved CJK handling, built-in input validation, progress visualization.

## Session Log (2025-11-11 TASK-009 Completion)
- **Completed TASK-009**: Rich UI Phase 1 - Core Infrastructure
- Created `src/ui/rich_console.py` singleton wrapper with custom theme (info/success/warning/error styles)
- Added `USE_RICH_UI` config flag to `config.py` with default value `true` per spec
- Migrated 4 message functions (print_info, print_success, print_warning, print_error) and clear_screen to delegate to RichConsole
- Implemented feature flag logic: Rich mode when USE_RICH_UI=true, legacy ANSI fallback when false
- Created 13 new unit tests in `tests/unit/test_rich_console.py` covering singleton pattern, theme config, output functions, CJK handling, and configuration
- Updated 40 existing tests in `tests/unit/test_console_interface.py` to mock RichConsole instead of builtins.print
- **All 53 tests pass** - backward compatibility fully maintained
- Key learnings:
  - Singleton pattern requires test reset between test cases to avoid state pollution
  - Rich library handles CJK characters natively without manual width calculation
  - Unicode symbols (ℹ ✓ ⚠ ✗) render correctly in modern Windows Terminal
  - Feature flag pattern enables safe gradual migration with instant rollback capability

## Session Log (2025-11-11 TASK-010 Completion)
- **Completed TASK-010**: Rich UI Phase 2 - UI Components
- **REMOVED ALL LEGACY CODE** - Rich is now the ONLY implementation (no fallbacks)
- Removed USE_RICH_UI config flag - simplified to single code path
- Migrated `print_document_info` → `rich.panel.Panel` with emoji support (📄)
- Migrated `print_numbered_list` → `rich.table.Table` with clean formatting
- Added `progress_bar()` context manager using `rich.progress.Progress` with spinner, bar, and task progress
- Added `prompt_int()` and `confirm()` methods using `rich.prompt.IntPrompt` and `Confirm`
- Integrated `rich.logging.RichHandler` in `error_handler.py` with rich_tracebacks, markup, and clean formatting
- Updated console_interface.py - removed 100+ lines of manual ANSI/width-calculation code
- **All 59 tests pass** (19 Rich console + 40 console interface)
- Code reduction: ~150 lines removed from console_interface.py
- Key insights:
  - Rich handles all text wrapping and CJK width automatically
  - Panel and Table widgets eliminate need for manual box-drawing
  - RichHandler provides superior logging with syntax highlighting
  - Removing feature flags simplified codebase significantly

## Session Log (2025-11-11 TASK-011 Completion)
- **Completed TASK-011**: Rich UI Phase 3 - Advanced Features
- **THREE-PHASE RICH UI MIGRATION NOW COMPLETE** - all phases (1, 2, 3) done
- Enabled `rich.traceback.install()` globally in `main.py` with `show_locals=True` and `width=120`
- Migrated `print_final_result()` to use `rich.tree.Tree` for hierarchical status visualization:
  - Root node shows overall status with color-coded icons (✓/⚠/✗)
  - Statistics branch shows total/success/failure counts and success rate percentage
  - Dynamic styling based on success rate (green for 100%, yellow for partial, red for 0%)
  - Wrapped in styled Panel with title "🎉 처리 완료"
- Added `print_processing_summary()` method with `rich.markdown.Markdown`:
  - Renders detailed summary reports with heading hierarchy
  - Shows basic info (total/success/failure/elapsed time)
  - Calculates performance metrics (avg time, throughput, success rate)
  - Supports custom fields dynamically
  - Wrapped in Panel with title "📊 상세 리포트"
- **All 188 unit tests pass** including 5 new tests (3 Tree + 2 Markdown)
- Skipped `rich.live.Live` implementation - real-time updates not critical for current batch processing workflow
- Key insights:
  - Tree provides excellent hierarchical data visualization with minimal code
  - Markdown rendering enables rich formatted reports without manual layout
  - Rich tracebacks with show_locals greatly improves error debugging
  - Phase 3 adds ~100 lines but provides powerful visualization capabilities

## Session Log (2025-11-11 Selection Menu Rich Migration)
- **Migrated `print_selection_menu()` to Rich Panel + Table** - removed last remaining legacy ANSI code block
- Added `print_selection_menu()` method to `RichConsole` class in `src/ui/rich_console.py`:
  - Uses `rich.table.Table` with styled numbered rows (cyan bold [01], [02], etc.)
  - Uses `rich.panel.Panel` to wrap table with titled border
  - Supports `allow_skip` option for [00] skip entry with yellow styling
  - Custom `skip_text` parameter (default: "목록에 없음")
- Updated `console_interface.py:print_selection_menu()` to delegate to `_rich_console.print_selection_menu()`
- Removed 20+ lines of manual ANSI box-drawing code (replaced by 3-line delegation)
- Added 5 comprehensive tests to `test_rich_console.py`:
  - Basic menu rendering verification (3 console.print calls: newline + Panel + newline)
  - Skip option with custom text
  - Empty items list handling
  - Long item text wrapping
  - Korean/CJK text rendering
- **All 69 UI tests pass** (24 Rich Console + 40 Console Interface + 5 Selection Menu)
- Key insights:
  - Rich Panel + Table eliminates all manual width calculation and box-drawing
  - Consistent styling across all menu types (selection, recommendation, predefined list)
  - CJK character width handled automatically by Rich
  - **100% Rich UI migration complete** - no legacy ANSI code remaining in user-facing UI components

## Session Log (2025-11-13 TASK-002 Completion - Deployment Readiness)
- **Completed TASK-002**: Finalize Supabase deployment readiness
- **Created 3 new utility modules for production monitoring**:
  1. **audit_logger.py** (282 lines): JSON Lines audit logging with daily rotation
     - Tracks all CRUD, API, and SEARCH operations
     - Structured logs for compliance and security
     - Storage: ./logs/audit/audit_YYYYMMDD.jsonl
  2. **monitoring_hooks.py** (326 lines): Real-time health tracking and alerting
     - Health metrics: success rate, response time, error count, consecutive failures
     - 4 alert types: API failure, performance degradation, rate limit, DB error
     - Configurable thresholds: 5000ms performance, 10% error rate, 3 consecutive failures
  3. **quota_manager.py** (358 lines): API quota and budget management
     - Daily/monthly budget tracking with 4 status levels (OK/WARNING/CRITICAL/EXCEEDED)
     - Pre-request quota validation to prevent overruns
     - Auto-stop capability when budget exceeded
- **Integrated all systems**:
  - OpenAI embedding service: quota checks, audit logs, monitoring for all API calls
  - Supabase service: audit logs for all upserts/deletes, monitoring for DB errors
  - main.py: Initialize all systems at startup
- **Created RUNBOOK.md** (550+ lines): Complete operational guide
  - System architecture, monitoring procedures, audit logging usage
  - Quota management, troubleshooting, emergency procedures
  - Deployment checklist
- **Total changes**: 7 files, 1780+ insertions
- **Key insights**:
  - Audit logging provides complete trail of all critical operations
  - Monitoring hooks enable proactive issue detection before failures cascade
  - Quota management prevents unexpected cost overruns
  - All systems work together: audit logs show what happened, monitoring shows system health, quota prevents budget violations
  - Ready for safe production deployment with comprehensive observability

## Session Log (2025-11-14 Documentation Consolidation)
- **Migrated `/docs` folder to `.governance` structure** per SDD principles
- **Extracted performance analysis patterns** from `PHASE3_ANALYSIS.md` into `.governance/patterns.md`:
  - Added "Performance Analysis Workflow" section with baseline management strategy
  - Documented phase3_analysis.py script usage for regression detection and improvement validation
  - Integrated 40-50% throughput improvement target into governance knowledge
- **Created `.governance/operations.md`** (395 lines) consolidating all production operational knowledge from `RUNBOOK.md`:
  - System architecture and environment configuration
  - Monitoring & alerting procedures (health metrics, 4 alert types)
  - Audit logging structure and review commands
  - API quota management (budget tracking, quota status levels)
  - Common operations (startup, health checks, performance monitoring)
  - Troubleshooting guides (5 common issues with diagnosis/resolution)
  - Emergency procedures (shutdown, data recovery, contacts)
  - Deployment checklist and configuration reference
- **Deleted `/docs` folder** - all user-facing documentation now unified into AI-readable `.governance` structure
- **Key insight**: Separating "user docs" vs "AI knowledge" created duplication; SDD principles require single source of truth in `.governance`
- **Trace compliance**: All new governance files maintain `spec_id: SPEC-governance-doc-structure-1` and `task_id: TASK-001`

## Next Session Targets
1. Finish Phase 3 instrumentation work (TASK-003), focusing on payment info and circulation dialog flows.
2. Harden configuration and vector-threshold management (TASK-004) so prod deployments do not require code edits.
3. Consider pagination for Supabase list APIs (TASK-006) to avoid memory pressure at scale.
4. Stabilize DocumentProcessor UX + error handling (TASK-005).

## Session Log (2025-11-11 mypy cleanup)
- Added targeted mypy overrides so test modules keep pytest-style helpers untyped while the production packages stay strict.
- Cleaned up `RichConsole.progress_bar()` and `prompt_int()` signatures plus fixtures for card/reception data so type checking no longer needs ignores.
- Documented that `uv run mypy -p services -p dialogs -p ui -p utils -p debug -m config -m main -m delete_data` (code) and `uv run mypy tests` (test suite) must both stay green for TASK-002 compliance.

## Session Log (2025-11-12 Comprehensive Codebase Analysis)
- **Conducted full codebase audit** to identify technical debt accumulated during library migrations (Ollama→Supabase, ANSI→Rich).
- **Created SPEC-codebase-cleanup-1** with 3-phase improvement plan covering 10 distinct tasks (TASK-012 through TASK-021).
- **Key Findings**:
  - **Legacy Code**: Chroma references still present in config.py, delete_data.py despite complete Supabase migration
  - **Architecture Violations**: SupabaseService creates OpenAIEmbeddingService internally (DI pattern violation)
  - **Logging Pattern Violations**: ~20 files use f-strings in logger calls instead of %s formatting
  - **Missing Instrumentation**: 7 Supabase I/O methods lack @log_execution_time decorator
  - **Code Duplication**: 3 similar button click methods in official_service.py (~100 lines duplicate)
  - **Hard-coded Values**: Timeout values, pricing constants, UI patterns scattered throughout code
  - **Large File**: official_service.py at 1047 lines violates single responsibility principle
- **Phase 1 Tasks (Priority 1, 4 hours)**:
  - TASK-012: Remove Chroma legacy code (1h)
  - TASK-013: Fix dependency injection in SupabaseService (0.5h)
  - TASK-014: Convert f-string logging to %s format (2h)
  - TASK-015: Add performance instrumentation to 7 methods (0.5h)
- **Phase 2 Tasks (Priority 2, 11 hours)**:
  - TASK-016: Split official_service.py into 4 modular files (8h)
  - TASK-017: Unify button click logic (2h)
  - TASK-018: Centralize timeout and UI configuration (1h)
- **Phase 3 Tasks (Priority 3, 6 hours)**:
  - TASK-019: Replace broad Exception handling (3h)
  - TASK-020: Complete ANSI code removal (2h)
  - TASK-021: Complete type hint coverage (1h)
- **Expected Outcomes**:
  - 10% code reduction (~300 lines)
  - Governance compliance: 60% → 95%+
  - official_service.py: 1047 lines → <700 lines (split into 4 files)
  - Zero legacy library references
  - All I/O operations instrumented
- **Total Estimated Effort**: 21 hours (2.5 days)
- **Analysis artifacts** stored in `.spec/codebase-cleanup/spec.yaml` and `.tasks/backlog.yaml`
