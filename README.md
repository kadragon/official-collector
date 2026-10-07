<!-- Trace:
  spec_id: SPEC-governance-doc-structure-1
  task_id: TASK-001
-->
# Official Collector

Official Collector is a Python 3.12+ RPA system that automates reception and electronic official documents.
Supabase (pgvector) and OpenAI embeddings power intelligent handler/task-card matching, while pywinauto drives Windows UI automation.

> Agent contributors: start at `AGENTS.md` (entry map) — `docs/runbook.md` for commands, `docs/architecture.md` for structure, `docs/conventions.md` for rules, `docs/workflows.md` for the work cycle.

## Architecture At A Glance
- **Services**: `DocumentProcessor` orchestrates flows; `SupabaseService` handles CRUD/vector search; `OpenAIEmbeddingService` tracks embedding cost and retries.
- **Data Stores**: Supabase hosts `reception_documents`, `task_cards`, and `document_embeddings`; local caches remain under `./data/` and `.cache/`.
- **Performance**: `utils/performance_logger.py` instruments OpenAI, Supabase, and RPA hotspots.

## SDD/TDD Documentation Map
- `.spec/` - functional truth (see `core-automation`, `supabase-migration`, `performance-observability`, `governance-doc-structure`).
- `.tasks/` - operational truth (`current.yaml`, `backlog.yaml`, `done.yaml`).
- `.governance/` - memory, coding standards, reusable patterns, and environment facts.
Follow the loop: read the spec -> add/update tests -> implement -> refactor -> update `.tasks/` -> summarize in `.governance/memory.md`.

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
- Supabase migration artifacts are tracked in `.tasks/done.yaml` (`TASK-100`), ensuring historical traceability.

## Need To Know
- Always load `.governance/` and `.tasks/current.yaml` before coding; every commit must reference a `spec_id` and a `task_id`.
- Interactive prompts during DocumentProcessor fallback must include timeouts to keep RPA flows safe.
- When ambiguity exists in specs, add a backlog entry instead of guessing.
- Production safety: set `ENVIRONMENT=production` to block destructive operations; the `--delete` workflow requires explicit opt-in there.
