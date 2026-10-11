# Trace: backlog.md - Approval decision memory / Console focus before operator input
"""Windows console prompts with a deadline and no background stdin threads."""

import msvcrt
import json
import subprocess
import sys
import time
from typing import List, Optional

from config import TimeoutConfig
from ui.rich_console import RichConsole
from ui.console_interface import activate_cmd_window
from utils.error_handler import setup_logger
from utils.wait_helpers import wait_for_poll_interval

logger = setup_logger(__name__)
console = RichConsole()


def get_timed_text_input(prompt: str, *, timeout: float) -> Optional[str]:
    """Read a composed console line; a bounded child owns the blocking read."""
    if timeout <= 0 or not sys.stdin.isatty():
        logger.warning("Native line input unavailable: %s", prompt)
        return None
    activate_cmd_window()
    console.console.print(prompt, end=": ", markup=False)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import json,sys; print(json.dumps(sys.stdin.readline().rstrip('\\r\\n')))",
            ],
            stdin=sys.stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
        )
        if result.returncode:
            logger.error("Native line reader failed: exit=%s", result.returncode)
            return None
        value = json.loads(result.stdout)
        if not isinstance(value, str):
            logger.warning("Native line reader returned an invalid value")
            return None
        return value.strip() or None
    except subprocess.TimeoutExpired:
        # run() kills and waits for the child, so no stdin reader survives.
        logger.warning("Native line input timed out after %s seconds", timeout)
        console.console.print()
        return None
    except (OSError, ValueError) as error:
        logger.error("Native line input failed: %s", error)
        return None


def get_timed_input(prompt: str, *, timeout: float) -> Optional[str]:
    """Return a line, or None on deadline/Escape/unavailable interactive stdin."""
    if timeout <= 0 or not sys.stdin.isatty():
        logger.warning("Interactive input unavailable or deadline expired: %s", prompt)
        return None
    activate_cmd_window()
    deadline = time.monotonic() + timeout
    console.console.print(prompt, end=": ", markup=False)
    characters: List[str] = []
    extended = False
    while time.monotonic() < deadline:
        if not msvcrt.kbhit():
            remaining = max(0.0, deadline - time.monotonic())
            wait_for_poll_interval(
                min(TimeoutConfig.CONDITION_WAIT_INTERVAL, remaining)
            )
            continue
        key = msvcrt.getwch()
        if extended:
            extended = False
        elif key in ("\x00", "\xe0"):
            extended = True
        elif key in ("\r", "\n"):
            console.console.print()
            return "".join(characters).strip()
        elif key in ("\x1b", "\x03"):
            logger.info("Operator cancelled input: %s", prompt)
            console.console.print()
            return None
        elif key == "\b":
            if characters:
                characters.pop()
                console.console.print("\b \b", end="", markup=False)
        elif key.isprintable():
            characters.append(key)
            console.console.print(key, end="", markup=False)
    logger.warning("Operator input timed out after %s seconds: %s", timeout, prompt)
    console.console.print()
    return None


def choose_timed_option(
    title: str, options: List[str], *, allow_manual: bool = False
) -> Optional[str]:
    """Choose a numbered option; empty string requests manual fallback."""
    if not options:
        return "" if allow_manual else None
    activate_cmd_window()
    console.print_menu(title, options)
    if allow_manual:
        console.print_info("0: 직접 지정")
    deadline = time.monotonic() + TimeoutConfig.USER_SELECTION_WAIT
    while time.monotonic() < deadline:
        value = get_timed_input(
            "번호 선택 (Esc: 건너뛰기)", timeout=deadline - time.monotonic()
        )
        if value is None:
            return None
        if allow_manual and value == "0":
            return ""
        try:
            return console.validate_selection(value, options)
        except ValueError as error:
            logger.info("Invalid operator selection: %s", error)
            console.print_warning(str(error))
    return None
