"""Domain model and threshold unit tests."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from holds.domain.errors import ThresholdFailedError
from holds.domain.metrics import consistency_rate, rate, summarize_task
from holds.domain.models import AttemptResult, TaskSpec, Thresholds
from holds.domain.thresholds import (
    ensure_thresholds_passed,
    evaluate_regression,
    evaluate_thresholds,
    regression_points,
)


def test_thresholds_reject_out_of_range() -> None:
    with pytest.raises(ValueError, match="pass_rate_gte"):
        Thresholds(pass_rate_gte=1.5)


def test_evaluate_thresholds_boundary() -> None:
    passed, failures = evaluate_thresholds(
        thresholds=Thresholds(pass_rate_gte=0.95, schema_valid_rate_gte=1.0),
        pass_rate=0.95,
        schema_valid_rate=1.0,
    )
    assert passed is True
    assert failures == ()

    passed, failures = evaluate_thresholds(
        thresholds=Thresholds(pass_rate_gte=0.95),
        pass_rate=0.949,
        schema_valid_rate=None,
    )
    assert passed is False
    assert failures


def test_ensure_thresholds_passed_raises() -> None:
    with pytest.raises(ThresholdFailedError):
        ensure_thresholds_passed(
            thresholds=Thresholds(pass_rate_gte=1.0),
            pass_rate=0.5,
            schema_valid_rate=None,
        )


def test_regression_points_and_evaluation() -> None:
    assert regression_points(0.96, 0.98) == pytest.approx(2.0)
    ok, message, delta = evaluate_regression(
        name="pass_rate",
        candidate=0.96,
        baseline=0.98,
        allowed_points=1.0,
    )
    assert ok is False
    assert delta == pytest.approx(2.0)
    assert "regressed" in message


def test_consistency_rate_ignores_correctness() -> None:
    attempts = (
        AttemptResult(
            task_id="t",
            attempt_id="t-001",
            status="passed",
            passed=True,
            duration_ms=1,
            exit_code=0,
            output={"category": "refund_request"},
        ),
        AttemptResult(
            task_id="t",
            attempt_id="t-002",
            status="failed",
            passed=False,
            duration_ms=1,
            exit_code=0,
            output={"category": "other"},
        ),
        AttemptResult(
            task_id="t",
            attempt_id="t-003",
            status="passed",
            passed=True,
            duration_ms=1,
            exit_code=0,
            output={"category": "refund_request"},
        ),
    )
    assert consistency_rate(attempts) == pytest.approx(2 / 3)


def test_summarize_task_threshold() -> None:
    task = TaskSpec(
        id="t",
        input={},
        thresholds=Thresholds(pass_rate_gte=1.0),
    )
    attempts = (
        AttemptResult(
            task_id="t",
            attempt_id="t-001",
            status="passed",
            passed=True,
            duration_ms=1,
            exit_code=0,
            schema_valid=True,
        ),
        AttemptResult(
            task_id="t",
            attempt_id="t-002",
            status="failed",
            passed=False,
            duration_ms=1,
            exit_code=0,
            schema_valid=True,
        ),
    )
    summary = summarize_task(task, attempts)
    assert summary.pass_rate == pytest.approx(0.5)
    assert summary.threshold_passed is False


@given(
    numerator=st.integers(min_value=0, max_value=100),
    denominator=st.integers(min_value=1, max_value=100),
)
def test_rate_property(numerator: int, denominator: int) -> None:
    value = rate(min(numerator, denominator), denominator)
    assert 0.0 <= value <= 1.0
    assert value == pytest.approx(min(numerator, denominator) / denominator)
