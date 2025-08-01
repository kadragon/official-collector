#!/usr/bin/env python3
"""
Window Structure Debugging Tool using pywinauto's print_control_identifiers()

This tool helps debug window structure and control identification for RPA automation.
It's specifically designed to analyze the window structure during the circulation completion process.
"""

import time
import logging
import os
from pathlib import Path
from datetime import datetime
from pywinauto import Application
from pywinauto.findbestmatch import MatchError

# Ensure debug log directory exists (프로젝트 루트 기준)
project_root = Path(__file__).parent.parent  # src 폴더의 상위 폴더 (프로젝트 루트)
log_dir = project_root / 'logs' / 'debug'
log_dir.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            log_dir / f'debug_window_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WindowStructureDebugger:
    """창 구조 디버깅을 위한 클래스"""

    def __init__(self, app_title_patterns=None, interactive=True):
        """
        Initialize the debugger

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

    def connect_to_app(self) -> bool:
        """
        Connect to the target application

        Returns:
            bool: True if connection successful, False otherwise
        """
        for pattern in self.app_title_patterns:
            try:
                # Try to connect to existing application with current pattern
                self.app = Application(backend="win32").connect(
                    title_re=f".*{pattern}.*")
                self.dlg = self.app.top_window()
                logger.info(
                    f"Successfully connected to application with pattern: {pattern}")
                return True
            except Exception as e:
                logger.debug(
                    f"Failed to connect with pattern '{pattern}': {e}")
                continue

        logger.error(
            f"Failed to connect to any application with patterns: {self.app_title_patterns}")
        return False

    def print_window_structure(self, save_to_file=True) -> str:
        """
        Print the complete window structure using print_control_identifiers()

        Args:
            save_to_file: Whether to save output to file

        Returns:
            str: The control identifiers output
        """
        if not self.dlg:
            logger.error("No dialog connected. Call connect_to_app() first.")
            return ""

        try:
            logger.info("=== Printing window structure ===")

            # Capture the output by redirecting to a string
            import io
            import sys

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
                # 프로젝트 루트 기준으로 debug 디렉토리 설정
                project_root = Path(__file__).parent.parent
                debug_dir = project_root / 'logs' / 'debug'
                debug_dir.mkdir(parents=True, exist_ok=True)
                filename = debug_dir / f"window_structure_{timestamp}.log"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Window Structure Debug - {datetime.now()}\n")
                    f.write(
                        f"Application patterns: {self.app_title_patterns}\n")
                    f.write(
                        f"Current window title: {self.dlg.window_text()}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(output)
                logger.info(f"Window structure saved to: {filename}")

            return output

        except Exception as e:
            logger.error(f"Failed to print window structure: {e}")
            return ""

    def monitor_dialog_changes(self, interval=1.0, duration=30.0):
        """
        Monitor dialog changes over time

        Args:
            interval: Monitoring interval in seconds
            duration: Total monitoring duration in seconds
        """
        if not self.dlg:
            logger.error("No dialog connected. Call connect_to_app() first.")
            return

        logger.info(
            f"Starting dialog monitoring for {duration} seconds (interval: {interval}s)")
        start_time = time.time()
        iteration = 0

        while time.time() - start_time < duration:
            iteration += 1
            logger.info(f"=== Monitoring iteration {iteration} ===")

            # Check if any dialogs exist
            dialogs = self._find_confirm_dialogs()
            if dialogs:
                logger.info(f"Found {len(dialogs)} dialog(s)")
                for i, dialog in enumerate(dialogs):
                    logger.info(f"Dialog {i+1} structure:")
                    self._print_dialog_structure(dialog)
            else:
                logger.info("No dialogs found")

            time.sleep(interval)

        logger.info("Dialog monitoring completed")

    def _find_confirm_dialogs(self) -> list:
        """
        Find all confirmation dialogs

        Returns:
            list: List of dialog windows
        """
        dialogs = []
        try:
            # Look for windows with title '확인'
            confirm_dialogs = self.app.windows(
                title='확인', control_type='Window')
            dialogs.extend(confirm_dialogs)

            # Also look for any popup dialogs
            popup_dialogs = self.app.windows(
                control_type='Window', class_name='#32770')
            dialogs.extend(popup_dialogs)

        except Exception as e:
            logger.debug(f"Error finding dialogs: {e}")

        return dialogs

    def _print_dialog_structure(self, dialog):
        """
        Print structure of a specific dialog

        Args:
            dialog: Dialog window to analyze
        """
        try:
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            dialog.print_control_identifiers()

            sys.stdout = old_stdout
            output = buffer.getvalue()

            print(output)

        except Exception as e:
            logger.error(f"Failed to print dialog structure: {e}")

    def debug_circulation_completion_flow(self):
        """
        Debug the circulation completion flow by monitoring dialogs
        """
        logger.info("=== Starting circulation completion flow debugging ===")

        # Step 1: Print current window structure
        logger.info("Step 1: Current window structure")
        self.print_window_structure()

        # Step 2: Wait for user to click reception button (only in interactive mode)
        if self.interactive:
            input("\nPress Enter after clicking the reception button...")
        else:
            logger.info("Non-interactive mode: skipping user input")

        # Step 3: Monitor for circulation completion dialog
        logger.info("Step 3: Monitoring for circulation completion dialog")
        self.monitor_dialog_changes(interval=0.5, duration=15.0)

        logger.info("=== Circulation completion flow debugging completed ===")


def main():
    """Main function for debugging"""
    print("Window Structure Debugging Tool")
    print("=" * 40)

    # Initialize debugger
    debugger = WindowStructureDebugger()

    # Connect to application
    if not debugger.connect_to_app():
        print("Failed to connect to application. Please ensure the application is running.")
        return

    while True:
        print("\nDebugging Options:")
        print("1. Print current window structure")
        print("2. Monitor dialog changes")
        print("3. Debug circulation completion flow")
        print("4. Exit")

        choice = input("\nSelect option (1-4): ").strip()

        if choice == '1':
            debugger.print_window_structure()
        elif choice == '2':
            duration = float(
                input("Enter monitoring duration (seconds, default 30): ") or "30")
            interval = float(
                input("Enter monitoring interval (seconds, default 1): ") or "1")
            debugger.monitor_dialog_changes(
                interval=interval, duration=duration)
        elif choice == '3':
            debugger.debug_circulation_completion_flow()
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
