"""JSON Schema grader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from holds.domain.errors import GraderError
from holds.domain.models import GraderEvidence, GraderSpec


class JsonSchemaGrader:
    """Validate structured agent output against a JSON Schema."""

    @property
    def version_tag(self) -> str:
        return "json_schema:1"

    def grade(
        self,
        *,
        spec: GraderSpec,
        output: dict[str, Any],
        expected: dict[str, Any],
        suite_dir: Path,
    ) -> GraderEvidence:
        del expected
        grader_id = spec.id or "json_schema"
        schema = _load_schema(spec.schema, suite_dir)
        try:
            validator = Draft202012Validator(schema)
            validator.validate(output)
        except SchemaError as error:
            msg = f"invalid JSON Schema: {error.message}"
            raise GraderError(msg) from error
        except ValidationError as error:
            return GraderEvidence(
                grader_id=grader_id,
                grader_type="json_schema",
                passed=False,
                message=f"schema validation failed: {error.message}",
                details={"path": list(error.path), "validator": error.validator},
            )
        return GraderEvidence(
            grader_id=grader_id,
            grader_type="json_schema",
            passed=True,
            message="schema valid",
        )


def _load_schema(schema: str | dict[str, Any] | None, suite_dir: Path) -> dict[str, Any]:
    if schema is None:
        msg = "json_schema grader requires `schema`"
        raise GraderError(msg)
    if isinstance(schema, dict):
        return schema
    path = Path(schema)
    if not path.is_absolute():
        path = suite_dir / path
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        msg = f"unable to load schema `{path}`: {error}"
        raise GraderError(msg) from error
    if not isinstance(payload, dict):
        msg = f"schema at `{path}` must be a JSON object"
        raise GraderError(msg)
    return payload
