"""Baseline promotion helpers."""

from __future__ import annotations

from holds.domain.models import Baseline, RunResult, Thresholds


def baseline_from_run(
    run: RunResult,
    *,
    promoted_at: str,
    reviewer: str | None,
    reason: str | None,
    thresholds: Thresholds | None = None,
) -> Baseline:
    """Create an immutable baseline from an accepted run."""
    return Baseline(
        schema_version="1",
        suite_hash=run.suite_hash,
        suite_version=run.suite_version,
        run_id=run.run_id,
        agent_command=run.agent_command,
        application_revision=run.application_revision,
        grader_versions=run.grader_versions,
        promoted_at=promoted_at,
        reviewer=reviewer,
        reason=reason,
        summary=run.summary,
        task_summaries=run.task_summaries,
        model_id=run.model_id,
        provider=run.provider,
        temperature=run.temperature,
        seed=run.seed,
        thresholds=thresholds or Thresholds(),
    )
