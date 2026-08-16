"""Suite execution use case."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from holds.application.resilience import ResilienceAttempt, attach_resilience
from holds.domain.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    GraderError,
    MissingResultArtifactError,
)
from holds.domain.metrics import summarize_run, summarize_task
from holds.domain.models import (
    AttemptResult,
    AttemptStatus,
    GraderEvidence,
    RunResult,
    Suite,
    TaskSpec,
)
from holds.ports import (
    AgentLaunchRequest,
    AgentLaunchResult,
    AgentRunner,
    ApplicationRevisionProvider,
    Clock,
    Grader,
    IdFactory,
    ResilienceRequest,
    ResilienceRunner,
)


class RunService:
    """Orchestrates suite execution, grading, and aggregation."""

    def __init__(
        self,
        *,
        agent_runner: AgentRunner,
        graders: dict[str, Grader],
        clock: Clock,
        ids: IdFactory,
        revision_provider: ApplicationRevisionProvider,
        resilience_runner: ResilienceRunner | None = None,
        include_outputs: bool = False,
    ) -> None:
        self._agent_runner = agent_runner
        self._graders = graders
        self._clock = clock
        self._ids = ids
        self._revision_provider = revision_provider
        self._resilience_runner = resilience_runner
        self._include_outputs = include_outputs

    def execute(
        self,
        suite: Suite,
        *,
        env: dict[str, str] | None = None,
        model_id: str | None = None,
        provider: str | None = None,
        temperature: float | None = None,
        fail_on_thresholds: bool = True,
    ) -> RunResult:
        """Run every task/attempt and return a versioned report."""
        del fail_on_thresholds
        started_at = self._clock.now_iso()
        suite_dir = Path(suite.source_path).resolve().parent if suite.source_path else Path.cwd()
        grader_versions: set[str] = set()
        attempts = self._collect_attempts(suite, suite_dir, env or {}, grader_versions)
        task_summaries = tuple(
            summarize_task(
                task,
                [attempt for attempt in attempts if attempt.task_id == task.id],
            )
            for task in suite.tasks
        )
        summary = summarize_run(task_summaries, attempts, suite.thresholds)
        return RunResult(
            schema_version="1",
            suite_version=suite.version,
            suite_hash=suite.content_hash,
            run_id=self._ids.run_id(),
            agent_command=suite.agent.command,
            application_revision=self._revision_provider.revision(),
            started_at=started_at,
            finished_at=self._clock.now_iso(),
            attempts=tuple(attempts),
            task_summaries=task_summaries,
            summary=summary,
            grader_versions=tuple(sorted(grader_versions)),
            model_id=model_id,
            provider=provider,
            temperature=temperature,
            seed=suite.defaults.seed,
        )

    def _collect_attempts(
        self,
        suite: Suite,
        suite_dir: Path,
        env: dict[str, str],
        grader_versions: set[str],
    ) -> list[AttemptResult]:
        attempts: list[AttemptResult] = []
        for task in suite.tasks:
            attempts.extend(
                self._run_task(
                    suite=suite,
                    suite_dir=suite_dir,
                    task=task,
                    env=env,
                    grader_versions=grader_versions,
                )
            )
        return attempts

    def _run_task(
        self,
        *,
        suite: Suite,
        suite_dir: Path,
        task: TaskSpec,
        env: dict[str, str],
        grader_versions: set[str],
    ) -> list[AttemptResult]:
        timeout = suite.timeout_for(task)
        return [
            self._run_attempt(
                suite=suite,
                suite_dir=suite_dir,
                task=task,
                attempt_id=self._ids.attempt_id(task.id, index),
                timeout=timeout,
                env=env,
                grader_versions=grader_versions,
            )
            for index in range(1, suite.repeats_for(task) + 1)
        ]

    def _run_attempt(
        self,
        *,
        suite: Suite,
        suite_dir: Path,
        task: TaskSpec,
        attempt_id: str,
        timeout: float,
        env: dict[str, str],
        grader_versions: set[str],
    ) -> AttemptResult:
        working_directory = _working_directory(suite, suite_dir)
        session = ResilienceAttempt(
            runner=self._resilience_runner,
            request=_maul_request(suite, suite_dir, task, attempt_id),
            enabled=task.maul is not None and self._resilience_runner is not None,
        )
        with session as prepared:
            attempt = self._launch_and_grade(
                request=AgentLaunchRequest(
                    command=suite.agent.command,
                    working_directory=working_directory,
                    result_path=working_directory / suite.agent.result_path,
                    input_path=working_directory / ".holds" / f"{attempt_id}.input.json",
                    input_payload=task.input,
                    task_id=task.id,
                    attempt_id=attempt_id,
                    timeout_seconds=timeout,
                    seed=suite.defaults.seed,
                    env={**env, **prepared.env},
                ),
                suite_dir=suite_dir,
                task=task,
                attempt_id=attempt_id,
                timeout=timeout,
                seed=suite.defaults.seed,
                grader_versions=grader_versions,
            )
        return attach_resilience(attempt, session.collected, task.maul)

    def _launch_and_grade(
        self,
        *,
        request: AgentLaunchRequest,
        suite_dir: Path,
        task: TaskSpec,
        attempt_id: str,
        timeout: float,
        seed: int | None,
        grader_versions: set[str],
    ) -> AttemptResult:
        launch = self._safe_launch(
            request,
            task_id=task.id,
            attempt_id=attempt_id,
            timeout=timeout,
            seed=seed,
        )
        if isinstance(launch, AttemptResult):
            return launch
        early = _launch_failure_result(
            task_id=task.id,
            attempt_id=attempt_id,
            launch=launch,
            seed=seed,
            include_outputs=self._include_outputs,
        )
        if early is not None:
            return early
        return self._grade_attempt(
            suite_dir=suite_dir,
            task=task,
            attempt_id=attempt_id,
            launch=launch,
            seed=seed,
            grader_versions=grader_versions,
        )

    def _safe_launch(
        self,
        request: AgentLaunchRequest,
        *,
        task_id: str,
        attempt_id: str,
        timeout: float,
        seed: int | None,
    ) -> AgentLaunchResult | AttemptResult:
        try:
            return self._agent_runner.run(request)
        except AgentTimeoutError as error:
            return _error_attempt(
                task_id=task_id,
                attempt_id=attempt_id,
                status="timeout",
                duration_ms=int(timeout * 1000),
                error=str(error),
                seed=seed,
            )
        except MissingResultArtifactError as error:
            return _error_attempt(
                task_id=task_id,
                attempt_id=attempt_id,
                status="missing_artifact",
                duration_ms=0,
                error=str(error),
                seed=seed,
            )
        except AgentExecutionError as error:
            return _error_attempt(
                task_id=task_id,
                attempt_id=attempt_id,
                status="agent_error",
                duration_ms=0,
                error=str(error),
                seed=seed,
            )

    def _grade_attempt(
        self,
        *,
        suite_dir: Path,
        task: TaskSpec,
        attempt_id: str,
        launch: AgentLaunchResult,
        seed: int | None,
        grader_versions: set[str],
    ) -> AttemptResult:
        assert launch.output is not None
        try:
            evidence, schema_valid = self._grade_output(
                suite_dir=suite_dir,
                task=task,
                output=launch.output,
                grader_versions=grader_versions,
            )
        except GraderError as error:
            return AttemptResult(
                task_id=task.id,
                attempt_id=attempt_id,
                status="grader_error",
                passed=False,
                duration_ms=launch.duration_ms,
                exit_code=launch.exit_code,
                error=str(error),
                seed=seed,
                stdout_tail=_tail(launch.stdout),
                stderr_tail=_tail(launch.stderr),
                output=launch.output if self._include_outputs else None,
            )
        passed = all(item.passed for item in evidence)
        return AttemptResult(
            task_id=task.id,
            attempt_id=attempt_id,
            status="passed" if passed else "failed",
            passed=passed,
            duration_ms=launch.duration_ms,
            exit_code=launch.exit_code,
            graders=evidence,
            schema_valid=schema_valid,
            output=launch.output if self._include_outputs else None,
            model_id=_extract_model_id(launch.output),
            seed=seed,
            stdout_tail=_tail(launch.stdout),
            stderr_tail=_tail(launch.stderr),
        )

    def _grade_output(
        self,
        *,
        suite_dir: Path,
        task: TaskSpec,
        output: dict[str, Any],
        grader_versions: set[str],
    ) -> tuple[tuple[GraderEvidence, ...], bool | None]:
        evidence: list[GraderEvidence] = []
        schema_valid: bool | None = None
        for index, spec in enumerate(task.graders):
            item = self._grade_one(
                suite_dir=suite_dir,
                task=task,
                output=output,
                spec_index=index,
                grader_versions=grader_versions,
            )
            evidence.append(item)
            if spec.type == "json_schema":
                schema_valid = item.passed if schema_valid is None else schema_valid and item.passed
        return tuple(evidence), schema_valid

    def _grade_one(
        self,
        *,
        suite_dir: Path,
        task: TaskSpec,
        output: dict[str, Any],
        spec_index: int,
        grader_versions: set[str],
    ) -> GraderEvidence:
        spec = task.graders[spec_index]
        grader = self._graders.get(spec.type)
        if grader is None:
            msg = f"no grader registered for type `{spec.type}`"
            raise GraderError(msg)
        grader_versions.add(grader.version_tag)
        item = grader.grade(
            spec=spec,
            output=output,
            expected=task.expected,
            suite_dir=suite_dir,
        )
        if item.grader_id:
            return item
        return GraderEvidence(
            grader_id=spec.id or f"{spec.type}:{spec_index}",
            grader_type=item.grader_type,
            passed=item.passed,
            message=item.message,
            details=item.details,
        )


def _working_directory(suite: Suite, suite_dir: Path) -> Path:
    if suite.agent.working_directory:
        return Path(suite.agent.working_directory)
    return suite_dir


def _maul_request(
    suite: Suite,
    suite_dir: Path,
    task: TaskSpec,
    attempt_id: str,
) -> ResilienceRequest:
    maul = task.maul
    if maul is None:
        return ResilienceRequest(
            scenarios=(),
            config_path=None,
            repeats=1,
            seed=suite.defaults.seed,
            task_id=task.id,
            attempt_id=attempt_id,
        )
    config_path = suite_dir / maul.config if maul.config else None
    return ResilienceRequest(
        scenarios=maul.scenarios,
        config_path=config_path,
        repeats=maul.repeats or 1,
        seed=suite.defaults.seed,
        task_id=task.id,
        attempt_id=attempt_id,
    )


def _launch_failure_result(
    *,
    task_id: str,
    attempt_id: str,
    launch: AgentLaunchResult,
    seed: int | None,
    include_outputs: bool,
) -> AttemptResult | None:
    if launch.timed_out:
        status: AttemptStatus = "timeout"
        error = "agent timed out"
        output = None
    elif launch.artifact_error is not None or launch.output is None:
        status = "missing_artifact"
        error = launch.artifact_error or "missing result artifact"
        output = None
    elif launch.exit_code != 0:
        status = "agent_error"
        error = f"agent exited with code {launch.exit_code}"
        output = launch.output if include_outputs else None
    else:
        return None
    return AttemptResult(
        task_id=task_id,
        attempt_id=attempt_id,
        status=status,
        passed=False,
        duration_ms=launch.duration_ms,
        exit_code=launch.exit_code,
        error=error,
        seed=seed,
        stdout_tail=_tail(launch.stdout),
        stderr_tail=_tail(launch.stderr),
        output=output,
    )


def _error_attempt(
    *,
    task_id: str,
    attempt_id: str,
    status: AttemptStatus,
    duration_ms: int,
    error: str,
    seed: int | None,
) -> AttemptResult:
    return AttemptResult(
        task_id=task_id,
        attempt_id=attempt_id,
        status=status,
        passed=False,
        duration_ms=duration_ms,
        exit_code=None,
        error=error,
        seed=seed,
    )


def _tail(text: str, limit: int = 400) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None
    if len(stripped) <= limit:
        return stripped
    return stripped[-limit:]


def _extract_model_id(output: dict[str, Any]) -> str | None:
    value = output.get("model") or output.get("model_id")
    return value if isinstance(value, str) else None
