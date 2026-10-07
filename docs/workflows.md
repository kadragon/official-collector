# Workflows

The repo runs one defined loop (from `README.md`): read the spec → add/update tests → implement → refactor → update `.tasks/` → summarize in `.governance/memory.md`. All steps below run inline on the main thread — this repo has no agent roles, so drop any "delegate to X" wording until `dev:harness-curate` creates one.

## `code` — Implementation (primary cycle)

1. **Branch.** `git checkout -b <type>/<slug>` — never work on `main`.
2. **Read truth.** Load the owning `.spec/` file, `.tasks/current.yaml` (+ `backlog.yaml`), and relevant `.governance/` pages before touching code.
3. **Tests first.** Write or extend pytest tests reproducing the desired behavior; watch them fail.
4. **Implement minimally.** Smallest change that passes; follow `docs/conventions.md` (DI, decorators, `%s` logging, explicit waits).
5. **Verify.** `pytest tests/unit/ -v`, then `uv run pylint src/`; run mypy/bandit for touched areas. Never weaken a valid test to make code pass.
6. **Record.** Move the task entry in `.tasks/` (`backlog.yaml` → `done.yaml`), append the session learning to `.governance/memory.md`.

## `draft` — Documentation

Ground every claim in current code. Update `.governance/` or `docs/`; never change production code in this workflow. A doc that reveals a missing constraint becomes a `.tasks/backlog.yaml` entry.

## `constrain` — Architectural Enforcement

1. Write the structural check (lint rule, grep test, or pytest boundary test) first.
2. Run it. If current code violates it, add remediation to `.tasks/backlog.yaml` — do not fix inline.
3. Document the boundary in `docs/architecture.md`.

## `sweep` — Garbage Collection

Between features: remove dead refs (Chroma/Ollama leftovers), stale thresholds, duplicated wait logic. Trivials fixed inline; structural items go to `.tasks/backlog.yaml`. No sweep script installed yet — first drift signal triggers it.

## `explore` — Research

State the question → inspect windows/code paths → report options and tradeoffs → do not commit. Approved findings flow into `code`.

## Permitted Side-Effects

| Primary workflow | Permitted side-effect |
|------------------|-----------------------|
| `code` | Add a `.tasks/backlog.yaml` entry on discovering debt or spec ambiguity |
| `code` | Update owning docs after implementation |
| `draft` | Add a backlog entry when a doc reveals missing behavior |
| `sweep` | Fix trivial dead code inline |

Writing production code during `draft` or `sweep` is not permitted.
