# Trace:
#   spec_id: SPEC-rich-ui-enhancement-1
#   task_id: TASK-010
"""
Rich Console Wrapper Singleton

Provides a singleton wrapper around Rich library's Console with custom theme
and feature flag support for gradual migration from legacy ANSI mode.

Key features:
- Singleton pattern ensures single Console instance
- Custom theme for consistent styling
- Function flag (USE_RICH_UI) for backward compatibility
- Improved CJK character handling
- Type-safe message functions
- Panel and Table widgets for structured output
"""
import logging
from typing import Any, Iterator, List, Optional
from contextlib import contextmanager
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.markdown import Markdown
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.prompt import IntPrompt, Confirm


# Module-level singleton instance
_instance: Optional["RichConsole"] = None


class RichConsole:
    """
    Singleton wrapper for Rich Console with custom theme.

    Usage:
        console = RichConsole()
        console.print_info("Information message")
        console.print_success("Success message")
        console.clear_screen()
    """

    _initialized: bool

    def __new__(cls) -> "RichConsole":
        """Enforce singleton pattern."""
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self) -> None:
        """Initialize RichConsole (only runs once due to singleton)."""
        if self._initialized:
            return

        # Define custom theme
        self.theme = Theme(
            {
                "info": "blue",
                "success": "green",
                "warning": "yellow",
                "error": "red bold",
                "dim": "dim",
                "bold": "bold",
                "cyan": "cyan",
                "white": "white",
            }
        )

        # Create Console instance with theme
        self.console = Console(
            theme=self.theme,
            force_terminal=True,
            legacy_windows=False,  # Use modern Windows terminal support
        )

        self._initialized = True
        self._logger = logging.getLogger(__name__)
        self._logger.debug("RichConsole initialized")

    def print_info(self, message: str) -> None:
        """
        Print an informational message.

        Args:
            message: The message to display
        """
        self.console.print(f"[info]ℹ [INFO][/info] {message}")

    def print_success(self, message: str) -> None:
        """
        Print a success message.

        Args:
            message: The message to display
        """
        self.console.print(f"[success]✓ [OK][/success] {message}")

    def print_warning(self, message: str) -> None:
        """
        Print a warning message.

        Args:
            message: The message to display
        """
        self.console.print(f"[warning]⚠ [WARN][/warning] {message}")

    def print_error(self, message: str) -> None:
        """
        Print an error message.

        Args:
            message: The message to display
        """
        self.console.print(f"[error]✗ [ERROR][/error] {message}")

    def clear_screen(self) -> None:
        """Clear the terminal screen using Rich console."""
        self.console.clear()

    def clear(self) -> None:
        """Clear the terminal screen (alias for clear_screen)."""
        self.clear_screen()

    def print_document_info(self, title: str, doc_type: str = "문서") -> None:
        """
        Print document information in a styled panel.

        Args:
            title: The document title
            doc_type: The document type (default: "문서")
        """
        panel = Panel(
            title,
            title=f"📄 처리 중인 {doc_type}",
            border_style="cyan",
            padding=(0, 2),
        )
        self.console.print(panel)

    def print_numbered_list(
        self, items: List[str], start_index: int = 1, title: Optional[str] = None
    ) -> None:
        """
        Print a numbered list as a table.

        Args:
            items: List of items to display
            start_index: Starting number (default: 1)
            title: Optional table title
        """
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("번호", style="cyan", width=6)
        table.add_column("내용")

        for idx, item in enumerate(items):
            number = f"[{idx + start_index:02d}]"
            table.add_row(number, item)

        if title:
            panel = Panel(table, title=title, border_style="cyan")
            self.console.print(panel)
        else:
            self.console.print(table)

    def print_selection_menu(
        self,
        title: str,
        items: List[str],
        allow_skip: bool = False,
        skip_text: str = "목록에 없음",
    ) -> None:
        """
        Print a selection menu with numbered items in a Rich Panel + Table.

        Args:
            title: Menu title
            items: List of items to display
            allow_skip: Whether to show skip option (00)
            skip_text: Text for skip option (default: "목록에 없음")
        """
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("번호", style="cyan bold", width=6)
        table.add_column("내용", style="white")

        # Add main items
        for idx, item in enumerate(items, start=1):
            number = f"[{idx:02d}]"
            table.add_row(number, item)

        # Add skip option if allowed
        if allow_skip:
            table.add_row("[yellow][00][/yellow]", f"[yellow]{skip_text}[/yellow]")

        # Wrap in panel with title
        panel = Panel(
            table,
            title=f"[bold white]{title}[/bold white]",
            border_style="cyan",
            padding=(1, 2),
        )

        self.console.print()
        self.console.print(panel)
        self.console.print()

    @contextmanager
    def progress_bar(self, description: str = "Processing...") -> Iterator[Progress]:
        """
        Create a progress bar context manager for batch operations.

        Args:
            description: Description text for the progress bar

        Usage:
            with rich_console.progress_bar("Processing documents") as progress:
                task = progress.add_task(description, total=100)
                for i in range(100):
                    # Do work
                    progress.update(task, advance=1)
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        )
        with progress:
            yield progress

    def prompt_int(
        self,
        prompt: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        default: Optional[int] = None,
    ) -> int:
        """
        Prompt user for an integer input with validation.

        Args:
            prompt: The prompt message
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            default: Default value if user presses Enter

        Returns:
            int: The validated integer input
        """
        choices: Optional[List[str]] = None
        if min_value is not None and max_value is not None:
            choices = [str(choice) for choice in range(min_value, max_value + 1)]

        prompt_kwargs: dict[str, Any] = {
            "prompt": prompt,
            "console": self.console,
        }
        if choices is not None:
            prompt_kwargs["choices"] = choices
        if default is not None:
            prompt_kwargs["default"] = default

        return IntPrompt.ask(**prompt_kwargs)

    def confirm(self, prompt: str, default: bool = True) -> bool:
        """
        Prompt user for yes/no confirmation.

        Args:
            prompt: The confirmation message
            default: Default value (True for yes, False for no)

        Returns:
            bool: User's choice
        """
        return Confirm.ask(prompt, console=self.console, default=default)

    def print_final_result(self, success_count: int, total_count: int) -> None:
        """
        Print final processing results as a tree structure.

        Args:
            success_count: Number of successfully processed documents
            total_count: Total number of processed documents
        """
        # Calculate statistics
        failure_count = total_count - success_count
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0

        # Determine overall status
        if success_count == total_count:
            status = "[success]✓ 모든 문서 처리 완료[/success]"
            status_style = "green"
        elif success_count == 0:
            status = "[error]✗ 모든 문서 처리 실패[/error]"
            status_style = "red"
        else:
            status = "[warning]⚠ 일부 문서 처리 완료[/warning]"
            status_style = "yellow"

        # Create tree structure
        tree = Tree(f"📊 처리 결과", style=status_style, guide_style="dim")

        # Add status node
        tree.add(status)

        # Add statistics branch
        stats_branch = tree.add("📈 통계")
        stats_branch.add(f"[cyan]전체 문서:[/cyan] {total_count}건")
        stats_branch.add(f"[green]성공:[/green] {success_count}건")
        if failure_count > 0:
            stats_branch.add(f"[red]실패:[/red] {failure_count}건")
        stats_branch.add(f"[bold]성공률:[/bold] {success_rate:.1f}%")

        # Print the tree
        self.console.print()
        self.console.print(Panel(tree, title="🎉 처리 완료", border_style=status_style))
        self.console.print()

    def print_processing_summary(self, summary_data: dict) -> None:
        """
        Print processing summary with Markdown formatting.

        Args:
            summary_data: Dictionary containing summary information
                - total_processed: Total documents processed
                - success_count: Successfully processed documents
                - failure_count: Failed documents
                - elapsed_time: Time elapsed in seconds
                - Any additional custom fields
        """
        # Extract common fields with defaults
        total = summary_data.get("total_processed", 0)
        success = summary_data.get("success_count", 0)
        failure = summary_data.get("failure_count", 0)
        elapsed = summary_data.get("elapsed_time", 0)

        # Build markdown content
        markdown_text = f"""# 📋 처리 요약

## 기본 정보

- **전체 문서**: {total}건
- **성공**: {success}건
- **실패**: {failure}건
- **소요 시간**: {elapsed:.2f}초

## 성능 지표

- **평균 처리 시간**: {elapsed / total if total > 0 else 0:.2f}초/건
- **처리 속도**: {total / elapsed if elapsed > 0 else 0:.2f}건/초
- **성공률**: {success / total * 100 if total > 0 else 0:.1f}%
"""

        # Add custom fields if any
        custom_fields = {
            k: v
            for k, v in summary_data.items()
            if k
            not in ["total_processed", "success_count", "failure_count", "elapsed_time"]
        }

        if custom_fields:
            markdown_text += "\n## 추가 정보\n\n"
            for key, value in custom_fields.items():
                markdown_text += f"- **{key}**: {value}\n"

        # Render markdown
        markdown = Markdown(markdown_text)
        self.console.print(Panel(markdown, title="📊 상세 리포트", border_style="cyan"))

    def print(self, message: str = "") -> None:
        """
        Print a plain message without any styling.

        Args:
            message: The message to display (default: empty line)
        """
        self.console.print(message)

    def print_menu(self, title: str, items: List[str]) -> None:
        """
        Print a menu with numbered items (alias for print_selection_menu).

        Args:
            title: Menu title
            items: List of items to display
        """
        self.print_selection_menu(title, items)

    def print_separator(self, length: int = 50, char: str = "=") -> None:
        """
        Print a separator line.

        Args:
            length: Length of the separator (default: 50)
            char: Character to use for separation (default: "=")
        """
        self.console.print(f"[dim]{char * length}[/dim]")

    def get_input(self, prompt: str, default: str = "") -> str:
        """
        Get user input with a styled prompt.

        Args:
            prompt: The prompt message
            default: Default value if user just presses Enter

        Returns:
            str: User input
        """
        if default:
            prompt_text = f"[cyan]❯[/cyan] {prompt} (기본값: {default}): "
        else:
            prompt_text = f"[cyan]❯[/cyan] {prompt}: "

        self.console.print(prompt_text, end="")
        user_input = input()
        return user_input.strip() if user_input.strip() else default

    def print_header(self, title: str, width: int = 60) -> None:
        """
        Print a styled header.

        Args:
            title: Header title
            width: Width of the header (default: 60)
        """
        panel = Panel(
            title,
            style="bold white on blue",
            border_style="blue",
            padding=(0, 1),
        )
        self.console.print()
        self.console.print(panel)
        self.console.print()

    def validate_selection(self, user_input: str, options: List[str]) -> str:
        """
        Validate user input and return the selected option.

        This method centralizes input validation logic for menu selections,
        following the DRY principle.

        Args:
            user_input: User input (number as string)
            options: List of available options

        Returns:
            str: The selected option

        Raises:
            ValueError: If input is invalid or out of range
        """
        try:
            index = int(user_input) - 1
            if 0 <= index < len(options):
                return options[index]
            else:
                raise ValueError(f"1부터 {len(options)} 사이의 번호를 입력해주세요.")
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("올바른 숫자를 입력해주세요.") from e
            raise
