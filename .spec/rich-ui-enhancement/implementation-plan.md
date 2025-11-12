<!-- Trace:
spec_id: SPEC-rich-ui-enhancement-1
task_id: TASK-009
-->

# Rich Library UI/UX Enhancement - Implementation Plan

## Overview

This document outlines the detailed implementation plan for migrating the terminal UI from ANSI escape codes to the Rich library.

## Current State Analysis

### Existing UI Components (`src/ui/console_interface.py`)

| Component | Current Implementation | Lines | Complexity |
|-----------|----------------------|-------|------------|
| Colors | ANSI escape codes | 32-44 | Low |
| Symbols | Plain text constants | 47-54 | Low |
| Text width calculation | Manual Unicode handling | 57-77 | High |
| Screen control | `clear_screen()` | 80-88 | Low |
| Separators | `draw_separator()` | 91-100 | Medium |
| Headers | `draw_header()` | 103-117 | Medium |
| Message functions | `print_info/success/warning/error()` | 125-146 | Low |
| Document info box | `print_document_info()` | 149-198 | High |
| Numbered lists | `print_numbered_list()` | 201-230 | High |
| Selection menu | `print_selection_menu()` | 233-254 | Medium |
| User input | `get_styled_input()` | 257-266 | Low |
| Result display | `print_final_result()` | 269-281 | Low |
| Input validation | `get_valid_selection()` | 297-307 | Low |
| Choice prompts | Multiple functions | 310-373 | Medium |
| ConsoleInterface class | Orchestration | 408-705 | High |

**Total LOC**: ~705 lines

### Pain Points

1. **Manual Unicode width calculation**: Lines 57-77 handle CJK characters manually
2. **Inconsistent spacing**: Box drawing requires careful padding calculation
3. **Limited validation**: User input validation is basic
4. **No progress feedback**: Batch operations lack visual progress
5. **Plain error display**: Exceptions shown as plain text
6. **Repetitive code**: Many formatting patterns repeated

## Phase 1: Core Infrastructure

### Goal
Replace ANSI primitives with Rich equivalents without changing behavior.

### Tasks

#### TASK-009-A: Create RichConsole Wrapper

**File**: `src/ui/rich_console.py` (new)

```python
"""
Rich Console Wrapper

Provides centralized Rich console instance and theme configuration.
"""

from typing import Optional
from rich.console import Console
from rich.theme import Theme

# Define custom theme
OFFICIAL_COLLECTOR_THEME = Theme({
    "info": "blue",
    "success": "green",
    "warning": "yellow",
    "error": "red bold",
    "dim": "dim",
    "highlight": "cyan",
    "title": "bold white",
    "doc_title": "bold cyan",
    "number": "cyan",
})

# Singleton console instance
_console: Optional[Console] = None

def get_console() -> Console:
    """Get or create the singleton Rich console instance."""
    global _console
    if _console is None:
        _console = Console(theme=OFFICIAL_COLLECTOR_THEME)
    return _console

def reset_console() -> None:
    """Reset console instance (for testing)."""
    global _console
    _console = None
```

**Tests**: `tests/unit/test_rich_console.py`
- Singleton behavior
- Theme application
- Reset functionality

#### TASK-009-B: Update Config for Feature Flag

**File**: `src/config.py`

Add configuration option:

```python
# UI Configuration
USE_RICH_UI: bool = os.getenv("USE_RICH_UI", "true").lower() == "true"
```

#### TASK-009-C: Migrate Message Functions

**File**: `src/ui/console_interface.py` (modify)

Replace:
```python
# Old
def print_info(message: str) -> None:
    _logger().info(message)
    print(f"{Colors.BLUE}{Symbols.INFO} {message}{Colors.RESET}")
```

With:
```python
# New
def print_info(message: str) -> None:
    _logger().info(message)
    if config.USE_RICH_UI:
        from ui.rich_console import get_console
        console = get_console()
        console.print(f"[info][INFO][/info] {message}")
    else:
        print(f"{Colors.BLUE}{Symbols.INFO} {message}{Colors.RESET}")
```

Apply to:
- `print_info()`
- `print_success()`
- `print_warning()`
- `print_error()`

#### TASK-009-D: Migrate Screen Control

Replace `clear_screen()`:

```python
def clear_screen() -> None:
    """Clear the screen."""
    if config.USE_RICH_UI:
        from ui.rich_console import get_console
        console = get_console()
        console.clear()
    else:
        # Legacy fallback
        try:
            if os.name == "nt":
                subprocess.run(["cmd", "/c", "cls"], check=True)
            else:
                subprocess.run(["clear"], check=True)
        except Exception:
            print("\n" * 50)
```

### Acceptance Criteria

- [ ] `RichConsole` singleton created and tested
- [ ] Config flag `USE_RICH_UI` added
- [ ] Message functions work with both Rich and legacy modes
- [ ] All existing tests pass with `USE_RICH_UI=true`
- [ ] All existing tests pass with `USE_RICH_UI=false`

---

## Phase 2: UI Components Enhancement

### Goal
Replace complex UI components with Rich widgets.

### Tasks

#### TASK-010-A: Migrate Document Info Box to Panel

**Before** (lines 149-198):
```python
def print_document_info(title: str, doc_type: str = "문서") -> None:
    # 60+ lines of manual box drawing
```

**After**:
```python
def print_document_info(title: str, doc_type: str = "문서") -> None:
    _logger().info(f"처리 중인 {doc_type}: {title}")

    if config.USE_RICH_UI:
        from rich.panel import Panel
        from ui.rich_console import get_console

        console = get_console()
        panel = Panel(
            title,
            title=f"[doc_title]처리 중인 {doc_type}[/doc_title]",
            border_style="white",
            padding=(0, 2),
        )
        console.print()
        console.print(panel)
        console.print()
    else:
        # Legacy implementation (keep for now)
        # ... existing code ...
```

**Benefits**:
- Automatic width calculation
- Proper CJK handling
- ~40 lines reduced to ~15

#### TASK-010-B: Migrate Numbered Lists to Table

**Before** (lines 201-230):
```python
def print_numbered_list(items: List[str], ...) -> None:
    # Manual formatting with word wrapping
```

**After**:
```python
def print_numbered_list(
    items: List[str],
    start_index: int = 1,
    highlight_color: str = "cyan"
) -> None:
    if config.USE_RICH_UI:
        from rich.table import Table
        from ui.rich_console import get_console

        console = get_console()
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("No", style=highlight_color, width=6)
        table.add_column("Item", overflow="fold")

        for idx, item in enumerate(items):
            number = f"[{idx + start_index:02d}]"
            table.add_row(number, item)

        console.print(table)
    else:
        # Legacy implementation
        # ... existing code ...
```

#### TASK-010-C: Add Progress Bar for Batch Operations

**File**: `src/main.py` (modify)

Add progress tracking to main loop:

```python
def run(self) -> None:
    # ... existing code ...

    if config.USE_RICH_UI:
        from rich.progress import Progress, SpinnerColumn, TextColumn
        from ui.rich_console import get_console

        console = get_console()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("문서 처리 중...", total=None)

            while True:
                # ... document processing ...
                progress.update(task, advance=1)
    else:
        # Legacy mode without progress
        while True:
            # ... existing code ...
```

#### TASK-010-D: Migrate Input Prompts

Replace `get_styled_input()` and validation:

```python
def get_user_choice_from_list(
    options: List[str],
    allow_skip: bool = False
) -> Tuple[SelectionResult, Optional[str]]:

    if config.USE_RICH_UI:
        from rich.prompt import IntPrompt
        from ui.rich_console import get_console

        console = get_console()

        while True:
            try:
                if allow_skip:
                    selection = IntPrompt.ask(
                        "[highlight]→[/highlight] 번호를 선택하세요",
                        console=console,
                        choices=[str(i) for i in range(0, len(options) + 1)],
                    )
                    if selection == 0:
                        return SelectionResult.SKIPPED, None
                else:
                    selection = IntPrompt.ask(
                        "[highlight]→[/highlight] 번호를 선택하세요",
                        console=console,
                        choices=[str(i) for i in range(1, len(options) + 1)],
                    )

                return SelectionResult.SELECTED, options[selection - 1]

            except ValueError:
                console.print("[error]유효하지 않은 입력입니다.[/error]")
    else:
        # Legacy implementation
        # ... existing code ...
```

#### TASK-010-E: Integrate Rich Logging

**File**: `src/utils/error_handler.py` (modify)

```python
def setup_logger(
    name: str,
    console_output: bool = True,
    file_output: bool = True
) -> logging.Logger:
    logger = logging.getLogger(name)

    # ... existing code ...

    if console_output:
        if config.USE_RICH_UI:
            from rich.logging import RichHandler
            from ui.rich_console import get_console

            console_handler = RichHandler(
                console=get_console(),
                rich_tracebacks=True,
                tracebacks_show_locals=True,
            )
        else:
            console_handler = logging.StreamHandler()

        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # ... rest of existing code ...
```

### Acceptance Criteria

- [ ] `print_document_info()` uses Rich Panel
- [ ] `print_numbered_list()` uses Rich Table
- [ ] Progress bar appears during batch processing
- [ ] Input prompts use Rich validation
- [ ] RichHandler integrates with logger
- [ ] CJK character alignment verified
- [ ] All tests updated and passing

---

## Phase 3: Advanced Features

### Goal
Add advanced visualization and reporting capabilities.

### Tasks

#### TASK-011-A: Add Live Status Updates

**File**: `src/services/document_processor.py` (modify)

```python
def process_task_card_matching(self, title: str) -> Optional[str]:
    if config.USE_RICH_UI:
        from rich.live import Live
        from rich.table import Table
        from ui.rich_console import get_console

        console = get_console()

        def make_status_table(stage: str) -> Table:
            table = Table(show_header=False, box=None)
            table.add_column("Status", style="cyan")
            table.add_row(f"문서: {title}")
            table.add_row(f"단계: {stage}")
            return table

        with Live(make_status_table("시작"), console=console, refresh_per_second=4):
            # Update stages as processing progresses
            # ... processing logic ...
    else:
        # Legacy mode
        # ... existing code ...
```

#### TASK-011-B: Add Tree View for Results

**File**: `src/ui/console_interface.py` (modify)

```python
def print_final_result(self, success_count: int, total_count: int) -> None:
    _logger().info(f"처리 완료 - 성공: {success_count}/{total_count}")

    if config.USE_RICH_UI:
        from rich.tree import Tree
        from rich.panel import Panel
        from ui.rich_console import get_console

        console = get_console()

        # Create result tree
        tree = Tree(f"[title]처리 결과[/title]")
        tree.add(f"[success]✓ 성공: {success_count}[/success]")
        if total_count > success_count:
            tree.add(f"[error]✗ 실패: {total_count - success_count}[/error]")
        tree.add(f"[dim]총 처리: {total_count}[/dim]")

        panel = Panel(tree, border_style="green" if success_count == total_count else "yellow")
        console.print()
        console.print(panel)
        console.print()
    else:
        # Legacy implementation
        # ... existing code ...
```

#### TASK-011-C: Enable Rich Tracebacks

**File**: `src/main.py` (top level)

```python
if __name__ == "__main__":
    if config.USE_RICH_UI:
        from rich.traceback import install
        install(show_locals=True, width=100, word_wrap=True)

    # ... rest of main ...
```

#### TASK-011-D: Optional Markdown Reports

**File**: `src/ui/console_interface.py` (new method)

```python
def print_processing_summary(
    self,
    reception_count: int,
    card_count: int,
    errors: List[str],
) -> None:
    if not config.USE_RICH_UI:
        return  # Skip in legacy mode

    from rich.markdown import Markdown
    from ui.rich_console import get_console

    console = get_console()

    report = f"""
# 처리 요약 보고서

## 통계
- **접수 문서**: {reception_count}건
- **과제 카드**: {card_count}건

## 오류 내역
{"".join(f"- {err}\n" for err in errors) if errors else "_오류 없음_"}
    """

    md = Markdown(report)
    console.print(md)
```

### Acceptance Criteria

- [ ] Live updates work during processing
- [ ] Tree view displays final results
- [ ] Rich tracebacks enabled globally
- [ ] Optional markdown reports functional
- [ ] Performance within 5% of baseline
- [ ] User testing completed with positive feedback

---

## Testing Strategy

### Unit Tests

**New test files**:
- `tests/unit/test_rich_console.py` - Console singleton
- `tests/unit/test_rich_ui_components.py` - Rich widget wrappers

**Modified test files**:
- `tests/unit/test_console_interface.py` - Parametrize for Rich/legacy modes

### Integration Tests

- Test complete workflow with `USE_RICH_UI=true`
- Test complete workflow with `USE_RICH_UI=false`
- Verify visual output in both modes

### Visual Regression Tests

Create snapshots for:
- Document info panels
- Selection menus
- Progress bars
- Final result trees

### Performance Tests

Benchmark:
- Time to render 100 document info panels
- Memory usage during batch processing
- Startup time with Rich vs legacy

---

## Migration Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: Core Infrastructure | 2 days | Day 1 | Day 2 |
| Phase 2: UI Components | 3 days | Day 3 | Day 5 |
| Phase 3: Advanced Features | 2 days | Day 6 | Day 7 |
| Testing & Stabilization | 2 days | Day 8 | Day 9 |
| Documentation & Cleanup | 1 day | Day 10 | Day 10 |

**Total**: 10 working days

---

## Rollback Plan

If critical issues arise:

1. Set `USE_RICH_UI=false` in config
2. Legacy ANSI mode remains functional
3. No data loss or processing interruption
4. Fix Rich implementation offline
5. Re-enable after validation

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test coverage | ≥90% | pytest --cov |
| Performance | ≤5% regression | Benchmark suite |
| CJK alignment | 100% correct | Visual inspection |
| User satisfaction | ≥4/5 rating | User survey |
| Code reduction | ≥20% LOC | git diff --stat |

---

## References

- Rich documentation: https://rich.readthedocs.io/
- Current UI implementation: `src/ui/console_interface.py`
- Related specs: `.spec/core-automation/`, `.spec/performance-observability/`
