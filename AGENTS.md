# Official Collector Agent Rules

Python 3.12+ RPA: pywinauto drives Windows official-document clients; Supabase/pgvector + OpenAI embeddings match handlers and task cards. Entry `src/main.py`. Queue truth `backlog.md`; durable knowledge `docs/` + `CHANGELOG.md` (`tasks.md` exists only during an active sprint).

## Docs Index (read on demand)

| File | When to read |
|------|--------------|
| `docs/runbook.md` | For build, test, lint commands, env setup, failure modes |
| `docs/architecture.md` | Before adding modules or changing service boundaries |
| `docs/conventions.md` | Before writing service, RPA, or UI code |
| `docs/workflows.md` | When starting any spec-to-code cycle |
| `docs/design/document-stages.md` | Before touching reception vs assigned-to-me vs post-approval routing |

## Golden Principles

Violations block commits. Each names its check.

1. **Config in `config.py`/`.env` only** — no hard-coded thresholds, pricing, or credentials in services. Check: `rg "SUPABASE_KEY|OPENAI_API_KEY" src/services/ src/ui/` empty.
2. **Dependency injection** — `main.py` constructs services and passes them down; a service never instantiates a sibling. Check: `rg "Service\(" src/services/` empty.
3. **Log with `%s`, never swallow** — logger calls use lazy `%s` args, no f-strings; every `except` logs. Check: `uv run pylint src/` green.
4. **Explicit RPA waits** — pywinauto goes through named wait helpers, no bare `time.sleep`; CLI fallbacks carry timeouts. Check: `rg "time\.sleep" src/` empty.
5. **Tests + trace first** — extend pytest tests before changing implementation; every commit references the `backlog.md` item or sprint title. Check: `pytest tests/unit/ -v` green.
6. **Fabrication ban:** an unread value is `[unknown — read {source}]`, never guessed. Applies to ports, endpoints, schema fields, thresholds, versions.

## Delegation

No roles or orchestrator exist — work inline on the main thread. Ad-hoc fan-out uses built-in `Explore` (code search) and `general-purpose` (parallel research) subagents with a four-field brief: Objective / Output format / Tools / Boundaries. Recurring delegations arrive via `dev:harness-curate` on transcript evidence.

<!-- harness:verbatim — mandated block, exempt from the non-inferability filter. Do not trim or paraphrase. -->
## Token Economy

Rules that apply every message — keep the context window lean.

1. Do not re-read a file already read in this session. If you need to check a change, read only the diff/region.
2. Do not call tools just to confirm information you already have. Simple questions deserve direct answers.
3. Run independent tool calls in parallel (multiple reads, grep + glob, etc.) — not sequentially.
4. Delegate any analysis that would produce >20 lines of output to a sub-agent; return only the conclusion to this context.
5. Do not restate what the user just said. They can read their own message.

## Working with Existing Code

Boundaries the linter can't express — ✅ do / ⚠️ do carefully / 🚫 never (commands: `docs/runbook.md`):

| | |
|---|---|
| ✅ | Construct services in `main.py`; handle errors with `utils/error_handler.py` decorators; wrap I/O with `@log_execution_time` |
| ⚠️ | `official_service.py` is mid-split (1047 lines); use `iter_all_*` generators for Supabase lists; dead Chroma/Ollama refs — remove on touch, never revive |
| 🚫 | `shell=True` in subprocess; bare `except`/`pass`; direct commit to `main`; guessing at spec ambiguity — file a `backlog.md` entry instead |

## Language Policy

- Code, commits, docs: English
- User-facing strings: Korean + English via Rich (existing convention); logs stay UTF-8 clean

<!-- harness:verbatim — mandated block, exempt from the non-inferability filter. Do not trim or paraphrase. -->
## Maintenance

Update this file **only** when ALL of the following are true:

1. Information is not directly discoverable from code / config / manifests / docs
2. It is operationally significant — affects build, test, deploy, or runtime safety
3. It would likely cause mistakes if left undocumented
4. It is stable and not task-specific

**Never add:** architecture summaries, directory overviews, style conventions
already enforced by tooling, anything already visible in the repo, or
temporary / task-specific instructions.

Prefer modifying or removing outdated entries over appending. When unsure, add
a short inline `TODO:` comment rather than inventing guidance.

Size budget: target ≤100 lines, hard warn >200. Move long content to
`docs/*.md` (read on demand, cross-tool) and leave a pointer line here. On a
Claude-Code-only repo you may instead use `.claude/rules/*.md` (path-scoped,
auto-loads when the matching area is touched); on a multi-tool repo keep the
content in `docs/` so Codex/Cursor see it too.

**Memory boundary:** durable code/repo facts live here, in `.claude/rules/`, and
`docs/` — human-authored and version-controlled. Claude Code's auto-memory
(`MEMORY.md`) holds the model's discovered preferences and cross-session
learnings only; never promote a code fact into auto-memory, and don't hand-edit
`MEMORY.md`.
