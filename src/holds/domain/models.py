"""Immutable domain models for suites, attempts, runs, and baselines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

GraderType = Literal["exact", "exact_field", "json_schema", "python"]
AttemptStatus = Literal[
    "passed",
    "failed",
    "agent_error",
    "timeout",
    "missing_artifact",
    "grader_error",
]
MaulExpectedOutcome = Literal["task_complete", "safe_degradation"]


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Absolute quality gates for a task or suite."""

    pass_rate_gte: float | None = None
    schema_valid_rate_gte: float | None = None
    max_regression_points: float | None = None

    def __post_init__(self) -> None:
        for name in ("pass_rate_gte", "schema_valid_rate_gte"):
            value = getattr(self, name)
            if value is not None and not 0.0 <= value <= 1.0:
                msg = f"{name} must be between 0.0 and 1.0 inclusive"
                raise ValueError(msg)
        if self.max_regression_points is not None and self.max_regression_points < 0.0:
            msg = "max_regression_points must be >= 0.0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class GraderSpec:
    """Named grader configuration from a suite."""

    type: GraderType
    id: str | None = None
    equals: Any = None
    path: str | None = None
    schema: str | dict[str, Any] | None = None
    callable: str | None = None
    version: str = "1"


@dataclass(frozen=True, slots=True)
class MaulCondition:
    """Optional adversity condition attached to a task."""

    scenarios: tuple[str, ...] = ()
    repeats: int | None = None
    config: str | None = None
    expected_outcome: MaulExpectedOutcome = "task_complete"

    def __post_init__(self) -> None:
        if self.repeats is not None and self.repeats < 1:
            msg = "maul.repeats must be >= 1"
            raise ValueError(msg)
        if self.expected_outcome not in {"task_complete", "safe_degradation"}:
            msg = "maul.expected_outcome must be task_complete or safe_degradation"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """One evaluable task in a suite."""

    id: str
    input: dict[str, Any]
    expected: dict[str, Any] = field(default_factory=dict)
    graders: tuple[GraderSpec, ...] = ()
    thresholds: Thresholds = field(default_factory=Thresholds)
    repeats: int | None = None
    timeout_seconds: float | None = None
    maul: MaulCondition | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            msg = "task id must be non-empty"
            raise ValueError(msg)
        if self.repeats is not None and self.repeats < 1:
            msg = "task repeats must be >= 1"
            raise ValueError(msg)
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            msg = "task timeout_seconds must be > 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class AgentSpec:
    """How Holds launches and collects output from the agent under test."""

    command: str
    result_path: str
    working_directory: str | None = None

    def __post_init__(self) -> None:
        if not self.command.strip():
            msg = "agent.command must be non-empty"
            raise ValueError(msg)
        if not self.result_path.strip():
            msg = "agent.result_path must be non-empty"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class SuiteDefaults:
    """Suite-wide defaults applied when a task omits an override."""

    repeats: int = 1
    timeout_seconds: float = 90.0
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.repeats < 1:
            msg = "defaults.repeats must be >= 1"
            raise ValueError(msg)
        if self.timeout_seconds <= 0:
            msg = "defaults.timeout_seconds must be > 0"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Suite:
    """Versioned, declarative evaluation suite."""

    version: int
    agent: AgentSpec
    defaults: SuiteDefaults
    tasks: tuple[TaskSpec, ...]
    thresholds: Thresholds = field(default_factory=Thresholds)
    source_path: str | None = None
    content_hash: str = ""

    def __post_init__(self) -> None:
        if self.version != 1:
            msg = f"unsupported suite version: {self.version}"
            raise ValueError(msg)
        if not self.tasks:
            msg = "suite must declare at least one task"
            raise ValueError(msg)
        ids = [task.id for task in self.tasks]
        if len(ids) != len(set(ids)):
            msg = "task ids must be unique"
            raise ValueError(msg)

    def repeats_for(self, task: TaskSpec) -> int:
        """Resolve effective repeat count for a task."""
        if task.repeats is not None:
            return task.repeats
        if task.maul is not None and task.maul.repeats is not None:
            return task.maul.repeats
        return self.defaults.repeats

    def timeout_for(self, task: TaskSpec) -> float:
        """Resolve effective timeout for a task."""
        if task.timeout_seconds is not None:
            return task.timeout_seconds
        return self.defaults.timeout_seconds


@dataclass(frozen=True, slots=True)
class GraderEvidence:
    """Structured evidence produced by one grader evaluation."""

    grader_id: str
    grader_type: GraderType
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AttemptResult:
    """Outcome of a single task attempt."""

    task_id: str
    attempt_id: str
    status: AttemptStatus
    passed: bool
    duration_ms: int
    exit_code: int | None
    graders: tuple[GraderEvidence, ...] = ()
    schema_valid: bool | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    model_id: str | None = None
    seed: int | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None
    resilience_report_path: str | None = None
    resilience_notes: str | None = None
    resilience_expected_outcome: str | None = None
    resilience_unrecovered_sessions: int | None = None
    resilience_recovery_events: int | None = None


@dataclass(frozen=True, slots=True)
class TaskSummary:
    """Aggregated metrics for one task across repeats."""

    task_id: str
    attempts: int
    passed: int
    pass_rate: float
    schema_valid_rate: float | None
    consistency_rate: float | None
    threshold_passed: bool
    threshold_failures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RunSummary:
    """Aggregate metrics for an entire suite run."""

    tasks: int
    attempts: int
    passed_attempts: int
    pass_rate: float
    schema_valid_rate: float | None
    threshold_passed: bool
    threshold_failures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RunResult:
    """Complete evaluation run artifact."""

    schema_version: str
    suite_version: int
    suite_hash: str
    run_id: str
    agent_command: str
    application_revision: str | None
    started_at: str
    finished_at: str
    attempts: tuple[AttemptResult, ...]
    task_summaries: tuple[TaskSummary, ...]
    summary: RunSummary
    grader_versions: tuple[str, ...] = ()
    model_id: str | None = None
    provider: str | None = None
    temperature: float | None = None
    seed: int | None = None


@dataclass(frozen=True, slots=True)
class Baseline:
    """Immutable accepted evaluation result used for regression comparison."""

    schema_version: str
    suite_hash: str
    suite_version: int
    run_id: str
    agent_command: str
    application_revision: str | None
    grader_versions: tuple[str, ...]
    promoted_at: str
    reviewer: str | None
    reason: str | None
    summary: RunSummary
    task_summaries: tuple[TaskSummary, ...]
    model_id: str | None = None
    provider: str | None = None
    temperature: float | None = None
    seed: int | None = None
    thresholds: Thresholds = field(default_factory=Thresholds)


@dataclass(frozen=True, slots=True)
class ComparisonDelta:
    """Absolute and relative quality change for one metric."""

    name: str
    candidate: float | None
    baseline: float | None
    delta_points: float | None
    allowed_regression_points: float | None
    passed: bool
    message: str


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Result of comparing a candidate run against a baseline."""

    compatible: bool
    passed: bool
    deltas: tuple[ComparisonDelta, ...]
    incompatibility_reasons: tuple[str, ...] = ()
