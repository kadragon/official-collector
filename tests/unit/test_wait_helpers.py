"""
Unit tests for the named wait helpers (backlog.md Now).

Every blocking wait in src/ routes through these helpers so sleeps stay
auditable in one place. Tests use tiny real delays to prove each helper
actually waits the requested duration.
"""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from utils.wait_helpers import (
    backoff,
    monitor_tick,
    pace,
    pause_between_documents,
    poll,
    settle,
)


@pytest.mark.parametrize(
    "helper",
    [settle, poll, backoff, pause_between_documents, monitor_tick, pace],
)
def test_each_helper_waits_the_requested_duration(helper):
    start = time.time()
    helper(0.02)
    assert time.time() - start >= 0.015
