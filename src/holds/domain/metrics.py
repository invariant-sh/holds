"""Aggregation and consistency metrics."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from holds.domain.models import AttemptResult, RunSummary, TaskSpec, TaskSummary, Thresholds
from holds.domain.thresholds import evaluate_thresholds


def rate(numerator: int, denominator: int) -> float:
    """Safe rate calculation."""
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def schema_valid_rate(attempts: Sequence[AttemptResult]) -> float | None:
    """Compute schema validity rate when any attempt reports the metric."""
    observed = [attempt for attempt in attempts if attempt.schema_valid is not None]
    if not observed:
        return None
    valid = sum(1 for attempt in observed if attempt.schema_valid)
    return rate(valid, len(observed))


def _canonicalize(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def consistency_rate(attempts: Sequence[AttemptResult]) -> float | None:
    """
    Fraction of successful outputs that match the most common successful output.

    Consistency is reported separately from correctness.
    """
    outputs = [
        _canonicalize(attempt.output)
        for attempt in attempts
        if attempt.status in {"passed", "failed"} and attempt.output is not None
    ]
    if len(outputs) < 2:
        return None
    counts: dict[str, int] = {}
    for item in outputs:
        counts[item] = counts.get(item, 0) + 1
    return rate(max(counts.values()), len(outputs))


def summarize_task(
    task: TaskSpec,
    attempts: Sequence[AttemptResult],
) -> TaskSummary:
    """Build per-task summary and absolute threshold decision."""
    passed = sum(1 for attempt in attempts if attempt.passed)
    pass_rate_value = rate(passed, len(attempts))
    schema_rate = schema_valid_rate(attempts)
    threshold_ok, failures = evaluate_thresholds(
        thresholds=task.thresholds,
        pass_rate=pass_rate_value,
        schema_valid_rate=schema_rate,
    )
    return TaskSummary(
        task_id=task.id,
        attempts=len(attempts),
        passed=passed,
        pass_rate=pass_rate_value,
        schema_valid_rate=schema_rate,
        consistency_rate=consistency_rate(attempts),
        threshold_passed=threshold_ok,
        threshold_failures=failures,
    )


def summarize_run(
    task_summaries: Sequence[TaskSummary],
    attempts: Sequence[AttemptResult],
    suite_thresholds: Thresholds,
) -> RunSummary:
    """Build suite-level summary combining task and suite thresholds."""
    passed_attempts = sum(1 for attempt in attempts if attempt.passed)
    pass_rate_value = rate(passed_attempts, len(attempts))
    schema_rate = schema_valid_rate(attempts)
    threshold_ok, failures = evaluate_thresholds(
        thresholds=suite_thresholds,
        pass_rate=pass_rate_value,
        schema_valid_rate=schema_rate,
    )
    task_failures = [
        f"task:{summary.task_id}: {message}"
        for summary in task_summaries
        for message in summary.threshold_failures
    ]
    all_failures = (*failures, *task_failures)
    return RunSummary(
        tasks=len(task_summaries),
        attempts=len(attempts),
        passed_attempts=passed_attempts,
        pass_rate=pass_rate_value,
        schema_valid_rate=schema_rate,
        threshold_passed=threshold_ok
        and all(summary.threshold_passed for summary in task_summaries),
        threshold_failures=all_failures,
    )
