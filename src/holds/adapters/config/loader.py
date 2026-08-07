"""YAML suite loading and validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from holds.domain.errors import SuiteValidationError
from holds.domain.models import (
    AgentSpec,
    GraderSpec,
    GraderType,
    MaulCondition,
    Suite,
    SuiteDefaults,
    TaskSpec,
    Thresholds,
)

SUPPORTED_VERSION = 1
ALLOWED_GRADER_TYPES: set[str] = {"exact", "exact_field", "json_schema", "python"}


def compute_suite_hash(raw: bytes) -> str:
    """Return a stable content hash for suite provenance."""
    return hashlib.sha256(raw).hexdigest()


class YamlSuiteLoader:
    """Load and validate `holds.yaml` documents."""

    def load(self, path: Path) -> Suite:
        """Parse a suite file into a typed Suite."""
        try:
            raw = path.read_bytes()
        except OSError as error:
            msg = f"unable to read suite file `{path}`: {error}"
            raise SuiteValidationError(msg) from error
        try:
            document = yaml.safe_load(raw)
        except yaml.YAMLError as error:
            msg = f"invalid YAML in `{path}`: {error}"
            raise SuiteValidationError(msg) from error
        if not isinstance(document, dict):
            msg = "suite document must be a mapping"
            raise SuiteValidationError(msg)
        return self._parse(
            document, source_path=str(path.resolve()), content_hash=compute_suite_hash(raw)
        )

    def _parse(self, document: dict[str, Any], *, source_path: str, content_hash: str) -> Suite:
        unknown = {
            str(key)
            for key in document
            if key not in {"version", "agent", "defaults", "tasks", "thresholds"}
        }
        if unknown:
            msg = f"unknown top-level fields: {sorted(unknown)}"
            raise SuiteValidationError(msg)

        version = document.get("version")
        if version != SUPPORTED_VERSION:
            msg = (
                f"unsupported suite version `{version}`; "
                f"Holds currently accepts version {SUPPORTED_VERSION}"
            )
            raise SuiteValidationError(msg)

        agent_raw = document.get("agent")
        if not isinstance(agent_raw, dict):
            msg = "agent must be a mapping"
            raise SuiteValidationError(msg)
        agent = AgentSpec(
            command=_require_str(agent_raw, "command", prefix="agent"),
            result_path=_require_str(agent_raw, "result_path", prefix="agent"),
            working_directory=_optional_str(agent_raw.get("working_directory")),
        )

        defaults_raw = document.get("defaults") or {}
        if not isinstance(defaults_raw, dict):
            msg = "defaults must be a mapping"
            raise SuiteValidationError(msg)
        defaults = SuiteDefaults(
            repeats=int(defaults_raw.get("repeats", 1)),
            timeout_seconds=float(defaults_raw.get("timeout_seconds", 90)),
            seed=_optional_int(defaults_raw.get("seed")),
        )

        tasks_raw = document.get("tasks")
        if not isinstance(tasks_raw, list) or not tasks_raw:
            msg = "tasks must be a non-empty list"
            raise SuiteValidationError(msg)
        tasks = tuple(self._parse_task(item, index) for index, item in enumerate(tasks_raw))
        thresholds = self._parse_thresholds(document.get("thresholds") or {}, prefix="thresholds")

        try:
            return Suite(
                version=int(version),
                agent=agent,
                defaults=defaults,
                tasks=tasks,
                thresholds=thresholds,
                source_path=source_path,
                content_hash=content_hash,
            )
        except ValueError as error:
            raise SuiteValidationError(str(error)) from error

    def _parse_task(self, raw: Any, index: int) -> TaskSpec:
        if not isinstance(raw, dict):
            msg = f"tasks[{index}] must be a mapping"
            raise SuiteValidationError(msg)
        unknown = {
            str(key)
            for key in raw
            if key
            not in {
                "id",
                "input",
                "expected",
                "graders",
                "thresholds",
                "repeats",
                "timeout_seconds",
                "maul",
            }
        }
        if unknown:
            msg = f"tasks[{index}] unknown fields: {sorted(unknown)}"
            raise SuiteValidationError(msg)
        task_id = _require_str(raw, "id", prefix=f"tasks[{index}]")
        input_payload = raw.get("input")
        if not isinstance(input_payload, dict):
            msg = f"tasks[{index}].input must be a mapping"
            raise SuiteValidationError(msg)
        expected = raw.get("expected") or {}
        if not isinstance(expected, dict):
            msg = f"tasks[{index}].expected must be a mapping"
            raise SuiteValidationError(msg)
        graders_raw = raw.get("graders") or []
        if not isinstance(graders_raw, list):
            msg = f"tasks[{index}].graders must be a list"
            raise SuiteValidationError(msg)
        graders = tuple(
            self._parse_grader(item, task_index=index, grader_index=grader_index)
            for grader_index, item in enumerate(graders_raw)
        )
        maul = None
        if "maul" in raw and raw["maul"] is not None:
            maul = self._parse_maul(raw["maul"], index)
        try:
            return TaskSpec(
                id=task_id,
                input=input_payload,
                expected=expected,
                graders=graders,
                thresholds=self._parse_thresholds(
                    raw.get("thresholds") or {},
                    prefix=f"tasks[{index}].thresholds",
                ),
                repeats=_optional_int(raw.get("repeats")),
                timeout_seconds=_optional_float(raw.get("timeout_seconds")),
                maul=maul,
            )
        except ValueError as error:
            raise SuiteValidationError(str(error)) from error

    def _parse_grader(self, raw: Any, *, task_index: int, grader_index: int) -> GraderSpec:
        prefix = f"tasks[{task_index}].graders[{grader_index}]"
        if not isinstance(raw, dict):
            msg = f"{prefix} must be a mapping"
            raise SuiteValidationError(msg)
        grader_type = raw.get("type")
        if grader_type not in ALLOWED_GRADER_TYPES:
            msg = f"{prefix}.type must be one of {sorted(ALLOWED_GRADER_TYPES)}"
            raise SuiteValidationError(msg)
        return GraderSpec(
            type=grader_type,  # type: ignore[arg-type]
            id=_optional_str(raw.get("id")),
            equals=raw.get("equals"),
            path=_optional_str(raw.get("path")),
            schema=raw.get("schema"),
            callable=_optional_str(raw.get("callable")),
            version=str(raw.get("version", "1")),
        )

    def _parse_maul(self, raw: Any, task_index: int) -> MaulCondition:
        prefix = f"tasks[{task_index}].maul"
        if not isinstance(raw, dict):
            msg = f"{prefix} must be a mapping"
            raise SuiteValidationError(msg)
        scenarios = raw.get("scenarios") or []
        if not isinstance(scenarios, list) or not all(isinstance(item, str) for item in scenarios):
            msg = f"{prefix}.scenarios must be a list of strings"
            raise SuiteValidationError(msg)
        try:
            return MaulCondition(
                scenarios=tuple(scenarios),
                repeats=_optional_int(raw.get("repeats")),
                config=_optional_str(raw.get("config")),
            )
        except ValueError as error:
            raise SuiteValidationError(str(error)) from error

    def _parse_thresholds(self, raw: Any, *, prefix: str) -> Thresholds:
        if not isinstance(raw, dict):
            msg = f"{prefix} must be a mapping"
            raise SuiteValidationError(msg)
        unknown = {
            str(key)
            for key in raw
            if key
            not in {
                "pass_rate_gte",
                "schema_valid_rate_gte",
                "max_regression_points",
            }
        }
        if unknown:
            msg = f"{prefix} unknown fields: {sorted(unknown)}"
            raise SuiteValidationError(msg)
        try:
            return Thresholds(
                pass_rate_gte=_optional_float(raw.get("pass_rate_gte")),
                schema_valid_rate_gte=_optional_float(raw.get("schema_valid_rate_gte")),
                max_regression_points=_optional_float(raw.get("max_regression_points")),
            )
        except ValueError as error:
            raise SuiteValidationError(str(error)) from error


def dump_canonical(document: dict[str, Any]) -> str:
    """Canonical JSON helper for tests and fingerprints."""
    return json.dumps(document, sort_keys=True, separators=(",", ":"))


def _require_str(raw: dict[str, Any], key: str, *, prefix: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"{prefix}.{key} must be a non-empty string"
        raise SuiteValidationError(msg)
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        msg = "expected string or null"
        raise SuiteValidationError(msg)
    return value


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        msg = "expected integer or null"
        raise SuiteValidationError(msg)
    return value


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = "expected number or null"
        raise SuiteValidationError(msg)
    return float(value)


# Silence unused import used only for typing documentation.
_ = GraderType
