# Runbook

## Quick Start

### Prerequisites

- Python 3.12+ (`python --version`)
- `uv` package manager
- Windows with GUI access to the target official-document client (pywinauto is Windows-only)
- Supabase project + OpenAI API key (see Environment Variables)

### Setup

```powershell
git clone <repo-url>
cd official-collector
uv install                # install dependencies
uv sync --group dev       # dev dependencies (pytest, pylint, mypy, bandit, black)
Copy-Item .env.example .env   # then fill in real credentials
```

### Verify

```powershell
uv run ./src/main.py --help   # entry starts without import errors
pytest tests/unit/ -v         # unit suite green
```

## Build

No build step — interpreted Python, entry `src/main.py`.

| Command | Purpose |
|---------|---------|
| `uv run ./src/main.py` | Production mode |
| `uv run ./src/main.py --interactive` | Manual confirmation per document |
| `uv run ./src/main.py --delete` | Cleanup / deletion workflow (destructive — see below) |
| `uv run -m src.debug.debug_manager` | pywinauto window-inspection / dialog monitoring |

## Test

| Command | Purpose |
|---------|---------|
| `pytest tests/unit/ -v` | Unit tests only (fast, no external services) |
| `pytest tests/ --cov=src --cov-report=html` | Full suite with coverage |
| `pytest tests/unit/test_console_interface.py -k clear_screen` | Single-target example |
| `uv run pylint src/` | Lint (lazy `%s` logging, no swallowed errors) |
| `uv run mypy -p services -p dialogs -p ui -p utils -p debug -m config -m main -m delete_data` | Type check, production code |
| `uv run bandit -r -ll --configfile .bandit src/` | Security scan |
| `uv run black --check --diff .` | Format check |

Test files live in `tests/unit/` (`test_*.py`); fixtures in `tests/fixtures/`. Markers: `integration`, `performance`, `unit`, `slow`, `requires_data` (`pytest.ini`).

## Lint & Format

Pre-commit runs all four (`black --check`, `mypy`, `pylint`, `bandit`); CI runs Bandit on push/PR to `main`.

## Deploy

No deploy pipeline — runs as a local Windows workstation process. Production checklist:

- [ ] `.env` holds real `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- [ ] `ENVIRONMENT=production` set (blocks `clear_all_data` unless `ALLOW_DESTRUCTIVE_OPERATIONS=true`)
- [ ] Budget limits configured (`OPENAI_DAILY_BUDGET_USD`, `OPENAI_MONTHLY_BUDGET_USD`)
- [ ] `./logs/audit/` writable (audit JSONL sink)

## Common Failures

### Approval decision memory

- The legacy `document_sort()` entry point uses injected `TaskCardHandler.capture_requested()`: verified selector control, bounded operator selection and actual field readback. A differing card is rejected before document-info OK saves it. Missing/cancelled capture or a changed raw title returns `False` before approval. Normal final-handler capture still permits operator corrections. Coordinate clicks and fixed selection sleeps are removed; live speed measurements remain pending.
- Reception and approval results share one complete confirmation-body pass: enumerate all descendant Text/Edit/Static fields once, ignoring the generic `확인` caption and button controls. Read the complete body before matching; an early matching clause must not hide a warning or cancellation in another field. `UIConfig` lists known complete next/exit bodies, including verified completion-prefix/question combinations. Unknown bodies remain untouched; approval-result handling returns a boolean outcome.
- Enumerate confirmation windows under the retained main-window wrapper, then read and click the same dialog wrapper; a lazy `WindowSpecification` can otherwise re-resolve a different window by title. Reception/circulation questions require the entire body to match exactly. Nested body fields are included in the complete pass; unreadable bodies may be retried on that same wrapper. Missing/ambiguous windows or buttons, failed body reads and destroyed wrappers stop without confirming another dialog.

- Own-handler documents with receptionist and manager rows request `상위 결재 완료 여부 확인`; select final processing only after superior approval actually completed. DB card recommendations are shown, then the client unit-card chooser opens. Choose/confirm there, leave document-info Confirm untouched and enter Enter in the console within 60 seconds. The collector reads the actual card, saves document info and verifies final approval before retaining its DB update. Live end-to-end verification pending.

- Toolbar combo boxes opening in sequence during review can come from pywinauto best-match indexing (`dlg["name"]`): its text collection expands unnamed UIA combos. Review-path payment-info/approval buttons and approval tab now use exact title/control-type selectors. Live behavior verification pending.

- Submitted drafts with a `기안` row and the configured operator as `검토` or `결재` use the existing explicit review-consent path; they do not require an `업무담당자` row. Missing or ambiguous own roles stop.
- Manual line save is complete only after acknowledging the exact `결재선 변경을 완료했습니다.` result and verifying result/editor closure. The original editor wrapper is retained before saving; post-close title lookup cannot invalidate a successful save. Live result-click verification pending.

- The first post-click observation may already be the completion/next-document prompt. Review confirmation reads its body: a known approval question is confirmed, while a known next/exit result proceeds without another approval click. Confirmation/result waits are bounded to 10 seconds; failures log the observed body. Unknown/cancel-approval messages remain blocked.
- A verified next-document prompt is confirmed before a bounded 10-second load wait: prompt gone, nonempty raw title changed, main window enabled. Only then is the next title captured for review. Unchanged title or incomplete loading stops; identical-title queue entries need a verified document identifier before support can be added. Review-time title-change checks remain active.
- If a post-submit confirmation remains open with `결재문서를 처리하였습니다. 다음 문서를 처리하겠습니까?`, this is the next-document prompt (user screenshot verified). Its body is read from UIA child wrappers without calling nonexistent `exists()`; the existing continuation loop confirms it. `예(Y)` is included alongside `예(&Y)` in button fallback patterns. Live verification pending.
- Electronic documents compare the `업무담당자` row's name with `MY_NAME` (fallback: `base_data.json.my_name`, then a 60-second input prompt). Use the exact name shown in the approval line. Missing/ambiguous handler or unavailable identity stops the run.
- Different handler: review the document, then select `검토 완료, 결재`. The collector clicks approval, confirms only the known approval prompt, and requires a result/next-document transition before counting success. Next/exit dialogs use the existing loop; each next review document requires fresh consent. Skip, timeout, unexpected prompt or unverified transition stops the run. This branch never selects task cards or changes the approval line. Live verification pending.
- Operator-name input uses a composed console line instead of raw key reads. A child reader inherits console stdin; its 60-second timeout kills/waits for the reader. Blank Enter cancels. Numeric menus keep raw bounded input; set `MY_NAME` to avoid repeated name entry.
- Assigned-line memory with no saved candidates opens manual registration directly; no empty numbered-list menu.
- `Approval role probe could not close its dialog` means closure was not verified. Cancellation uses bounded win32 `WM_CLOSE` instead of Escape; live verification remains pending.
- Closure verification retains the original HWND wrapper. Re-resolving a `WindowSpecification` by title after closure can fail even when the original dialog closed; live verification remains pending.
- Reception uses `MY_DEPARTMENT` (or `base_data.json.my_department`) for the org-chart fallback. Empty requests a department pick. Menus show full member-node text; ambiguous names are refused.
- Assigned documents reuse local approval lines in both vector backends. Below 0.85 similarity, a timed selection asks for confirmation or manual configuration.
- For manual configuration, build the line in the open client dialog, leave its Confirm button untouched, then return to the console and press Enter within 60 seconds. The collector reads and confirms the line. Escape, timeout, console failure or unverified save returns without learning it.
- After configuring an assigned document's line, the run ends. Submit the document in the client. Completion markers for stage 3 still need a live dump.
- Live verification is pending: check reception department/member reads, ordered application and manual capture/save/cancel against a disposable client document before production use.

### Supabase connection failures
**Symptom:** "Connection refused" / timeout errors, consecutive-failure alerts.
**Cause:** Bad credentials, RLS policy block, or project downtime.
**Fix:** Verify `.env` vars; `curl $SUPABASE_URL/rest/v1/`; check Supabase dashboard and RLS policies.

### Vector search returns nothing
**Symptom:** Empty recommendation lists.
**Cause:** Similarity threshold too strict, or missing embeddings. The Supabase
backend defaults to `VECTOR_SIMILARITY_THRESHOLD=0.3`; the local FastEmbed
backend defaults to `LOCAL_VECTOR_SIMILARITY_THRESHOLD=0.5` (retuned 2026-10-07:
sample Korean titles score ~0.95 near-duplicate, 0.49–0.64 related, 0.21–0.45
unrelated on the 384-dim model, so 0.3 admits unrelated pairs).
**Fix:** Lower the threshold for the active backend (`VECTOR_BACKEND=supabase`
vs `local`); verify counts via `get_document_count()`.

### Local vector DB dimension mismatch
**Symptom:** `ValueError: Local vector DB dimension mismatch` on startup.
**Cause:** The SQLite DB is pinned to one embedding dimension (`vector_meta`).
Supabase 1536-dim OpenAI vectors do not transfer to the local 384-dim store —
switching models/backends requires a reindex, never a copy.
**Fix:** Delete the local DB file (default `data/local_vectors.db`) or clear and
reindex from source documents; keep one embedding model per DB.

### Quota exceeded
**Symptom:** "Quota check failed", API calls blocked.
**Cause:** Daily/monthly OpenAI budget spent.
**Fix:** Raise `OPENAI_DAILY_BUDGET_USD`; inspect `logs/audit/` for usage spikes; never reset metrics in production.

### pywinauto targets missing (Linux CI / headless)
**Symptom:** Window-not-found errors outside Windows.
**Cause:** RPA stack requires the Windows GUI client.
**Fix:** Run RPA paths on Windows only; keep pure-logic tests in `tests/unit/` platform-independent.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | yes | OpenAI embeddings key |
| `SUPABASE_URL` / `SUPABASE_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | yes | Supabase access |
| `ENVIRONMENT` | no | `production` blocks destructive ops |
| `MY_NAME` | no | Exact operator name for handler routing; fallback to base data, then timed runtime input |
| `ALLOW_DESTRUCTIVE_OPERATIONS` | no | `true` re-enables deletes in production |
| `VECTOR_SIMILARITY_THRESHOLD` | no | Supabase backend prefilter, default `0.3`, range `0.0–1.0` |
| `LOCAL_VECTOR_SIMILARITY_THRESHOLD` | no | Local backend prefilter, default `0.5`, range `0.0–1.0` (falls back to legacy `VECTOR_SIMILARITY_THRESHOLD` when unset) |
| `OPENAI_DAILY_BUDGET_USD` / `OPENAI_MONTHLY_BUDGET_USD` | no | Defaults `10.0` / `300.0` |
| `QUOTA_AUTO_STOP` | no | `true` blocks all API calls once exceeded |
| `LOG_LEVEL` / `DEBUG_MODE` / `LOG_RETENTION_DAYS` | no | Logging tuning |

Never commit real secrets — `.env.example` holds placeholders only.
