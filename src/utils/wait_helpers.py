# Trace: backlog.md Now — named wait helpers (central sleep owner)
"""Named wait helpers for all blocking waits in src/.

Every blocking pause in src/ routes through this module so that waits stay
auditable in exactly one place (no direct sleep call sites may remain
outside this module — enforced by the backlog item's search check).
Callers pass an explicit duration from ``config.TimeoutConfig`` —
this module intentionally takes no config dependency itself, so importing it
can never create an import cycle.

Pick the helper by intent:

- :func:`settle` — brief UI-settle pause after focus/click actions.
- :func:`poll` — one polling-loop interval while waiting on an element.
- :func:`backoff` — computed retry/backoff delay (quota, network, COM).
- :func:`pause_between_documents` — operator-visible transition pause.
- :func:`monitor_tick` — debug-monitor loop tick.
- :func:`pace` — rate-limit-friendly pacing pause between API batches.
"""

from __future__ import annotations

from time import sleep as _platform_sleep


def settle(delay: float) -> None:
    """Pause briefly so the UI settles after a focus/click action."""
    _platform_sleep(delay)


def poll(interval: float) -> None:
    """Wait one polling interval before re-checking an element/condition."""
    _platform_sleep(interval)


def backoff(wait_time: float) -> None:
    """Wait out a computed retry/backoff delay."""
    _platform_sleep(wait_time)


def pause_between_documents(delay: float) -> None:
    """Operator-visible pause while the next document is prepared."""
    _platform_sleep(delay)


def monitor_tick(interval: float) -> None:
    """Wait one debug-monitor loop tick."""
    _platform_sleep(interval)


def pace(delay: float) -> None:
    """Rate-limit-friendly pacing pause between API batches."""
    _platform_sleep(delay)
