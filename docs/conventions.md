# Conventions

Rules agents get wrong that the linter does not own. Tooling-owned style (black, pylint, mypy) is not repeated here.

## Trace Headers

Every code change cites its backlog item. New/edited source files carry:

```python
# Trace: <backlog.md item or sprint title>
```

Old `spec_id`/`task_id` headers remain as history; replace with the one-liner on touch, never add new `SPEC-*`/`TASK-*` IDs.

Commits reference the backlog item or sprint title as well. Spec ambiguity is never guessed — file a `backlog.md` entry instead.

## Git Conventions

```
[TYPE] description
```

| Type | Meaning |
|------|---------|
| `[FEAT]` | New behavior |
| `[FIX]` | Bug fix — reproduction test first, then minimal change |
| `[REFACTOR]` | Structure only, no behavior change |
| `[TEST]` | Test-only change |
| `[CONSTRAINT]` | Structural guards (lint rule, CI check, schema) |
| `[DOCS]` | Documentation only |
| `[HARNESS]` | Skill / hook / agent-instruction changes |
| `[PLAN]` | Backlog / task-queue changes |

Branch before the first edit of any task: `git checkout -b <type>/<slug>`. Never commit directly to `main`.

## Service Rules

- **DI, not construction:** services receive collaborators as constructor args from `main.py`. A service importing and instantiating a sibling is a violation, even when it "works".
- **Errors via decorators:** Supabase paths use `@handle_supabase_error`, pywinauto paths use `@handle_pywinauto_error` (`utils/error_handler.py`). Bare `except`/`pass` is forbidden — log with context.
- **Logging:** `logger.info("msg %s", arg)` — lazy `%s` args, never f-strings; keep messages UTF-8 clean (Korean log text is fine).
- **Instrumentation:** every I/O-heavy function gets `@log_execution_time` (or `tracked_timer` for blocks). Analyze `⏱️` log lines with `src/utils/phase3_analysis.py` (baselines, regression compare, markdown reports).

## RPA Rules

- Waits go through named helpers (`_ensure_*`, `_wait_for_*`); bare `time.sleep` needs a rationale comment, and long waits get wrapped.
- Every interactive CLI fallback (selection menus, confirmations) carries an explicit timeout/backoff — automation must never hang on a prompt.
- Verify the target window before acting; log failures with the window title and what was attempted.
- Timeouts, button patterns, and window-title patterns live in `config.py` (`TimeoutConfig`, `UIConfig`) — never inline magic numbers. Pricing lives in `OpenAIPricingConfig`; similarity bounds in `VectorConfig`.

## UI Rules

- All user output goes through the `RichConsole` singleton (`src/ui/rich_console.py`) — no `print()` or ANSI escapes in new code.
- Dead Chroma/Ollama references are removal candidates: delete on touch, never extend.
