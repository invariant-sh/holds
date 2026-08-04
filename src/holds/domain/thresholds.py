"""Threshold evaluation policies."""

from __future__ import annotations

from holds.domain.errors import ThresholdFailedError
from holds.domain.models import Thresholds


def evaluate_rate_threshold(
    *,
    name: str,
    actual: float | None,
    required: float | None,
) -> str | None:
    """Return a failure message when an absolute rate threshold is breached."""
    if required is None:
        return None
    if actual is None:
        return f"{name}: required {required:.4f} but metric is unavailable"
    if actual + 1e-12 < required:
        return f"{name}: {actual:.4f} < required {required:.4f}"
    return None


def evaluate_thresholds(
    *,
    thresholds: Thresholds,
    pass_rate: float,
    schema_valid_rate: float | None,
) -> tuple[bool, tuple[str, ...]]:
    """Evaluate absolute thresholds and return pass flag plus failure messages."""
    failures: list[str] = []
    for message in (
        evaluate_rate_threshold(
            name="pass_rate_gte",
            actual=pass_rate,
            required=thresholds.pass_rate_gte,
        ),
        evaluate_rate_threshold(
            name="schema_valid_rate_gte",
            actual=schema_valid_rate,
            required=thresholds.schema_valid_rate_gte,
        ),
    ):
        if message is not None:
            failures.append(message)
    return (not failures, tuple(failures))


def ensure_thresholds_passed(
    *,
    thresholds: Thresholds,
    pass_rate: float,
    schema_valid_rate: float | None,
) -> None:
    """Raise when absolute thresholds fail."""
    passed, failures = evaluate_thresholds(
        thresholds=thresholds,
        pass_rate=pass_rate,
        schema_valid_rate=schema_valid_rate,
    )
    if not passed:
        raise ThresholdFailedError("; ".join(failures))


def regression_points(candidate: float, baseline: float) -> float:
    """Return positive points when the candidate is worse than the baseline."""
    return max(0.0, (baseline - candidate) * 100.0)


def evaluate_regression(
    *,
    name: str,
    candidate: float | None,
    baseline: float | None,
    allowed_points: float | None,
) -> tuple[bool, str, float | None]:
    """Evaluate allowed regression in percentage points."""
    if candidate is None or baseline is None:
        return False, f"{name}: unavailable for regression comparison", None
    delta = regression_points(candidate, baseline)
    allowed = 0.0 if allowed_points is None else allowed_points
    if delta > allowed + 1e-12:
        return (
            False,
            f"{name}: regressed {delta:.2f} points; allowed {allowed:.2f}",
            delta,
        )
    return True, f"{name}: regression {delta:.2f} points within allowed {allowed:.2f}", delta
