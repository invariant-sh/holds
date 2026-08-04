"""Shared pytest fixtures and fakes."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.support.fakes import FakeAgentRunner, FakeClock, FakeIds, FakeRevision

from holds.domain.models import (
    AgentSpec,
    GraderSpec,
    Suite,
    SuiteDefaults,
    TaskSpec,
    Thresholds,
)

__all__ = [
    "FakeAgentRunner",
    "FakeClock",
    "FakeIds",
    "FakeRevision",
]


@pytest.fixture
def sample_suite(tmp_path: Path) -> Suite:
    suite_path = tmp_path / "holds.yaml"
    suite_path.write_text("version: 1\n", encoding="utf-8")
    return Suite(
        version=1,
        agent=AgentSpec(command="python agent.py", result_path="artifacts/result.json"),
        defaults=SuiteDefaults(repeats=2, timeout_seconds=10, seed=7),
        tasks=(
            TaskSpec(
                id="classify-refund-request",
                input={"customer_message": "I was charged twice."},
                expected={"category": "refund_request"},
                graders=(
                    GraderSpec(type="exact_field", path="$.category", equals="refund_request"),
                ),
                thresholds=Thresholds(pass_rate_gte=1.0),
            ),
        ),
        thresholds=Thresholds(pass_rate_gte=1.0),
        source_path=str(suite_path),
        content_hash="a" * 64,
    )
