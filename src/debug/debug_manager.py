#!/usr/bin/env python3
"""
Unified Debug Manager for RPA Window Structure Analysis

This module consolidates all debugging functionality into a single, unified interface
that supports both interactive (human) and programmatic (AI) usage modes.
"""

import time
import logging
import io
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Union

from pywinauto import Application

# Ensure debug log directory exists
project_root = Path(__file__).parent.parent.parent
log_dir = project_root / "logs" / "debug"
log_dir.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


class UnifiedDebugManager:
    """통합된 디버그 관리자 - 대화형 및 프로그래매틱 모드 지원"""

    def __init__(
        self, app_title_patterns: Optional[List[str]] = None, interactive: bool = True
    ):
        """
        Initialize the unified debug manager

        Args:
            app_title_patterns: List of title patterns to search for
            interactive: Whether to run in interactive mode (for human use) or programmatic mode (for AI use)
        """
        if app_title_patterns is None:
            self.app_title_patterns = ["접수:", "전자결재"]
        else:
            self.app_title_patterns = app_title_patterns
        self.interactive = interactive
        self.app = None
        self.dlg = None

        # Setup logging for this session
        if not hasattr(logger, "handlers") or not logger.handlers:
            self._setup_logging()

    def _setup_logging(self) -> None:
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=(
                [
                    logging.FileHandler(
                        log_dir
                        / f'debug_session_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
                    ),
                    logging.StreamHandler(),
                ]
                if self.interactive
                else [
                    logging.FileHandler(
                        log_dir
                        / f'debug_session_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
                    )
                ]
            ),
        )

    def connect_to_app(self) -> bool:
        """
        Connect to the target application

        Returns:
            bool: True if connection successful, False otherwise
        """
        for pattern in self.app_title_patterns:
            try:
                self.app = Application(backend="win32").connect(
                    title_re=f".*{pattern}.*"
                )
                self.dlg = self.app.top_window()  # type: ignore[attr-defined]
                logger.info(
                    f"Successfully connected to application with pattern: {pattern}"
                )
                return True
            except Exception as e:
                logger.debug(f"Failed to connect with pattern '{pattern}': {e}")
                continue

        logger.error(
            f"Failed to connect to any application with patterns: {self.app_title_patterns}"
        )
        return False

    def get_window_structure(self, save_to_file: bool = True) -> str:
        """
        Get the complete window structure using print_control_identifiers()

        Args:
            save_to_file: Whether to save output to file

        Returns:
            str: The control identifiers output
        """
        if not self.dlg:
            logger.error("No dialog connected. Call connect_to_app() first.")
            return ""

        try:  # type: ignore[unreachable]
            logger.info("=== Getting window structure ===")

            # Capture the output by redirecting to a string
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            # Print control identifiers
            self.dlg.print_control_identifiers()

            # Restore stdout and get the output
            sys.stdout = old_stdout
            output = buffer.getvalue()

            # Print to console only in interactive mode
            if self.interactive:
                print(output)

            # Save to file if requested
            if save_to_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = log_dir / f"window_structure_{timestamp}.log"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"Window Structure Debug - {datetime.now()}\n")
                    f.write(f"Application patterns: {self.app_title_patterns}\n")
                    f.write(f"Current window title: {self.dlg.window_text()}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(output)
                logger.info(f"Window structure saved to: {filename}")

            return output

        except Exception as e:
            logger.error(f"Failed to get window structure: {e}")
            return ""

    def analyze_current_window(
        self, app_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Quick window analysis for programmatic use

        Args:
            app_patterns: Optional application patterns to override defaults

        Returns:
            Dict containing analysis results
        """
        try:
            if app_patterns:
                self.app_title_patterns = app_patterns

            # Connect to application
            if not self.connect_to_app():
                return {
                    "success": False,
                    "error": "Failed to connect to application",
                    "connected_app": None,
                    "window_structure": None,
                }

            # Get window structure
            window_structure = self.get_window_structure(save_to_file=True)

            return {
                "success": True,
                "connected_app": self.dlg.window_text() if self.dlg else None,
                "window_structure": window_structure,
                "analysis_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Window analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "connected_app": None,
                "window_structure": None,
            }

    def monitor_dialogs(
        self, duration: float = 30.0, interval: float = 1.0
    ) -> Union[None, List[Dict[str, Any]]]:
        """
        Monitor dialog changes over time

        Args:
            duration: Total monitoring duration in seconds
            interval: Monitoring interval in seconds

        Returns:
            None for interactive mode, List of dialogs for programmatic mode
        """
        if not self.dlg:
            logger.error("No dialog connected. Call connect_to_app() first.")
            return [] if not self.interactive else None

        logger.info(  # type: ignore[unreachable]
            f"Starting dialog monitoring for {duration} seconds (interval: {interval}s)"
        )
        start_time = time.time()
        iteration = 0
        dialogs_found = [] if not self.interactive else None

        while time.time() - start_time < duration:
            iteration += 1

            if self.interactive:
                logger.info(f"=== Monitoring iteration {iteration} ===")

            # Check if any dialogs exist
            dialogs = self._find_confirm_dialogs()
            if dialogs:
                logger.info(f"Found {len(dialogs)} dialog(s)")
                for i, dialog in enumerate(dialogs):
                    if self.interactive:
                        logger.info(f"Dialog {i+1} structure:")
                        self._print_dialog_structure(dialog)
                    else:
                        # Store dialog info for programmatic use
                        dialog_info = self._analyze_dialog(dialog, iteration)
                        dialogs_found.append(dialog_info)
            else:
                if self.interactive:
                    logger.info("No dialogs found")

            time.sleep(interval)

        logger.info("Dialog monitoring completed")
        return dialogs_found

    def _find_confirm_dialogs(self) -> List:
        """
        Find all confirmation dialogs

        Returns:
            List of dialog windows
        """
        dialogs = []
        try:
            # Look for windows with title '확인'
            confirm_dialogs = self.app.windows(title="확인", control_type="Window")  # type: ignore[attr-defined]
            dialogs.extend(confirm_dialogs)

            # Also look for any popup dialogs
            popup_dialogs = self.app.windows(control_type="Window", class_name="#32770")  # type: ignore[attr-defined]
            dialogs.extend(popup_dialogs)

        except Exception as e:
            logger.debug(f"Error finding dialogs: {e}")

        return dialogs

    def _print_dialog_structure(self, dialog: Any) -> None:
        """
        Print structure of a specific dialog (interactive mode)

        Args:
            dialog: Dialog window to analyze
        """
        try:
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            dialog.print_control_identifiers()

            sys.stdout = old_stdout
            output = buffer.getvalue()

            if self.interactive:
                print(output)

        except Exception as e:
            logger.error(f"Failed to print dialog structure: {e}")

    def _analyze_dialog(self, dialog: Any, iteration: int) -> Dict[str, Any]:
        """
        Analyze dialog for programmatic use

        Args:
            dialog: Dialog to analyze
            iteration: Monitoring iteration number

        Returns:
            Dict containing dialog analysis
        """
        try:
            dialog_info: Dict[str, Any] = {
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "title": getattr(dialog, "window_text", lambda: "Unknown")(),
                "class_name": getattr(dialog, "class_name", lambda: "Unknown")(),
                "rect": None,
                "text_content": None,
                "controls": [],
            }

            # Get position info
            try:
                rect = dialog.rectangle()
                dialog_info["rect"] = {
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                }
            except Exception:
                pass

            # Get text content
            try:
                dialog_info["text_content"] = self._get_dialog_text_safe(dialog)
            except Exception:
                pass

            # Get child controls info
            try:
                children = dialog.children()
                dialog_info["controls"] = [
                    {
                        "control_type": getattr(child, "element_info", {}).get(
                            "control_type", "Unknown"
                        ),
                        "title": getattr(child, "window_text", lambda: "")(),
                        "class_name": getattr(child, "class_name", lambda: "")(),
                    }
                    for child in children[:5]  # First 5 controls only
                ]
            except Exception:
                pass

            return dialog_info

        except Exception as e:
            logger.error(f"Failed to analyze dialog: {e}")
            return {
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

    def _get_dialog_text_safe(self, dialog: Any) -> str:
        """
        Safely extract dialog text

        Args:
            dialog: Dialog object

        Returns:
            str: Extracted text
        """
        text_methods = [
            lambda: dialog.window_text(),
            lambda: dialog.child_window(control_type="Text").window_text(),
            lambda: dialog.child_window(control_type="Static").window_text(),
        ]

        for method in text_methods:
            try:
                text = method()
                if text and text.strip():
                    return str(text)
            except Exception:
                continue

        return ""

    def find_circulation_completion_dialog(
        self, timeout: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """
        Find circulation completion dialog

        Args:
            timeout: Maximum wait time

        Returns:
            Dialog information if found, None otherwise
        """
        if not self.dlg:
            logger.error("No active connection.")
            return None

        start_time = time.time()  # type: ignore[unreachable]

        while time.time() - start_time < timeout:
            try:
                dialogs = self._find_confirm_dialogs()

                for dialog in dialogs:
                    text_content = self._get_dialog_text_safe(dialog)

                    # Check for circulation completion dialog keywords
                    if any(
                        keyword in text_content
                        for keyword in ["공람지정", "완료", "확인"]
                    ):
                        dialog_info = self._analyze_dialog(dialog, 0)
                        dialog_info["is_circulation_dialog"] = True
                        logger.info(
                            f"Found circulation completion dialog: {text_content[:50]}"
                        )
                        return dialog_info

            except Exception as e:
                logger.debug(f"Error searching for circulation dialog: {e}")

            time.sleep(0.1)

        logger.info("No circulation completion dialog found within timeout")
        return None

    def debug_circulation_completion_flow(self) -> None:
        """Debug the circulation completion flow with monitoring"""
        logger.info("=== Starting circulation completion flow debugging ===")

        # Step 1: Print current window structure
        logger.info("Step 1: Current window structure")
        self.get_window_structure()

        # Step 2: Wait for user action (only in interactive mode)
        if self.interactive:
            input("\nPress Enter after clicking the reception button...")
        else:
            logger.info("Non-interactive mode: skipping user input")

        # Step 3: Monitor for circulation completion dialog
        logger.info("Step 3: Monitoring for circulation completion dialog")
        self.monitor_dialogs(interval=0.5, duration=15.0)

        logger.info("=== Circulation completion flow debugging completed ===")

    def run_interactive_session(self) -> None:
        """Run interactive debugging session"""
        if not self.interactive:
            logger.warning("Interactive session called in non-interactive mode")
            return

        print("Unified Debug Manager - Interactive Mode")
        print("=" * 40)

        # Connect to application
        if not self.connect_to_app():
            print(
                "Failed to connect to application. Please ensure the application is running."
            )
            return

        while True:
            print("\nDebugging Options:")
            print("1. Print current window structure")
            print("2. Monitor dialog changes")
            print("3. Debug circulation completion flow")
            print("4. Find circulation completion dialog")
            print("5. Exit")

            choice = input("\nSelect option (1-5): ").strip()

            if choice == "1":
                self.get_window_structure()
            elif choice == "2":
                duration = float(
                    input("Enter monitoring duration (seconds, default 30): ") or "30"
                )
                interval = float(
                    input("Enter monitoring interval (seconds, default 1): ") or "1"
                )
                self.monitor_dialogs(duration=duration, interval=interval)
            elif choice == "3":
                self.debug_circulation_completion_flow()
            elif choice == "4":
                timeout = float(input("Enter timeout (seconds, default 5): ") or "5")
                dialog = self.find_circulation_completion_dialog(timeout=timeout)
                if dialog:
                    print(f"Found dialog: {dialog}")
                else:
                    print("No circulation completion dialog found")
            elif choice == "5":
                print("Exiting...")
                break
            else:
                print("Invalid option. Please try again.")


# Convenience functions for easy access


def create_debug_manager(
    interactive: bool = True, app_patterns: Optional[List[str]] = None
) -> UnifiedDebugManager:
    """
    Create a debug manager instance

    Args:
        interactive: Whether to run in interactive mode
        app_patterns: Optional application patterns

    Returns:
        UnifiedDebugManager instance
    """
    return UnifiedDebugManager(app_title_patterns=app_patterns, interactive=interactive)


def quick_window_analysis(app_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Quick window analysis convenience function

    Args:
        app_patterns: Optional application patterns

    Returns:
        Dict containing analysis results
    """
    manager = UnifiedDebugManager(app_title_patterns=app_patterns, interactive=False)
    return manager.analyze_current_window()


def monitor_circulation_dialogs(duration: float = 10.0) -> List[Dict[str, Any]]:
    """
    Monitor for circulation dialogs convenience function

    Args:
        duration: Monitoring duration

    Returns:
        List of detected dialogs
    """
    manager = UnifiedDebugManager(interactive=False)

    # Connect to application
    analysis = manager.analyze_current_window()
    if not analysis["success"]:
        logger.error("Failed to connect to application for monitoring")
        return []

    # Monitor dialogs
    result = manager.monitor_dialogs(duration=duration, interval=0.5)
    return result if result is not None else []


def run_interactive_debug() -> None:
    """Run interactive debugging session"""
    manager = UnifiedDebugManager(interactive=True)
    manager.run_interactive_session()


if __name__ == "__main__":
    run_interactive_debug()
