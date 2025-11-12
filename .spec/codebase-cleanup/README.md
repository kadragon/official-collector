<!-- Trace:
spec_id: SPEC-codebase-cleanup-1
task_id: TASK-012
-->

# Codebase Cleanup & Architecture Improvement Plan

> 📅 Created: 2025-11-12
> 🎯 Status: Planning Complete
> ⏱️ Estimated Effort: 21 hours (2.5 days)

## Executive Summary

Comprehensive codebase analysis identified technical debt accumulated during major library migrations:
- **Ollama → Supabase**: Legacy Chroma references remain
- **ANSI → Rich UI**: Partial migration leaves inconsistent patterns

**Current State**: 60% governance compliance, 3000 LOC with significant duplication
**Target State**: 95%+ compliance, 2700 LOC, modular architecture

---

## 📊 Analysis Results

### Legacy Code Residue
- ❌ **Chroma references** in config.py, delete_data.py (should be 100% Supabase)
- ⚠️ **ANSI codes** still used in console_interface.py deletion UI
- ✅ **Ollama** fully removed (no issues found)

### Architecture Violations
1. **Dependency Injection** (High): SupabaseService creates dependencies internally
2. **Logging Pattern** (High): ~20 files use f-strings instead of %s formatting
3. **Performance Instrumentation** (Medium): 7 Supabase methods missing decorators
4. **Configuration** (Medium): Hard-coded timeouts, pricing, UI patterns

### Code Quality Issues
1. **official_service.py**: 1047 lines (should be <300 per SRP)
2. **Button Click Logic**: 3 duplicate methods (~100 lines)
3. **Exception Handling**: 100+ broad `except Exception` statements
4. **Type Hints**: ~20 functions missing return type annotations

---

## 🎯 Three-Phase Improvement Plan

### Phase 1: Critical Cleanup (Priority 1)
**Duration**: 4 hours
**Focus**: Remove blockers, fix governance violations

| Task | Description | Time | Files |
|------|-------------|------|-------|
| TASK-012 | Remove Chroma legacy code | 1h | config.py, delete_data.py |
| TASK-013 | Fix dependency injection | 0.5h | supabase_service.py, main.py |
| TASK-014 | Convert f-string logging | 2h | 4 files, ~20 violations |
| TASK-015 | Add performance instrumentation | 0.5h | supabase_service.py |

**Acceptance Criteria**:
- `grep -ri 'chroma' src/` returns 0 results
- All services follow DI pattern
- Zero f-strings in logger calls
- All I/O methods have `@log_execution_time`

---

### Phase 2: Structural Refactoring (Priority 2)
**Duration**: 11 hours
**Focus**: Improve architecture, reduce duplication

| Task | Description | Time | Impact |
|------|-------------|------|--------|
| TASK-016 | Split official_service.py | 8h | 1047 → 700 lines (4 files) |
| TASK-017 | Unify button click logic | 2h | -100 lines duplication |
| TASK-018 | Centralize configuration | 1h | TimeoutConfig, UIConfig |

**Acceptance Criteria**:
- `official_service.py < 350 lines`
- Single button click implementation
- No magic numbers or hard-coded strings

---

### Phase 3: Quality Improvements (Priority 3)
**Duration**: 6 hours
**Focus**: Incremental polish

| Task | Description | Time | Benefit |
|------|-------------|------|---------|
| TASK-019 | Specific exception types | 3h | Better error handling |
| TASK-020 | Remove remaining ANSI codes | 2h | Consistent Rich UI |
| TASK-021 | Complete type hint coverage | 1h | mypy --strict passes |

**Acceptance Criteria**:
- Exception decorators for common patterns
- Zero ANSI escape codes
- Full type coverage, mypy clean

---

## 📈 Expected Outcomes

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Total LOC** | ~3000 | ~2700 | -10% |
| **official_service.py** | 1047 lines | <700 lines | -33% |
| **Governance Compliance** | 60% | 95%+ | +58% |
| **Code Duplication** | High | Low | DRY compliant |
| **Legacy References** | Multiple | Zero | 100% clean |
| **I/O Instrumentation** | Partial | Complete | 100% coverage |

---

## 🚀 Getting Started

### Prerequisites
```bash
# Ensure all tests pass
pytest tests/ -v

# Check current type coverage
mypy -p services -p dialogs -p ui -p utils

# Run existing linters
uv run pylint src/
```

### Recommended Approach
1. **Create feature branch**: `git checkout -b cleanup/codebase-improvements`
2. **Start with Phase 1**: Highest ROI, lowest risk
3. **Validate continuously**: Run tests after each task
4. **Review incrementally**: Don't wait for all phases
5. **Merge by phase**: Separate PRs for easier review

### Phase 1 Quick Start
```bash
# TASK-012: Remove Chroma code
grep -ri 'chroma' src/  # Find all references
# Edit config.py, delete_data.py
pytest tests/unit/test_config.py -v

# TASK-013: Fix DI
# Edit main.py, supabase_service.py
pytest tests/unit/test_supabase_service.py -v

# TASK-014: Fix logging
grep -r 'logger.*f"' src/  # Find f-strings
# Replace with %s formatting
pytest tests/ -k logging

# TASK-015: Add decorators
# Add @log_execution_time to 7 methods
pytest tests/unit/test_supabase_service.py -v
```

---

## 📋 Task Reference

### Backlog Location
All tasks tracked in `.tasks/backlog.yaml`:
- **TASK-012** through **TASK-015**: Phase 1 (Priority 1)
- **TASK-016** through **TASK-018**: Phase 2 (Priority 2)
- **TASK-019** through **TASK-021**: Phase 3 (Priority 3)

### Governance References
- **coding-style.md**: DI pattern, logging format, type hints
- **patterns.md**: Performance instrumentation, batch operations
- **memory.md**: Session log updated with analysis findings

### Test Strategy
Each phase requires:
- ✅ Unit tests pass (`pytest tests/unit/ -v`)
- ✅ Integration tests pass (`pytest tests/integration/ -v`)
- ✅ Type checking clean (`mypy -p services -p dialogs -p ui -p utils`)
- ✅ Coverage maintained (`pytest --cov=src --cov-report=html`)
- ✅ Linting passes (`uv run pylint src/`)

---

## 🎓 Key Learnings

### What Went Wrong
1. **Incomplete Migration**: Chroma code left behind after Supabase switch
2. **Partial Refactoring**: Rich UI migration didn't remove all ANSI codes
3. **Rapid Feature Development**: Technical debt accumulated without cleanup sprints
4. **Missing Validation**: No automated checks for governance compliance

### How to Prevent
1. **Migration Checklist**: Create removal checklist before switching libraries
2. **Automated Governance**: Add pre-commit hooks for logging patterns, f-strings
3. **Regular Audits**: Schedule quarterly technical debt reviews
4. **Code Size Limits**: Add CI checks for file size (e.g., max 500 lines)
5. **Test Coverage Gates**: Fail CI if coverage drops below 90%

---

## 🔗 Related Documents

- **Spec**: [spec.yaml](./spec.yaml)
- **Tasks**: [.tasks/backlog.yaml](../../.tasks/backlog.yaml)
- **Governance**: [.governance/coding-style.md](../../.governance/coding-style.md)
- **Memory**: [.governance/memory.md](../../.governance/memory.md)
- **Analysis Report**: See session log 2025-11-12 in memory.md

---

## 📞 Questions?

- **Task Assignment**: Check `.tasks/backlog.yaml` for ownership
- **Technical Approach**: Refer to governance docs for patterns
- **Priority Questions**: Phase 1 should be completed first (blocking issues)
- **Scope Concerns**: Each task is independently valuable; phases can be split

---

**Status**: ✅ Planning Complete - Ready for Implementation
**Next Step**: Review Phase 1 tasks and begin with TASK-012 (Chroma cleanup)
