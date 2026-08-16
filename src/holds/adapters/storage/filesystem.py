"""Filesystem artifact store with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, cast

from holds.domain.errors import BaselineError
from holds.domain.models import (
    AttemptResult,
    AttemptStatus,
    Baseline,
    GraderEvidence,
    GraderType,
    RunResult,
    RunSummary,
    TaskSummary,
    Thresholds,
)


class FilesystemArtifactStore:
    """Read and write run/baseline JSON artifacts."""

    def write_run(self, path: Path, run: RunResult) -> Path:
        """Write a run report atomically."""
        _atomic_write_json(path, asdict(run))
        return path

    def read_run(self, path: Path) -> RunResult:
        """Load a run report."""
        payload = _read_json(path)
        return run_from_dict(payload)

    def write_baseline(self, path: Path, baseline: Baseline) -> Path:
        """Write a baseline atomically; refuse silent overwrite."""
        if path.exists():
            msg = f"baseline already exists at `{path}`"
            raise BaselineError(msg)
        _atomic_write_json(path, asdict(baseline))
        return path

    def read_baseline(self, path: Path) -> Baseline:
        """Load a baseline."""
        payload = _read_json(path)
        return baseline_from_dict(payload)


def run_from_dict(payload: dict[str, Any]) -> RunResult:
    """Rehydrate a RunResult from JSON."""
    return RunResult(
        schema_version=str(payload["schema_version"]),
        suite_version=int(payload["suite_version"]),
        suite_hash=str(payload["suite_hash"]),
        run_id=str(payload["run_id"]),
        agent_command=str(payload["agent_command"]),
        application_revision=_optional_str(payload.get("application_revision")),
        started_at=str(payload["started_at"]),
        finished_at=str(payload["finished_at"]),
        attempts=tuple(_attempt_from_dict(item) for item in payload.get("attempts", [])),
        task_summaries=tuple(
            _task_summary_from_dict(item) for item in payload.get("task_summaries", [])
        ),
        summary=_run_summary_from_dict(payload["summary"]),
        grader_versions=tuple(str(item) for item in payload.get("grader_versions", [])),
        model_id=_optional_str(payload.get("model_id")),
        provider=_optional_str(payload.get("provider")),
        temperature=_optional_float(payload.get("temperature")),
        seed=_optional_int(payload.get("seed")),
    )


def baseline_from_dict(payload: dict[str, Any]) -> Baseline:
    """Rehydrate a Baseline from JSON."""
    thresholds_raw = payload.get("thresholds") or {}
    return Baseline(
        schema_version=str(payload["schema_version"]),
        suite_hash=str(payload["suite_hash"]),
        suite_version=int(payload["suite_version"]),
        run_id=str(payload["run_id"]),
        agent_command=str(payload["agent_command"]),
        application_revision=_optional_str(payload.get("application_revision")),
        grader_versions=tuple(str(item) for item in payload.get("grader_versions", [])),
        promoted_at=str(payload["promoted_at"]),
        reviewer=_optional_str(payload.get("reviewer")),
        reason=_optional_str(payload.get("reason")),
        summary=_run_summary_from_dict(payload["summary"]),
        task_summaries=tuple(
            _task_summary_from_dict(item) for item in payload.get("task_summaries", [])
        ),
        model_id=_optional_str(payload.get("model_id")),
        provider=_optional_str(payload.get("provider")),
        temperature=_optional_float(payload.get("temperature")),
        seed=_optional_int(payload.get("seed")),
        thresholds=Thresholds(
            pass_rate_gte=_optional_float(thresholds_raw.get("pass_rate_gte")),
            schema_valid_rate_gte=_optional_float(thresholds_raw.get("schema_valid_rate_gte")),
            max_regression_points=_optional_float(thresholds_raw.get("max_regression_points")),
        ),
    )


def _attempt_from_dict(payload: dict[str, Any]) -> AttemptResult:
    status = str(payload["status"])
    allowed_status: set[str] = {
        "passed",
        "failed",
        "agent_error",
        "timeout",
        "missing_artifact",
        "grader_error",
    }
    if status not in allowed_status:
        msg = f"invalid attempt status `{status}`"
        raise BaselineError(msg)
    return AttemptResult(
        task_id=str(payload["task_id"]),
        attempt_id=str(payload["attempt_id"]),
        status=cast(AttemptStatus, status),
        passed=bool(payload["passed"]),
        duration_ms=int(payload["duration_ms"]),
        exit_code=_optional_int(payload.get("exit_code")),
        graders=tuple(_grader_from_dict(item) for item in payload.get("graders", [])),
        schema_valid=payload.get("schema_valid"),
        output=payload.get("output"),
        error=_optional_str(payload.get("error")),
        model_id=_optional_str(payload.get("model_id")),
        seed=_optional_int(payload.get("seed")),
        stdout_tail=_optional_str(payload.get("stdout_tail")),
        stderr_tail=_optional_str(payload.get("stderr_tail")),
        resilience_report_path=_optional_str(payload.get("resilience_report_path")),
        resilience_notes=_optional_str(payload.get("resilience_notes")),
        resilience_expected_outcome=_optional_str(payload.get("resilience_expected_outcome")),
        resilience_unrecovered_sessions=_optional_int(
            payload.get("resilience_unrecovered_sessions")
        ),
        resilience_recovery_events=_optional_int(payload.get("resilience_recovery_events")),
    )


def _grader_from_dict(payload: dict[str, Any]) -> GraderEvidence:
    grader_type = str(payload["grader_type"])
    allowed: set[str] = {"exact", "exact_field", "json_schema", "python"}
    if grader_type not in allowed:
        msg = f"invalid grader type `{grader_type}`"
        raise BaselineError(msg)
    return GraderEvidence(
        grader_id=str(payload["grader_id"]),
        grader_type=cast(GraderType, grader_type),
        passed=bool(payload["passed"]),
        message=str(payload["message"]),
        details=dict(payload.get("details") or {}),
    )


def _task_summary_from_dict(payload: dict[str, Any]) -> TaskSummary:
    return TaskSummary(
        task_id=str(payload["task_id"]),
        attempts=int(payload["attempts"]),
        passed=int(payload["passed"]),
        pass_rate=float(payload["pass_rate"]),
        schema_valid_rate=_optional_float(payload.get("schema_valid_rate")),
        consistency_rate=_optional_float(payload.get("consistency_rate")),
        threshold_passed=bool(payload["threshold_passed"]),
        threshold_failures=tuple(str(item) for item in payload.get("threshold_failures", [])),
    )


def _run_summary_from_dict(payload: dict[str, Any]) -> RunSummary:
    return RunSummary(
        tasks=int(payload["tasks"]),
        attempts=int(payload["attempts"]),
        passed_attempts=int(payload["passed_attempts"]),
        pass_rate=float(payload["pass_rate"]),
        schema_valid_rate=_optional_float(payload.get("schema_valid_rate")),
        threshold_passed=bool(payload["threshold_passed"]),
        threshold_failures=tuple(str(item) for item in payload.get("threshold_failures", [])),
    )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        msg = f"unable to read artifact `{path}`: {error}"
        raise BaselineError(msg) from error
    if not isinstance(payload, dict):
        msg = f"artifact `{path}` must be a JSON object"
        raise BaselineError(msg)
    return payload


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


# Keep dataclass helper available for future nested conversions.
_ = is_dataclass
