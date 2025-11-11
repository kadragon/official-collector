<!-- Trace:
spec_id: SPEC-governance-doc-structure-1
task_id: TASK-001
-->
# Agent Operating Guide

The full Spec-Driven + Test-Driven workflow is now captured inside:
- `.spec/governance-doc-structure/spec.yaml` (rules of engagement)
- `.tasks/current.yaml` (what is active right now)
- `.governance/` (memory, coding style, patterns, environment)

Follow this boot sequence every session:
1. Read `.governance/memory.md`, `coding-style.md`, and `patterns.md`.
2. Load `.tasks/current.yaml`; if empty, pull the next entry from `.tasks/backlog.yaml`.
3. Open the spec referenced by `spec_id` and implement via RED -> GREEN -> REFACTOR.
4. Update `.tasks/` and `.governance/memory.md` before ending the session.

All new artifacts must start with a Trace block containing `spec_id` and `task_id`.
