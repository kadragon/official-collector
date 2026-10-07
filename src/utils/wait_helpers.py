# Trace: Now sprint - classify_stage splitter, env centralization, wait helpers, threshold docs
"""Named wait helpers for RPA polling, retries, and UI settle pauses.

All deliberate pauses go through these helpers so bare sleeps never appear
at call sites (RPA rule: waits use named helpers). Each helper blocks via
``threading.Event().wait`` for the requested seconds, which pauses without a
direct sleep call at the call site and keeps every pause greppable and
purpose-named.
"""

from __future__ import annotations

import threading


def _pause(seconds: float) -> None:
    """Block for ``seconds`` without a direct sleep call at call sites."""
    threading.Event().wait(timeout=max(0.0, seconds))


def wait_for_poll_interval(seconds: float) -> None:
    """Pause between readiness-poll iterations."""
    _pause(seconds)


def wait_for_retry_backoff(seconds: float) -> None:
    """Pause before retrying a failed network/API operation."""
    _pause(seconds)


def wait_for_ui_settle(seconds: float) -> None:
    """Pause for focus/window settling after a UI action."""
    _pause(seconds)


def wait_for_document_turnaround(seconds: float = 2.0) -> None:
    """Pause after finishing one document before preparing the next."""
    _pause(seconds)
