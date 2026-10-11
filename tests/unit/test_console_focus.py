# Trace: backlog.md - Console focus before operator input
"""Focus the owning console regardless of its window title."""

from unittest.mock import Mock

import pywinauto
import win32console

from ui import console_interface


def test_focus_uses_native_console_handle(monkeypatch):
    monkeypatch.setattr(win32console, "GetConsoleWindow", lambda: 123)
    application = Mock()
    factory = Mock(return_value=application)
    monkeypatch.setattr(pywinauto, "Application", factory)

    console_interface.activate_cmd_window()

    application.connect.assert_called_once_with(handle=123)
    application.connect.return_value.window.assert_called_once_with(handle=123)
    application.connect.return_value.window.return_value.set_focus.assert_called_once_with()


def test_title_fallback_without_native_console(monkeypatch):
    monkeypatch.setattr(win32console, "GetConsoleWindow", lambda: 0)
    application = Mock()
    monkeypatch.setattr(pywinauto, "Application", Mock(return_value=application))

    console_interface.activate_cmd_window()

    application.connect.assert_called_once_with(title="DocumentAutoClassifier")
    application.connect.return_value.window.return_value.set_focus.assert_called_once_with()


def test_native_focus_failure_uses_title_fallback(monkeypatch):
    monkeypatch.setattr(win32console, "GetConsoleWindow", lambda: 123)
    native = Mock()
    native.connect.return_value.window.return_value.set_focus.side_effect = OSError(
        "foreground denied"
    )
    fallback = Mock()
    monkeypatch.setattr(pywinauto, "Application", Mock(side_effect=[native, fallback]))

    console_interface.activate_cmd_window()

    fallback.connect.assert_called_once_with(title="DocumentAutoClassifier")
    fallback.connect.return_value.window.return_value.set_focus.assert_called_once_with()


def test_focus_failure_logs_warning_without_aborting(monkeypatch):
    monkeypatch.setattr(win32console, "GetConsoleWindow", lambda: 0)
    application = Mock()
    application.connect.side_effect = OSError("no console window")
    monkeypatch.setattr(pywinauto, "Application", Mock(return_value=application))
    logger = Mock()
    monkeypatch.setattr(console_interface, "_logger", lambda: logger)

    console_interface.activate_cmd_window()

    logger.warning.assert_called_once()
