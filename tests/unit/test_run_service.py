"""Run service unit tests."""

from __future__ import annotations

from tests.support.fakes import FakeAgentRunner, FakeClock, FakeIds, FakeRevision

from holds.adapters.graders import default_graders
from holds.application.run import RunService
from holds.domain.models import Suite


def test_run_service_aggregates_repeats(sample_suite: Suite) -> None:
    service = RunService(
        agent_runner=FakeAgentRunner(),
        graders=default_graders(),
        clock=FakeClock(),
        ids=FakeIds(),
        revision_provider=FakeRevision(),
    )
    result = service.execute(sample_suite)
    assert result.summary.attempts == 2
    assert result.summary.pass_rate == 1.0
    assert result.summary.threshold_passed is True
    assert result.grader_versions


def test_run_service_records_agent_failure(sample_suite: Suite) -> None:
    service = RunService(
        agent_runner=FakeAgentRunner(exit_code=2),
        graders=default_graders(),
        clock=FakeClock(),
        ids=FakeIds(),
        revision_provider=FakeRevision(),
    )
    result = service.execute(sample_suite)
    assert result.summary.pass_rate == 0.0
    assert result.attempts[0].status == "agent_error"
