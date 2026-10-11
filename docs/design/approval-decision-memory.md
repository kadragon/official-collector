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
- Auto-proceed threshold is 0.85 (`VectorConfig.AUTO_SELECTION_SIMILARITY_THRESHOLD` in `config.py`), keeping existing behavior; backend thresholds remain candidate filters (Supabase 0.3, local 0.5 by default). Source: grill Q1.
- New local-only `approval_lines(title PK, approvers JSON ordered, embedding BLOB, timestamps)` plus `vec_approval_lines` in `LocalVectorService`, mirroring `reception_mappings`/`task_card_mappings` DDL, dimension check, and upsert/KNN patterns. No Supabase DDL change; `SupabaseService` approval-line methods are legacy no-ops (log + None). Source: grill Q2.
- Storage backend is local SQLite regardless of `VECTOR_BACKEND` (Supabase mode also reads/writes the local file for approval lines). Source: grill Q5-equivalent (local-only answer).
- Reception fallback department comes from config (`MY_DEPARTMENT` in `config.py`/`base_data.json`, new `UnifiedConfig` property); when empty, fall back to manual department pick. Uses `ApprovalLineHandler` org-chart read path plus a new department-member listing reader. Source: grill Q3.
- Assigned fallback opens the dialog via `ApprovalLineHandler.connect_approval_window`, waits at most 60 seconds for Enter, reads `List1`, confirms the staged line and upserts only after confirmation succeeds. Escape, unavailable console input and timeout cancel without saving. Source: grill Q4; timeout approved 2026-10-07.
- Scope covers stage-2 (approval line) and stage-3 (task-card) reuse paths; `classify_stage()` splitter and stage-3 completion-marker finalization stay with the existing backlog items and are not redefined here. Source: grill Q6 (stage-2+3 포함, markers TBD per `docs/design/document-stages.md`).

## Testing Decisions
- Unit tests first for new store and matching logic (local tmp DB, JSON order preserved, KNN reuse, dedup/upsert, Supabase legacy no-op), run with `pytest tests/unit/ -v`.
- Lint/type gates: `uv run pylint src/` green (lazy `%s` logging, no bare except, no new `time.sleep`), `mypy` per `docs/runbook.md`.
- Manual verification only with a live client for the two RPA paths (org-chart listing, Enter-wait capture); no production-code change for stage markers without a live dump.

## Out of Scope
- Supabase `approval_lines` table, RPC functions, or 1536-dim vector transfer (reindex required, per architecture gotchas).
- `classify_stage()` changes, stage-3 completion-marker strings, per-row completion-state and task-card field RPA readers (covered by backlog Next items, need live dumps). The verified raw `결재방법` column is read for the known stage-2 signature only.
- Task-card selection RPA speedup (`_perform_task_card_selection` coords/sleeps) and confirm-dialog fast-pass unification.
- Chroma/Ollama revival, pricing/threshold hard-coding outside `config.py`, unrelated API changes.

## Resolved runtime behavior
- Electronic documents check handler identity before reuse/classification. A different handler asks for review consent, clicks the approval button and confirms only the known approval prompt on explicit consent. A verified result/next-document transition permits the next iteration with fresh consent; failure or skip ends the run. No approval-line learning or task-card selection occurs in this branch.
- Empty approval memory goes directly to manual registration without a numbered list menu. `MY_NAME` / `base_data.json.my_name` supplies the exact operator name; missing identity requests bounded runtime input.
- `MY_DEPARTMENT` overrides `base_data.json.my_department`. Empty means a timed department pick; selected members display their full org-chart node text.
- Enter-wait timeout is 60 seconds (`TimeoutConfig.MANUAL_APPROVAL_LINE_WAIT`). Selection menus also use a bounded deadline; retries never reset the menu's deadline.
- Stored names require unique department resolution before application. Homonyms and incomplete org-chart reads abort application.
- Stage 2 configures the approval line and ends the run. The operator submits the document in the client; adding a superior alone must not trigger task-card processing on the same document.
- A reception selection is removed from the pending-learning queue if applying the line or calling the reception flow fails. A failed selection or role probe ends the run without repeatedly prompting on the same document.

## Further Notes

- Implemented foundations (2026-10-07): local ordered approval-line store, transactional updates, KNN deduplication, pagination and Supabase no-ops; org-chart department/member readers and unique department resolution.
- Runtime reception/assigned wiring is implemented in `Main`, `DocumentProcessor` and `OfficialCollector`. Supabase mode injects a separate local model/store for approval lines; cloud vectors never enter that store.
- Verification: 301 unit tests pass using temporary local databases and fake GUI controls; pylint, Bandit (`--ini`) and touched-file Black checks pass. Six touched service/config/input modules pass mypy. Whole-project mypy has 50 diagnostics, identical to a same-format HEAD snapshot; no new type errors. Live-client verification remains pending.
- Risk: local DB file is dimension-pinned (384 vs 1536); new vec table must join the existing dimension check and reindex hint.
- The 0.85 auto-selection constant now lives in `config.py` (`VectorConfig`).
- Backlog sync: this spec does not close the `classify_stage()` or stage-3 dump items; tickets must reference them as blocked-by rather than duplicate.
