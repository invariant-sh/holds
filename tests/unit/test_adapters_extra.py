"""Additional adapter coverage tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from holds.adapters.graders.exact import ExactGrader, resolve_path
from holds.adapters.reporting import render_comparison_terminal, render_run_terminal
from holds.adapters.resilience.maul import NoopResilienceRunner
from holds.adapters.runtime import GitRevisionProvider, SystemClock, UuidFactory
from holds.domain.models import (
    AttemptResult,
    ComparisonDelta,
    ComparisonResult,
    GraderSpec,
    RunResult,
    RunSummary,
    TaskSummary,
)
from holds.ports import ResilienceRequest


def test_exact_match_and_path_helpers() -> None:
    grader = ExactGrader()
    evidence = grader.grade(
        spec=GraderSpec(type="exact", equals={"category": "refund_request"}),
        output={"category": "refund_request"},
        expected={},
        suite_dir=Path("."),
    )
    assert evidence.passed is True
    assert resolve_path({"a": {"b": 1}}, "$.a.b") == 1
    with pytest.raises(KeyError):
        resolve_path({"a": 1}, "$.missing")


def test_noop_resilience_and_runtime_helpers(tmp_path: Path) -> None:
    runner = NoopResilienceRunner()
    request = ResilienceRequest(scenarios=("force_500",), config_path=None, repeats=1, seed=1)
    assert runner.prepare(request).report_path is None
    assert runner.collect(request).notes == "maul disabled"
    assert SystemClock().now_iso().endswith("Z")
    assert UuidFactory().attempt_id("task", 2) == "task-002"
    # Outside a git repo this may be None; inside holds it should resolve.
    revision = GitRevisionProvider(cwd=str(tmp_path)).revision()
    assert revision is None or isinstance(revision, str)


def test_renderers() -> None:
    run = RunResult(
        schema_version="1",
        suite_version=1,
        suite_hash="a" * 64,
        run_id="run-1",
        agent_command="python agent.py",
        application_revision=None,
        started_at="t0",
        finished_at="t1",
        attempts=(
            AttemptResult(
                task_id="t",
                attempt_id="t-001",
                status="passed",
                passed=True,
                duration_ms=1,
                exit_code=0,
            ),
        ),
        task_summaries=(
            TaskSummary(
                task_id="t",
                attempts=1,
                passed=1,
                pass_rate=1.0,
                schema_valid_rate=1.0,
                consistency_rate=1.0,
                threshold_passed=True,
            ),
        ),
        summary=RunSummary(
            tasks=1,
            attempts=1,
            passed_attempts=1,
            pass_rate=1.0,
            schema_valid_rate=1.0,
            threshold_passed=True,
        ),
    )
    text = render_run_terminal(run)
    assert "Pass rate" in text
    comparison = render_comparison_terminal(
        ComparisonResult(
            compatible=True,
            passed=True,
            deltas=(
                ComparisonDelta(
                    name="pass_rate",
                    candidate=1.0,
                    baseline=1.0,
                    delta_points=0.0,
                    allowed_regression_points=1.0,
                    passed=True,
                    message="ok",
                ),
            ),
        )
    )
    assert "PASS" in comparison
