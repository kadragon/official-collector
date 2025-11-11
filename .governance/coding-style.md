<!-- Trace:
spec_id: SPEC-governance-doc-structure-1
task_id: TASK-001
-->
# Coding Style

- Target Python 3.12+, favor type hints (`typing` or `pydantic`-style) and dataclasses for structured data.
- Logging must remain UTF-8 clean; use `logger.info("msg %s", arg)` instead of f-strings in logging to avoid encoding surprises.
- Keep configuration in `config.py`/`.env`; no hard-coded similarity thresholds, pricing, or credentials inside services.
- Follow dependency-injection: construct services (`SupabaseService`, `OpenAIEmbeddingService`, `DocumentProcessor`) in `main.py` and pass them downward.
- RPA scripts (pywinauto) require explicit waits with descriptive helper names; avoid `sleep()` without rationale and wrap long waits in helper functions.
- Tests first: create or update unit/integration tests (pytest) before modifying implementation per SDD/TDD loop.
