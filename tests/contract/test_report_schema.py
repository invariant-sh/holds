"""Report contract tests."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from holds.adapters.reporting import render_run_json
from holds.domain.models import (
    AttemptResult,
    RunResult,
    RunSummary,
    TaskSummary,
)


def test_report_matches_contract_schema() -> None:
    schema = json.loads(
        (Path(__file__).resolve().parents[2] / "contracts" / "report.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    run = RunResult(
        schema_version="1",
        suite_version=1,
        suite_hash="a" * 64,
        run_id="run-1",
        agent_command="python agent.py",
        application_revision=None,
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
            ),
        ),
        task_summaries=(
            TaskSummary(
                task_id="t",
                attempts=1,
                passed=1,
                pass_rate=1.0,
                schema_valid_rate=None,
                consistency_rate=None,
                threshold_passed=True,
            ),
        ),
        summary=RunSummary(
            tasks=1,
            attempts=1,
            passed_attempts=1,
            pass_rate=1.0,
            schema_valid_rate=None,
            threshold_passed=True,
        ),
    )
    payload = json.loads(render_run_json(run))
    Draft202012Validator(schema).validate(payload)
