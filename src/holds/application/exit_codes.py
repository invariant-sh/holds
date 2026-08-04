"""Stable process exit codes for the Holds CLI."""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Public CLI exit status contract."""

    SUCCESS = 0
    USAGE = 2
    INVALID_SUITE = 10
    AGENT_FAILURE = 20
    GRADER_FAILURE = 30
    THRESHOLD_FAILURE = 40
    BASELINE_FAILURE = 50
    INCOMPATIBLE_BASELINE = 51
    RESILIENCE_FAILURE = 60
    INTERNAL = 70
