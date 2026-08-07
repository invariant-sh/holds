"""Fingerprint helpers."""

from __future__ import annotations

from holds.domain.fingerprints import are_compatible, compatibility_reasons
from holds.domain.models import Baseline, RunResult, RunSummary


def _run(hash_value: str = "a" * 64) -> RunResult:
    return RunResult(
        schema_version="1",
        suite_version=1,
        suite_hash=hash_value,
        run_id="run",
        agent_command="python agent.py",
        application_revision=None,
        started_at="t0",
        finished_at="t1",
        attempts=(),
        task_summaries=(),
        summary=RunSummary(
            tasks=0,
            attempts=0,
            passed_attempts=0,
            pass_rate=0.0,
            schema_valid_rate=None,
            threshold_passed=True,
        ),
        grader_versions=("exact:1",),
        model_id="m",
        provider="p",
    )


def _baseline(hash_value: str = "a" * 64) -> Baseline:
    run = _run(hash_value)
    return Baseline(
        schema_version="1",
        suite_hash=run.suite_hash,
        suite_version=run.suite_version,
        run_id=run.run_id,
        agent_command=run.agent_command,
        application_revision=None,
        grader_versions=run.grader_versions,
        promoted_at="t",
        reviewer=None,
        reason=None,
        summary=run.summary,
        task_summaries=(),
        model_id=run.model_id,
        provider=run.provider,
    )


def test_compatibility() -> None:
    assert are_compatible(_run(), _baseline()) is True
    reasons = compatibility_reasons(_run("b" * 64), _baseline())
    assert "suite_hash mismatch" in reasons
