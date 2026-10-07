# Official Collector

Official Collector is a Python 3.12+ RPA system that automates reception and electronic official documents.
Supabase (pgvector) and OpenAI embeddings power intelligent handler/task-card matching, while pywinauto drives Windows UI automation.

> Agent contributors: start at `AGENTS.md` (entry map) — `docs/runbook.md` for commands, `docs/architecture.md` for structure, `docs/conventions.md` for rules, `docs/workflows.md` for the work cycle.

## Architecture At A Glance
- **Services**: `DocumentProcessor` orchestrates flows; `SupabaseService` handles CRUD/vector search; `OpenAIEmbeddingService` tracks embedding cost and retries.
- **Data Stores**: Supabase hosts `reception_documents`, `task_cards`, and `document_embeddings`; local caches remain under `./data/` and `.cache/`.
- **Performance**: `utils/performance_logger.py` instruments OpenAI, Supabase, and RPA hotspots.

## Work Queue & Knowledge Map
- `backlog.md` - work queue (pick the top `## Now` item; `tasks.md` exists only during an active sprint).
- `CHANGELOG.md` - one line per completed item (detail lives in git history).
- `docs/` - durable knowledge (`runbook.md`, `architecture.md`, `conventions.md`, `workflows.md`).
Follow the loop: read `docs/` -> pick a `backlog.md` item -> add/update tests -> implement -> refactor -> tick `backlog.md` -> append a `CHANGELOG.md` line.

## Setup

Prerequisites: Python 3.12+, `uv`, Windows with GUI access to the target official-document client.

```powershell
uv sync                  # install dependencies
uv sync --group dev      # dev dependencies (pytest, pylint, mypy, bandit, black)
Copy-Item .env.example .env   # then fill in real credentials
```
Populate `.env` with OpenAI + Supabase credentials (`OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`).
Full variable reference: `docs/runbook.md` → Environment Variables.

## Running & Testing
```powershell
uv run ./src/main.py                 # production mode
uv run ./src/main.py --interactive   # manual confirmation per document
uv run ./src/main.py --delete        # cleanup / deletion workflow

pytest tests/unit/ -v
pytest tests/ --cov=src --cov-report=html
uv run pylint src/
```

## Data & Debug Utilities
- Base datasets live in `data/base_data.json`; historical migrations land in `data/backup/`.
- Use `uv run -m src.debug.debug_manager` for pywinauto window-inspection or dialog monitoring.
- Supabase migration history is recorded in `CHANGELOG.md`.

## Need To Know
- Always load `docs/` and `backlog.md` before coding; every commit must reference the backlog item or sprint title.
- Interactive prompts during DocumentProcessor fallback must include timeouts to keep RPA flows safe.
- When ambiguity exists in specs, add a backlog entry instead of guessing.
- Production safety: set `ENVIRONMENT=production` to block destructive operations; the `--delete` workflow requires explicit opt-in there.
