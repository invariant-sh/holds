"""Unit tests for optional Maul resilience adapter boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support.fakes import (
    FakeAgentRunner,
    FakeClock,
    FakeIds,
    FakeResilienceRunner,
    FakeRevision,
)

from holds.adapters.graders import default_graders
from holds.adapters.resilience.maul import MaulResilienceRunner, NoopResilienceRunner
from holds.application.run import RunService
from holds.domain.errors import ResilienceError
from holds.domain.models import MaulCondition, Suite, TaskSpec
from holds.ports import ResilienceRequest


def test_maul_runner_requires_binary(tmp_path: Path) -> None:
    runner = MaulResilienceRunner(maul_bin="maul-binary-does-not-exist", work_dir=tmp_path)
    with pytest.raises(ResilienceError, match="not found"):
        runner.prepare(
            ResilienceRequest(scenarios=("force_500",), config_path=None, repeats=1, seed=1)
        )


def test_noop_resilience_runner() -> None:
    runner = NoopResilienceRunner()
    request = ResilienceRequest(scenarios=(), config_path=None, repeats=1, seed=None)
    assert runner.prepare(request).notes == "maul disabled"
    assert runner.collect(request).notes == "maul disabled"


def test_maul_lifecycle_injects_env_and_writes_report(tmp_path: Path) -> None:
    fake_maul = Path(__file__).resolve().parents[1] / "support" / "fake_maul.py"
    runner = MaulResilienceRunner(maul_bin=str(fake_maul), work_dir=tmp_path)
    request = ResilienceRequest(
        scenarios=("force_500",),
        config_path=None,
        repeats=1,
        seed=7,
        task_id="degrade",
        attempt_id="degrade-001",
    )
    prepared = runner.prepare(request)
    assert prepared.env["MAUL_BASE_URL"].startswith("http://127.0.0.1:")
    assert prepared.env["OPENAI_BASE_URL"] == prepared.env["MAUL_BASE_URL"]
    collected = runner.collect(request)
    assert collected.report_path is not None
    assert collected.report_path.exists()
    assert collected.unrecovered_sessions == 1
    assert collected.notes == "maul report attached"


def test_run_service_collects_resilience_separately_from_task_quality(
    sample_suite: Suite, tmp_path: Path
) -> None:
    report = tmp_path / "reliability_report.json"
    report.write_text("{}", encoding="utf-8")
    resilience = FakeResilienceRunner(report_path=report)
    task = sample_suite.tasks[0]
    suite = Suite(
        version=sample_suite.version,
        agent=sample_suite.agent,
        defaults=sample_suite.defaults,
        tasks=(
            TaskSpec(
                id=task.id,
                input=task.input,
                expected=task.expected,
                graders=task.graders,
                thresholds=task.thresholds,
                repeats=task.repeats,
                timeout_seconds=task.timeout_seconds,
                maul=MaulCondition(scenarios=("force_500",), expected_outcome="safe_degradation"),
            ),
        ),
        thresholds=sample_suite.thresholds,
        source_path=sample_suite.source_path,
        content_hash=sample_suite.content_hash,
    )
    agent = FakeAgentRunner()
    service = RunService(
        agent_runner=agent,
        graders=default_graders(),
        clock=FakeClock(),
        ids=FakeIds(),
        revision_provider=FakeRevision(),
        resilience_runner=resilience,
    )
    result = service.execute(suite)
    assert len(resilience.prepared) == suite.repeats_for(suite.tasks[0])
    assert len(resilience.collected) == len(resilience.prepared)
    attempt = result.attempts[0]
    assert attempt.passed is True
    assert attempt.resilience_report_path == str(report)
    assert attempt.resilience_expected_outcome == "safe_degradation"
    assert attempt.resilience_unrecovered_sessions == 1
    assert agent.calls[0].env["MAUL_BASE_URL"] == "http://127.0.0.1:9/v1"
    assert agent.calls[0].env["OPENAI_BASE_URL"] == "http://127.0.0.1:9/v1"
