"""Holds CLI entrypoint."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from holds import __version__
from holds.adapters.config.loader import YamlSuiteLoader
from holds.adapters.graders import default_graders
from holds.adapters.reporting import (
    render_comparison_terminal,
    render_run_json,
    render_run_terminal,
)
from holds.adapters.resilience.maul import MaulResilienceRunner, NoopResilienceRunner
from holds.adapters.runner.subprocess_runner import SubprocessAgentRunner
from holds.adapters.runtime import GitRevisionProvider, SystemClock, UuidFactory
from holds.adapters.storage.filesystem import FilesystemArtifactStore
from holds.application.baseline import BaselineService
from holds.application.compare import CompareService
from holds.application.exit_codes import ExitCode
from holds.application.run import RunService
from holds.domain.errors import (
    AgentExecutionError,
    BaselineError,
    GraderError,
    HoldsError,
    IncompatibleBaselineError,
    ResilienceError,
    SuiteValidationError,
    ThresholdFailedError,
)
from holds.domain.models import Thresholds

app = typer.Typer(
    name="holds",
    help="Continuous task evaluation and regression harness for LLM agents.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=ExitCode.SUCCESS)


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", help="Show version and exit.", callback=_version_callback),
    ] = None,
) -> None:
    """Holds command group."""
    del version


@app.command("run")
def run_command(
    suite: Annotated[Path, typer.Option("--suite", help="Path to holds.yaml")] = Path("holds.yaml"),
    report: Annotated[
        Path, typer.Option("--report", help="Destination for the JSON run report")
    ] = Path("artifacts/holds_report.json"),
    model: Annotated[str | None, typer.Option("--model", help="Model id metadata")] = None,
    provider: Annotated[str | None, typer.Option("--provider", help="Provider metadata")] = None,
    temperature: Annotated[
        float | None, typer.Option("--temperature", help="Sampling temperature metadata")
    ] = None,
    include_outputs: Annotated[
        bool,
        typer.Option("--include-outputs", help="Persist raw agent outputs in the report"),
    ] = False,
    enable_maul: Annotated[
        bool,
        typer.Option("--enable-maul", help="Enable optional Maul resilience adapter"),
    ] = False,
    no_fail_on_threshold: Annotated[
        bool,
        typer.Option(
            "--no-fail-on-threshold",
            help="Always write the report even when thresholds fail",
        ),
    ] = False,
) -> None:
    """Execute a suite and write a versioned report."""
    loader = YamlSuiteLoader()
    store = FilesystemArtifactStore()
    try:
        loaded = loader.load(suite)
        service = RunService(
            agent_runner=SubprocessAgentRunner(),
            graders=default_graders(),
            clock=SystemClock(),
            ids=UuidFactory(),
            revision_provider=GitRevisionProvider(cwd=str(suite.parent)),
            resilience_runner=(
                MaulResilienceRunner(maul_bin=os.environ.get("HOLDS_MAUL_BIN", "maul"))
                if enable_maul
                else NoopResilienceRunner()
            ),
            include_outputs=include_outputs,
        )
        result = service.execute(
            loaded,
            env=dict(os.environ),
            model_id=model,
            provider=provider,
            temperature=temperature,
        )
        store.write_run(report, result)
        markdown = report.with_suffix(".md")
        markdown.write_text(render_run_terminal(result), encoding="utf-8")
        typer.echo(render_run_terminal(result), nl=False)
        typer.echo(f"Wrote report: {report}")
        if not no_fail_on_threshold and not result.summary.threshold_passed:
            message = "; ".join(result.summary.threshold_failures) or "thresholds failed"
            _fail(ExitCode.THRESHOLD_FAILURE, ThresholdFailedError(message))
        if any(attempt.status == "grader_error" for attempt in result.attempts):
            _fail(ExitCode.GRADER_FAILURE, GraderError("one or more grader errors occurred"))
        if any(
            attempt.status in {"agent_error", "timeout", "missing_artifact"}
            for attempt in result.attempts
        ):
            _fail(ExitCode.AGENT_FAILURE, AgentExecutionError("one or more agent attempts failed"))
    except SuiteValidationError as error:
        _fail(ExitCode.INVALID_SUITE, error)
    except ThresholdFailedError as error:
        _fail(ExitCode.THRESHOLD_FAILURE, error)
    except GraderError as error:
        _fail(ExitCode.GRADER_FAILURE, error)
    except AgentExecutionError as error:
        _fail(ExitCode.AGENT_FAILURE, error)
    except ResilienceError as error:
        _fail(ExitCode.RESILIENCE_FAILURE, error)
    except HoldsError as error:
        _fail(ExitCode.INTERNAL, error)


@app.command("baseline")
def baseline_command(
    run: Annotated[Path, typer.Option("--run", help="Candidate run report")] = Path(
        "artifacts/holds_report.json"
    ),
    output: Annotated[Path, typer.Option("--output", help="Baseline destination")] = Path(
        "artifacts/baseline.json"
    ),
    reviewer: Annotated[str | None, typer.Option("--reviewer")] = None,
    reason: Annotated[str | None, typer.Option("--reason")] = None,
    max_regression_points: Annotated[
        float | None,
        typer.Option("--max-regression-points", help="Allowed regression in percentage points"),
    ] = None,
    force: Annotated[bool, typer.Option("--force", help="Replace an existing baseline")] = False,
) -> None:
    """Promote an accepted run into an immutable baseline."""
    service = BaselineService(store=FilesystemArtifactStore(), clock=SystemClock())
    try:
        baseline = service.promote(
            run_path=run,
            baseline_path=output,
            reviewer=reviewer,
            reason=reason,
            thresholds=Thresholds(max_regression_points=max_regression_points),
            force=force,
        )
        typer.echo(
            f"Promoted baseline from run `{baseline.run_id}` -> {output}",
        )
    except BaselineError as error:
        _fail(ExitCode.BASELINE_FAILURE, error)
    except HoldsError as error:
        _fail(ExitCode.INTERNAL, error)


@app.command("compare")
def compare_command(
    candidate: Annotated[Path, typer.Option("--candidate")] = Path("artifacts/holds_report.json"),
    baseline: Annotated[Path, typer.Option("--baseline")] = Path("artifacts/baseline.json"),
    max_regression_points: Annotated[
        float | None,
        typer.Option("--max-regression-points"),
    ] = None,
    allow_incompatible: Annotated[
        bool,
        typer.Option("--allow-incompatible", help="Compare even when provenance differs"),
    ] = False,
) -> None:
    """Compare a candidate run against a baseline."""
    service = CompareService(store=FilesystemArtifactStore())
    try:
        result = service.compare(
            candidate_path=candidate,
            baseline_path=baseline,
            thresholds=(
                Thresholds(max_regression_points=max_regression_points)
                if max_regression_points is not None
                else None
            ),
            allow_incompatible=allow_incompatible,
        )
        typer.echo(render_comparison_terminal(result), nl=False)
        if not result.passed:
            raise typer.Exit(code=ExitCode.THRESHOLD_FAILURE)
    except IncompatibleBaselineError as error:
        _fail(ExitCode.INCOMPATIBLE_BASELINE, error)
    except BaselineError as error:
        _fail(ExitCode.BASELINE_FAILURE, error)
    except HoldsError as error:
        _fail(ExitCode.INTERNAL, error)


@app.command("validate")
def validate_command(
    suite: Annotated[Path, typer.Option("--suite")] = Path("holds.yaml"),
) -> None:
    """Validate a suite file without executing tasks."""
    try:
        loaded = YamlSuiteLoader().load(suite)
    except SuiteValidationError as error:
        _fail(ExitCode.INVALID_SUITE, error)
    else:
        typer.echo(
            f"Suite OK: version={loaded.version} tasks={len(loaded.tasks)} "
            f"hash={loaded.content_hash[:12]}"
        )


def _fail(code: ExitCode, error: Exception) -> None:
    typer.secho(f"error: {error}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=code)


# Keep render_run_json import used for potential scripting.
_ = render_run_json

if __name__ == "__main__":
    app()
