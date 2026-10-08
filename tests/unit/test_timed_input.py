# Trace: backlog.md - Approval decision memory / Assigned reuse
"""Bounded console input must not leave background stdin readers behind."""

from collections import deque
from types import SimpleNamespace

import pytest

from utils import timed_input
from config import TimeoutConfig


@pytest.fixture(autouse=True)
def console_focus(monkeypatch):
    from unittest.mock import Mock

    focus = Mock()
    monkeypatch.setattr(timed_input, "activate_cmd_window", focus)
    return focus


def test_raw_input_focuses_console_before_reading(
    keyboard_io, console_focus, monkeypatch
):
    keys, _ = keyboard_io
    keys.append("\r")

    def read_key():
        console_focus.assert_called_once_with()
        return keys.popleft()

    monkeypatch.setattr(timed_input.msvcrt, "getwch", read_key)
    assert timed_input.get_timed_input("done", timeout=60.0) == ""


def test_native_input_focuses_console_before_reader(console_focus, monkeypatch):
    monkeypatch.setattr(timed_input.sys, "stdin", SimpleNamespace(isatty=lambda: True))

    def read_line(*args, **kwargs):
        console_focus.assert_called_once_with()
        return SimpleNamespace(returncode=0, stdout='"operator"')

    monkeypatch.setattr(timed_input.subprocess, "run", read_line)
    assert timed_input.get_timed_text_input("name", timeout=60.0) == "operator"


@pytest.fixture
def keyboard_io(monkeypatch):
    keys = deque()
    clock = [0.0]
    monkeypatch.setattr(timed_input.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(timed_input.msvcrt, "kbhit", lambda: bool(keys))
    monkeypatch.setattr(timed_input.msvcrt, "getwch", keys.popleft)
    monkeypatch.setattr(timed_input.time, "monotonic", lambda: clock[0])

    def advance(seconds):
        clock[0] += seconds

    monkeypatch.setattr(timed_input, "wait_for_poll_interval", advance)
    return keys, clock


def test_enter_finishes_immediately(keyboard_io):
    keys, clock = keyboard_io
    keys.extend("\r")
    assert timed_input.get_timed_input("done", timeout=60.0) == ""
    assert clock[0] == 0.0


def test_editing_and_extended_keys(keyboard_io):
    keys, _ = keyboard_io
    keys.extend(["1", "2", "\b", "\xe0", "K", "3", "\r"])
    assert timed_input.get_timed_input("pick", timeout=60.0) == "13"


def test_input_expires_within_one_minute(keyboard_io):
    _, clock = keyboard_io
    assert timed_input.get_timed_input("done", timeout=60.0) is None
    assert 60.0 <= clock[0] <= 60.0 + TimeoutConfig.CONDITION_WAIT_INTERVAL


def test_redirected_stdin_never_blocks(monkeypatch):
    monkeypatch.setattr(timed_input.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert timed_input.get_timed_input("done", timeout=60.0) is None


def test_escape_cancels(keyboard_io):
    keys, _ = keyboard_io
    keys.append("\x1b")
    assert timed_input.get_timed_input("done", timeout=60.0) is None


def test_invalid_menu_inputs_do_not_restart_deadline(keyboard_io, monkeypatch):
    keys, clock = keyboard_io
    keys.extend(["x", "\r", "9", "\r"])
    monkeypatch.setattr(timed_input, "activate_cmd_window", lambda: None)
    assert timed_input.choose_timed_option("pick", ["Kim"]) is None
    assert 60.0 <= clock[0] <= 60.0 + TimeoutConfig.CONDITION_WAIT_INTERVAL


def test_menu_manual_fallback_is_distinct_from_timeout(keyboard_io, monkeypatch):
    keys, _ = keyboard_io
    keys.extend(["0", "\r"])
    monkeypatch.setattr(timed_input, "activate_cmd_window", lambda: None)
    assert timed_input.choose_timed_option("pick", ["Kim"], allow_manual=True) == ""


def test_native_text_input_preserves_composed_korean(monkeypatch):
    import json
    from unittest.mock import Mock

    monkeypatch.setattr(timed_input.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    run = Mock(return_value=SimpleNamespace(returncode=0, stdout=json.dumps("강동욱")))
    monkeypatch.setattr(timed_input.subprocess, "run", run)
    monkeypatch.setattr(
        timed_input.msvcrt, "getwch", lambda: pytest.fail("raw key input")
    )
    assert timed_input.get_timed_text_input("name", timeout=60.0) == "강동욱"
    assert run.call_args.kwargs["timeout"] == 60.0
    assert run.call_args.kwargs["stdin"] is timed_input.sys.stdin


def test_native_text_timeout_returns_without_a_reader(monkeypatch):
    monkeypatch.setattr(timed_input.sys, "stdin", SimpleNamespace(isatty=lambda: True))

    def timeout(*args, **kwargs):
        raise timed_input.subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(timed_input.subprocess, "run", timeout)
    assert timed_input.get_timed_text_input("name", timeout=60.0) is None
