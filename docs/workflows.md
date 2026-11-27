# Workflows

The repo uses GitHub Issues as its work queue. All steps below run inline on the main thread.

## `code` — Implementation (primary cycle)

1. **Branch.** `git checkout -b <type>/<slug>` — never work on `main`.
2. **Read truth.** Load the owning `docs/` pages and the issue before touching code.
3. **Tests first.** Write or extend pytest tests reproducing the desired behavior; watch them fail.
4. **Implement minimally.** Smallest change that passes; follow `docs/conventions.md` (DI, decorators, `%s` logging, explicit waits).
5. **Verify.** `pytest tests/unit/ -v`, then `uv run pylint src/`; run mypy/bandit for touched areas. Never weaken a valid test to make code pass.
6. **Record.** Link the issue in the PR with `Closes #N` and append one `CHANGELOG.md` line (≤160 chars).

## `draft` — Documentation

Ground every claim in current code. Update `docs/`; never change production code in this workflow. File a queue issue for a missing constraint.

## `constrain` — Architectural Enforcement

1. Write the structural check (lint rule, grep test, or pytest boundary test) first.
2. Run it. If current code violates it, file a remediation issue.
3. Document the boundary in `docs/architecture.md`.

## `sweep` — Garbage Collection

Between features: remove dead refs (Chroma/Ollama leftovers), stale thresholds, duplicated wait logic. Fix trivial items inline and file issues for structural items. No sweep script installed yet — first drift signal triggers it.

## `explore` — Research

State the question → inspect windows/code paths → report options and tradeoffs → do not commit. Approved findings flow into `code`.

## Permitted Side-Effects

| Primary workflow | Permitted side-effect |
|------------------|-----------------------|
| `code` | File a queue issue on discovering debt or spec ambiguity |
| `code` | Update owning docs after implementation |
| `draft` | File a queue issue when a doc reveals missing behavior |
| `sweep` | Fix trivial dead code inline |

Writing production code during `draft` or `sweep` is not permitted.
