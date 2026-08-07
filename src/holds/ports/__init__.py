"""Ports (protocols) for injectable dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from holds.domain.models import (
    AttemptResult,
    Baseline,
    GraderEvidence,
    GraderSpec,
    RunResult,
    Suite,
    TaskSpec,
)


@dataclass(frozen=True, slots=True)
class AgentLaunchRequest:
    """Inputs provided to the agent process for one attempt."""

    command: str
    working_directory: Path
    result_path: Path
    input_path: Path
    input_payload: dict[str, Any]
    task_id: str
    attempt_id: str
    timeout_seconds: float
    seed: int | None
    env: dict[str, str]


@dataclass(frozen=True, slots=True)
class AgentLaunchResult:
    """Raw process outcome before grading."""

    exit_code: int
    duration_ms: int
    timed_out: bool
    stdout: str
    stderr: str
    output: dict[str, Any] | None
    artifact_error: str | None


class AgentRunner(Protocol):
    """Executes one agent attempt and collects the result artifact."""

    def run(self, request: AgentLaunchRequest) -> AgentLaunchResult:
        """Run the agent command for a single attempt."""


class Grader(Protocol):
    """Evaluates one aspect of an agent output."""

    @property
    def version_tag(self) -> str:
        """Stable grader identity used in reports and baselines."""

    def grade(
        self,
        *,
        spec: GraderSpec,
        output: dict[str, Any],
        expected: dict[str, Any],
        suite_dir: Path,
    ) -> GraderEvidence:
        """Return structured evidence for one grader invocation."""


class ArtifactStore(Protocol):
    """Persists run reports and baselines."""

    def write_run(self, path: Path, run: RunResult) -> Path:
        """Write a run report atomically."""

    def read_run(self, path: Path) -> RunResult:
        """Load a run report."""

    def write_baseline(self, path: Path, baseline: Baseline) -> Path:
        """Write a baseline atomically without silent overwrite."""

    def read_baseline(self, path: Path) -> Baseline:
        """Load a baseline."""


class Clock(Protocol):
    """Provides timestamps for reports."""

    def now_iso(self) -> str:
        """Return an ISO-8601 UTC timestamp."""


class IdFactory(Protocol):
    """Creates stable-enough identifiers for runs and attempts."""

    def run_id(self) -> str:
        """Create a run identifier."""

    def attempt_id(self, task_id: str, index: int) -> str:
        """Create an attempt identifier."""


@dataclass(frozen=True, slots=True)
class ResilienceRequest:
    """Optional Maul adversity configuration for a task attempt."""

    scenarios: tuple[str, ...]
    config_path: Path | None
    repeats: int
    seed: int | None


@dataclass(frozen=True, slots=True)
class ResilienceOutcome:
    """Evidence attached when a task runs under injected faults."""

    report_path: Path | None
    notes: str | None = None


class ResilienceRunner(Protocol):
    """Optional adapter that runs a task under Maul conditions."""

    def prepare(self, request: ResilienceRequest) -> ResilienceOutcome:
        """Prepare adversity conditions before agent execution."""

    def collect(self, request: ResilienceRequest) -> ResilienceOutcome:
        """Collect resilience evidence after agent execution."""


class SuiteLoader(Protocol):
    """Loads and validates a suite document."""

    def load(self, path: Path) -> Suite:
        """Parse and validate a suite file."""


class ApplicationRevisionProvider(Protocol):
    """Resolves the application revision under test."""

    def revision(self) -> str | None:
        """Return a git revision or None when unavailable."""


# Re-export typing helpers used by application services.
__all__ = [
    "AgentLaunchRequest",
    "AgentLaunchResult",
    "AgentRunner",
    "ApplicationRevisionProvider",
    "ArtifactStore",
    "AttemptResult",
    "Baseline",
    "Clock",
    "Grader",
    "GraderEvidence",
    "GraderSpec",
    "IdFactory",
    "ResilienceOutcome",
    "ResilienceRequest",
    "ResilienceRunner",
    "RunResult",
    "Suite",
    "SuiteLoader",
    "TaskSpec",
]
