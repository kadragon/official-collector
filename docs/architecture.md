# Architecture

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+, strict typing (mypy) |
| RPA | pywinauto + pywin32 (Windows-only) |
| Database | Supabase PostgreSQL + pgvector (HNSW), `supabase` SDK |
| Embeddings | OpenAI `text-embedding-3-small` (1536 dims) |
| UI | Rich (panels, tables, trees, prompts) via `src/ui/rich_console.py` singleton |
| Config | `src/config.py` (`UnifiedConfig`) + `.env` |
| CI | GitHub Actions (Bandit); pre-commit (black, mypy, pylint, bandit) |

## Source Layout

```
src/
  main.py                 # composition root — constructs all services, parses CLI flags
  config.py               # UnifiedConfig: timeouts, pricing, vector, UI patterns
  services/
    document_processor.py # orchestrates reception + task-card flows
    supabase_service.py   # CRUD + vector search (only module touching the client)
    openai_embedding_service.py  # embeddings, quota, retry, cost tracking
    official_service.py   # pywinauto flows (1047 lines, mid-split — see below)
    window_manager.py / dialog_handler.py / button_controller.py  # RPA splits
  ui/                     # Rich console wrapper + console interface
  dialogs/                # prompt/selection dialogs (timeouts required)
  utils/                  # error_handler (decorators), performance_logger, audit, quota, monitoring
  debug/                  # window inspection via -m src.debug.debug_manager
```

## Layer Rules

Dependency flows downward: `main.py` → `services/` → `utils/` + `config.py`. Upper layers import lower ones, never the reverse.

- `main.py` is the only place that constructs services and injects them downward.
- A service never instantiates a sibling service (known violation being repaired: `SupabaseService` creating its own embedding service — see `.tasks/backlog.yaml` TASK-013 lineage).
- `supabase_service.py` is the only module that imports the Supabase client; embedding calls go through `OpenAIEmbeddingService`.
- `official_service.py` is mid-split into `window_manager` / `dialog_handler` / `button_controller` — put new RPA logic in the split modules, not the monolith.
- `data/base_data.json` seeds lists; runtime caches live in `data/backup/` and `.cache/`.

## Data Access

All persistence goes through `SupabaseService`: tables `reception_documents`, `task_cards`, `document_embeddings`. Similarity search runs in SQL (CTE dedup); service-side dedup is fallback only. Batch RPA mutations accumulate in memory and flush once via `flush_pending_updates()`. Large reads stream through `iter_all_cards()` / `iter_all_receptions()` (batch 500) — never load full tables into memory.

## Key Abstractions

1. **DocumentProcessor** — owns both flows; delegates matching to `SupabaseService`, falls back to CLI prompts with timeouts when confidence drops.
2. **Vector match + CLI fallback** — threshold default `0.3` (`VectorConfig`); low-confidence matches escalate to a timed human pick, never a silent default.
3. **PerformanceLogger** — `@log_execution_time` on every I/O path; Phase 1–7 baselines track the 40–50% throughput target.
4. **Quota / monitoring / audit** — `quota_manager` gates API calls pre-request; `monitoring_hooks` tracks health; `audit_logger` records CRUD/API/SEARCH as JSONL.
5. **Error decorators** — `@handle_supabase_error` / `@handle_pywinauto_error` in `utils/error_handler.py` replace broad `except` blocks.
