# Approval Decision Memory (local reuse for handlers and approval lines)

## Problem Statement
Reception (접수) handler choices and assigned-document (배정) approval lines are re-decided every run. Title-based vector queries exist for handlers (`DocumentProcessor.process_reception_document`) and task cards (`process_task_card_matching`), but there is no ordered approval-line store, no confirm-vs-auto rule in one place, no org-chart department fallback for reception, and no dialog-capture save for manually built approval lines. Operators repeat the same selections.

## Solution
Unify both flows as query → confirm → fallback → save → reuse, backed by local SQLite only. Reception keeps using `reception_mappings`; assigned approval lines gain a new local-only `approval_lines` store (ordered JSON + embedding). Supabase paths stay legacy (no new Supabase table). Fallbacks use the org chart (reception, config department) and the 결재정보>결재선 dialog with Enter-wait capture (assigned).

## User Stories
- As an operator processing a 접수 document, I want the title query to auto-proceed on high similarity or ask for confirmation otherwise, so that repeat titles skip manual picks.
- As an operator with no stored handler or no designated list, I want the org-chart members of my configured department listed for selection, so that I can pick without guessing names.
- As an operator processing an assigned (배정) document, I want the stored approval line suggested and auto-applied on high similarity or confirmed otherwise, so that repeat titles reuse the line.
- As an operator with no stored approval line, I want the 결재정보>결재선 dialog opened with an Enter-wait prompt and the finished line auto-read and saved, so that the next identical title reuses it.

## Implementation Decisions
- Auto-proceed threshold is 0.85 (`AUTO_SELECTION_SIMILARITY_THRESHOLD` in `document_processor.py`), keeping existing behavior; `VectorConfig` 0.3 stays as candidate-filter only. Source: grill Q1.
- New local-only `approval_lines(title PK, approvers JSON ordered, embedding BLOB, timestamps)` plus `vec_approval_lines` in `LocalVectorService`, mirroring `reception_mappings`/`task_card_mappings` DDL, dimension check, and upsert/KNN patterns. No Supabase DDL change; `SupabaseService` approval-line methods are legacy no-ops (log + None). Source: grill Q2.
- Storage backend is local SQLite regardless of `VECTOR_BACKEND` (Supabase mode also reads/writes the local file for approval lines). Source: grill Q5-equivalent (local-only answer).
- Reception fallback department comes from config (`MY_DEPARTMENT` in `config.py`/`base_data.json`, new `UnifiedConfig` property); when empty, fall back to manual department pick. Uses `ApprovalLineHandler` org-chart read path plus a new department-member listing reader. Source: grill Q3.
- Assigned fallback opens the dialog via `ApprovalLineHandler.connect_approval_window`, prompts Enter with an explicit Rich timeout (never hangs), then reads back `List1` via `read_approver_names` and upserts to local `approval_lines`. Source: grill Q4.
- Scope covers stage-2 (approval line) and stage-3 (task-card) reuse paths; `classify_stage()` splitter and stage-3 completion-marker finalization stay with the existing backlog items and are not redefined here. Source: grill Q6 (stage-2+3 포함, markers TBD per `docs/design/document-stages.md`).

## Testing Decisions
- Unit tests first for new store and matching logic (local tmp DB, JSON order preserved, KNN reuse, dedup/upsert, Supabase legacy no-op), run with `pytest tests/unit/ -v`.
- Lint/type gates: `uv run pylint src/` green (lazy `%s` logging, no bare except, no new `time.sleep`), `mypy` per `docs/runbook.md`.
- Manual verification only with a live client for the two RPA paths (org-chart listing, Enter-wait capture); no production-code change for stage markers without a live dump.

## Out of Scope
- Supabase `approval_lines` table, RPC functions, or 1536-dim vector transfer (reindex required, per architecture gotchas).
- `classify_stage()` implementation, stage-3 completion-marker strings, per-row approval-state and task-card field RPA readers (covered by backlog Now/Next items, need live dumps).
- Task-card selection RPA speedup (`_perform_task_card_selection` coords/sleeps) and confirm-dialog fast-pass unification.
- Chroma/Ollama revival, pricing/threshold hard-coding outside `config.py`, new public API beyond the store methods.

## Not yet specified
- `MY_DEPARTMENT` default when unconfigured — candidate: empty means manual pick every time.
- Enter-wait timeout value — candidate: reuse `TimeoutConfig.APPROVAL_LINE_WAIT` family with an explicit long bound.
- Cross-department homonym display in the department listing — candidate: `name + node-text` disambiguation per `match_node_text` behavior.

## Further Notes
- Risk: local DB file is dimension-pinned (384 vs 1536); new vec table must join the existing dimension check and reindex hint.
- Follow-up: centralize the 0.85 constant into `config.py` (`VectorConfig`) on touch, per the config-only golden principle.
- Backlog sync: this spec does not close the `classify_stage()` or stage-3 dump items; tickets must reference them as blocked-by rather than duplicate.
