<!-- Trace:
spec_id: SPEC-rich-ui-enhancement-1
task_id: TASK-009
-->

# Rich Library UI/UX Enhancement - Overview

## Executive Summary

This document provides a high-level overview of the Rich library UI/UX enhancement initiative for the official-collector project.

### Current State

The project currently uses **ANSI escape codes** for terminal UI, implemented in `src/ui/console_interface.py` (~705 lines).

**Challenges**:
- Manual Unicode width calculation for CJK characters (Korean text)
- Complex box-drawing logic with manual padding
- Limited user input validation
- No visual progress feedback for batch operations
- Plain text error messages without syntax highlighting

### Proposed Solution

Migrate to the **Rich library** (v14.1.0, already installed) in 3 phases:

1. **Phase 1** - Core Infrastructure (4 hours)
2. **Phase 2** - UI Components (6 hours)
3. **Phase 3** - Advanced Features (5 hours)

**Total effort**: ~15 hours (2 working days)

### Key Benefits

| Benefit | Current | With Rich |
|---------|---------|-----------|
| **Code Volume** | 705 lines | ~560 lines (-20%) |
| **CJK Handling** | Manual calculation | Automatic |
| **Input Validation** | Basic try/except | Built-in type-safe prompts |
| **Progress Feedback** | None | Spinner + progress bars |
| **Error Display** | Plain text | Syntax-highlighted tracebacks |
| **Table Rendering** | Manual formatting | Auto-aligned tables |

### Risk Mitigation

- **Feature flag** (`USE_RICH_UI`) enables/disables Rich mode
- **Legacy ANSI mode** remains functional as fallback
- **Zero data risk** - UI changes only, no processing logic affected
- **Gradual rollout** - Phase-by-phase deployment
- **Easy rollback** - Single config change reverts to legacy mode

---

## Visual Comparison

### Before (ANSI)

```
+- 처리 중인 문서 -------------------------------------------+
| 2025학년도 신입생 오리엔테이션 운영 계획                    |
+-----------------------------------------------------------+

[INFO] 과제 카드 매칭 시작...
[OK] 매칭 완료: 신입생 행사 운영
```

### After (Rich)

```
╭─ 처리 중인 문서 ──────────────────────────────────────────╮
│ 2025학년도 신입생 오리엔테이션 운영 계획                  │
╰───────────────────────────────────────────────────────────╯

ℹ [INFO] 과제 카드 매칭 시작...
✓ [OK] 매칭 완료: 신입생 행사 운영

━━━━━━━━━━━━━━━━━━━━━━━━ 50% ━━━━━━━━━━━━━━━━━━━━━━━━━
⠋ 문서 처리 중...
```

---

## Architecture Overview

### Component Layers

```
┌─────────────────────────────────────────────────┐
│            Application Layer                    │
│  (main.py, document_processor.py, etc.)         │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│      ConsoleInterface (Facade)                  │
│  - print_document_info()                        │
│  - print_numbered_list()                        │
│  - get_user_choice_from_list()                  │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┴─────────┐
        │                  │
┌───────▼──────┐  ┌───────▼──────────┐
│ Rich Mode    │  │ Legacy ANSI Mode │
│              │  │                  │
│ rich.panel   │  │ Manual formatting│
│ rich.table   │  │ ANSI escape codes│
│ rich.prompt  │  │ Basic input()    │
│ rich.progress│  │ No progress      │
└──────────────┘  └──────────────────┘
```

### Singleton Pattern

```python
# src/ui/rich_console.py

_console: Optional[Console] = None

def get_console() -> Console:
    """Singleton Rich console instance."""
    global _console
    if _console is None:
        _console = Console(theme=OFFICIAL_COLLECTOR_THEME)
    return _console
```

---

## Implementation Phases

### Phase 1: Core Infrastructure

**Goal**: Replace basic ANSI primitives with Rich equivalents.

**Components**:
- `rich_console.py` - Singleton console + theme
- Config flag - `USE_RICH_UI`
- Message functions - `print_info/success/warning/error`
- Screen control - `clear_screen()`

**Output**: Basic Rich output working, all tests passing.

---

### Phase 2: UI Components

**Goal**: Upgrade complex UI widgets to Rich components.

**Components**:
- Document info box → `rich.panel.Panel`
- Numbered lists → `rich.table.Table`
- Batch loop → `rich.progress.Progress`
- User input → `rich.prompt.IntPrompt`
- Logging → `rich.logging.RichHandler`

**Output**: All UI components using Rich, CJK alignment verified.

---

### Phase 3: Advanced Features

**Goal**: Add visualization and reporting capabilities.

**Components**:
- Real-time updates → `rich.live.Live`
- Result summary → `rich.tree.Tree`
- Error display → `rich.traceback`
- Optional reports → `rich.markdown.Markdown`

**Output**: Production-ready Rich UI with advanced features.

---

## Testing Strategy

### Test Coverage

```yaml
Unit Tests:
  - test_rich_console.py          # Singleton behavior
  - test_rich_ui_components.py    # Widget wrappers
  - test_console_interface.py     # Parametrized Rich/legacy

Integration Tests:
  - End-to-end workflow with USE_RICH_UI=true
  - End-to-end workflow with USE_RICH_UI=false
  - Visual regression tests (snapshots)

Performance Tests:
  - Benchmark: 100 document renders
  - Memory usage during batch
  - Startup time comparison
```

### Success Criteria

- ✅ All existing tests pass in both modes
- ✅ CJK alignment 100% correct
- ✅ Performance within 5% of baseline
- ✅ Code coverage ≥ 90%
- ✅ User satisfaction ≥ 4/5

---

## Rollout Plan

### Week 1: Development

| Day | Activity |
|-----|----------|
| Mon | Phase 1 implementation |
| Tue | Phase 1 testing + Phase 2 start |
| Wed | Phase 2 implementation |
| Thu | Phase 2 testing + Phase 3 start |
| Fri | Phase 3 implementation |

### Week 2: Validation

| Day | Activity |
|-----|----------|
| Mon | Integration testing |
| Tue | Performance benchmarking |
| Wed | User acceptance testing |
| Thu | Documentation + cleanup |
| Fri | Production deployment |

---

## Configuration

### Environment Variables

```bash
# Enable Rich UI (default: true)
USE_RICH_UI=true

# Disable Rich UI (fallback to legacy ANSI)
USE_RICH_UI=false
```

### Code Configuration

```python
# src/config.py

class Config:
    # UI Configuration
    USE_RICH_UI: bool = os.getenv("USE_RICH_UI", "true").lower() == "true"
```

---

## Migration Example

### Before: ANSI Code

```python
def print_info(message: str) -> None:
    """정보 메시지를 출력합니다."""
    _logger().info(message)
    print(f"{Colors.BLUE}{Symbols.INFO} {message}{Colors.RESET}")
```

### After: Rich with Fallback

```python
def print_info(message: str) -> None:
    """정보 메시지를 출력합니다."""
    _logger().info(message)

    if config.USE_RICH_UI:
        from ui.rich_console import get_console
        console = get_console()
        console.print(f"[info]ℹ [INFO][/info] {message}")
    else:
        # Legacy ANSI fallback
        print(f"{Colors.BLUE}{Symbols.INFO} {message}{Colors.RESET}")
```

---

## Dependencies

### Current

```toml
[project]
dependencies = [
    "rich>=13.0.0",  # Already installed v14.1.0
    # ... other deps
]
```

**No new dependencies required!**

---

## Related Documentation

- **Specification**: `.spec/rich-ui-enhancement/spec.yaml`
- **Implementation Plan**: `.spec/rich-ui-enhancement/implementation-plan.md`
- **Tasks**:
  - TASK-009 (Phase 1)
  - TASK-010 (Phase 2)
  - TASK-011 (Phase 3)

---

## Questions?

For implementation details, see:
- Implementation Plan: `.spec/rich-ui-enhancement/implementation-plan.md`
- Spec: `.spec/rich-ui-enhancement/spec.yaml`
- Backlog: `.tasks/backlog.yaml`

---

**Last Updated**: 2025-11-11
**Status**: Planning Complete, Ready for Implementation
**Next Step**: Begin TASK-009 (Phase 1 - Core Infrastructure)
