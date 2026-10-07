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

### Supabase connection failures
**Symptom:** "Connection refused" / timeout errors, consecutive-failure alerts.
**Cause:** Bad credentials, RLS policy block, or project downtime.
**Fix:** Verify `.env` vars; `curl $SUPABASE_URL/rest/v1/`; check Supabase dashboard and RLS policies.

### Vector search returns nothing
**Symptom:** Empty recommendation lists.
**Cause:** `VECTOR_SIMILARITY_THRESHOLD` too strict (default `0.3`), or missing embeddings.
**Fix:** Lower threshold (`VECTOR_SIMILARITY_THRESHOLD=0.2`); verify counts via `get_document_count()`.

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
| `ALLOW_DESTRUCTIVE_OPERATIONS` | no | `true` re-enables deletes in production |
| `VECTOR_SIMILARITY_THRESHOLD` | no | Default `0.3`, range `0.0–1.0` |
| `OPENAI_DAILY_BUDGET_USD` / `OPENAI_MONTHLY_BUDGET_USD` | no | Defaults `10.0` / `300.0` |
| `QUOTA_AUTO_STOP` | no | `true` blocks all API calls once exceeded |
| `LOG_LEVEL` / `DEBUG_MODE` / `LOG_RETENTION_DAYS` | no | Logging tuning |

Never commit real secrets — `.env.example` holds placeholders only.
