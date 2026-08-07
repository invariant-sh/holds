"""Baseline and compare unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support.fakes import FakeClock

from holds.adapters.storage.filesystem import FilesystemArtifactStore
from holds.application.baseline import BaselineService
from holds.application.compare import CompareService
from holds.domain.errors import IncompatibleBaselineError
from holds.domain.models import (
    AttemptResult,
    RunResult,
    RunSummary,
    TaskSummary,
    Thresholds,
)


def _run(*, suite_hash: str = "a" * 64, pass_rate: float = 1.0) -> RunResult:
    return RunResult(
        schema_version="1",
        suite_version=1,
        suite_hash=suite_hash,
        run_id="run-1",
        agent_command="python agent.py",
        application_revision="abc",
        started_at="2026-08-04T12:00:00Z",
        finished_at="2026-08-04T12:00:01Z",
        attempts=(
            AttemptResult(
                task_id="t",
                attempt_id="t-001",
                status="passed",
                passed=True,
                duration_ms=1,
                exit_code=0,
                schema_valid=True,
            ),
        ),
        task_summaries=(
            TaskSummary(
                task_id="t",
                attempts=1,
                passed=1,
                pass_rate=pass_rate,
                schema_valid_rate=1.0,
                consistency_rate=None,
                threshold_passed=True,
            ),
        ),
        summary=RunSummary(
            tasks=1,
            attempts=1,
            passed_attempts=1 if pass_rate == 1.0 else 0,
            pass_rate=pass_rate,
            schema_valid_rate=1.0,
            threshold_passed=True,
        ),
        grader_versions=("exact:1",),
        model_id="stub",
        provider="local",
    )


def test_baseline_promote_and_compare(tmp_path: Path) -> None:
    store = FilesystemArtifactStore()
    run_path = tmp_path / "run.json"
    baseline_path = tmp_path / "baseline.json"
    store.write_run(run_path, _run())
    baseline = BaselineService(store=store, clock=FakeClock()).promote(
        run_path=run_path,
        baseline_path=baseline_path,
        reviewer="eduardo",
        reason="accepted",
        thresholds=Thresholds(max_regression_points=1.0),
    )
    assert baseline.reviewer == "eduardo"

    candidate_path = tmp_path / "candidate.json"
    store.write_run(candidate_path, _run(pass_rate=0.995))
    result = CompareService(store=store).compare(
        candidate_path=candidate_path,
        baseline_path=baseline_path,
    )
    assert result.compatible is True
    assert result.passed is True


def test_compare_rejects_incompatible(tmp_path: Path) -> None:
    store = FilesystemArtifactStore()
    run_path = tmp_path / "run.json"
    baseline_path = tmp_path / "baseline.json"
    store.write_run(run_path, _run())
    BaselineService(store=store, clock=FakeClock()).promote(
        run_path=run_path,
        baseline_path=baseline_path,
        reviewer=None,
        reason=None,
    )
    candidate_path = tmp_path / "candidate.json"
    store.write_run(candidate_path, _run(suite_hash="b" * 64))
    with pytest.raises(IncompatibleBaselineError, match="suite_hash"):
        CompareService(store=store).compare(
            candidate_path=candidate_path,
            baseline_path=baseline_path,
        )
