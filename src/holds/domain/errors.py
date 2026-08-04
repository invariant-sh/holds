"""Domain errors for Holds."""

from __future__ import annotations


class HoldsError(Exception):
    """Base error for all Holds failures."""


class SuiteValidationError(HoldsError):
    """Raised when a suite file is invalid or unsupported."""


class AgentExecutionError(HoldsError):
    """Raised when the agent process fails before producing a usable result."""


class AgentTimeoutError(AgentExecutionError):
    """Raised when the agent process exceeds its timeout."""


class MissingResultArtifactError(AgentExecutionError):
    """Raised when the declared result artifact is missing or invalid."""


class GraderError(HoldsError):
    """Raised when a grader cannot evaluate an output."""


class ThresholdFailedError(HoldsError):
    """Raised when configured absolute thresholds are breached."""


class BaselineError(HoldsError):
    """Raised for baseline promotion or comparison failures."""


class IncompatibleBaselineError(BaselineError):
    """Raised when a candidate run cannot be compared to a baseline."""


class ResilienceError(HoldsError):
    """Raised when optional resilience (Maul) integration fails."""
