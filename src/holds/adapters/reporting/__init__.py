"""JSON and terminal reporters."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from holds.domain.models import ComparisonResult, RunResult


def run_to_dict(run: RunResult) -> dict[str, Any]:
    """Serialize a run result into a JSON-compatible mapping."""
    return asdict(run)


def render_run_json(run: RunResult) -> str:
    """Render a stable JSON report."""
    return json.dumps(run_to_dict(run), indent=2, sort_keys=True) + "\n"


def render_run_terminal(run: RunResult) -> str:
    """Render a concise human-readable run summary."""
    lines = [
        f"Holds run `{run.run_id}`",
        f"Suite hash: {run.suite_hash[:12]}",
        f"Pass rate: {run.summary.pass_rate:.2%} "
        f"({run.summary.passed_attempts}/{run.summary.attempts})",
    ]
    if run.summary.schema_valid_rate is not None:
        lines.append(f"Schema valid rate: {run.summary.schema_valid_rate:.2%}")
    lines.append("Thresholds: " + ("PASS" if run.summary.threshold_passed else "FAIL"))
    for task in run.task_summaries:
        consistency = (
            f", consistency={task.consistency_rate:.2%}"
            if task.consistency_rate is not None
            else ""
        )
        lines.append(
            f"- {task.task_id}: pass_rate={task.pass_rate:.2%} "
            f"({task.passed}/{task.attempts}){consistency}"
        )
        for failure in task.threshold_failures:
            lines.append(f"  ! {failure}")
    for failure in run.summary.threshold_failures:
        if not failure.startswith("task:"):
            lines.append(f"! {failure}")
    return "\n".join(lines) + "\n"


def render_comparison_terminal(result: ComparisonResult) -> str:
    """Render a concise comparison summary."""
    lines = [
        "Holds compare",
        f"Compatible: {'yes' if result.compatible else 'no'}",
        f"Result: {'PASS' if result.passed else 'FAIL'}",
    ]
    for reason in result.incompatibility_reasons:
        lines.append(f"- incompatible: {reason}")
    for delta in result.deltas:
        candidate = "n/a" if delta.candidate is None else f"{delta.candidate:.2%}"
        baseline = "n/a" if delta.baseline is None else f"{delta.baseline:.2%}"
        lines.append(
            f"- {delta.name}: candidate={candidate} baseline={baseline} "
            f"[{'ok' if delta.passed else 'fail'}] {delta.message}"
        )
    return "\n".join(lines) + "\n"
