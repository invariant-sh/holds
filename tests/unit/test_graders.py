"""Grader adapter tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from holds.adapters.graders.exact import ExactGrader
from holds.adapters.graders.json_schema import JsonSchemaGrader
from holds.adapters.graders.python_callable import PythonGrader, normalize_python_result
from holds.domain.errors import GraderError
from holds.domain.models import GraderSpec


def test_exact_field_grader() -> None:
    grader = ExactGrader()
    evidence = grader.grade(
        spec=GraderSpec(type="exact_field", path="$.category", equals="refund_request"),
        output={"category": "refund_request"},
        expected={},
        suite_dir=Path("."),
    )
    assert evidence.passed is True


def test_json_schema_grader(tmp_path: Path) -> None:
    schema = tmp_path / "schema.json"
    schema.write_text(
        '{"type":"object","required":["category"],"properties":{"category":{"type":"string"}}}',
        encoding="utf-8",
    )
    grader = JsonSchemaGrader()
    ok = grader.grade(
        spec=GraderSpec(type="json_schema", schema=str(schema.name)),
        output={"category": "refund_request"},
        expected={},
        suite_dir=tmp_path,
    )
    assert ok.passed is True
    bad = grader.grade(
        spec=GraderSpec(type="json_schema", schema=str(schema.name)),
        output={},
        expected={},
        suite_dir=tmp_path,
    )
    assert bad.passed is False


def test_python_grader(tmp_path: Path) -> None:
    module = tmp_path / "custom_graders.py"
    module.write_text(
        (
            "def ok(output, expected):\n"
            "    return output.get('category') == expected.get('category')\n"
        ),
        encoding="utf-8",
    )
    grader = PythonGrader()
    evidence = grader.grade(
        spec=GraderSpec(type="python", callable="custom_graders:ok"),
        output={"category": "refund_request"},
        expected={"category": "refund_request"},
        suite_dir=tmp_path,
    )
    assert evidence.passed is True


def test_normalize_python_result_rejects_invalid() -> None:
    with pytest.raises(GraderError):
        normalize_python_result(
            grader_id="x",
            result=cast(Any, object()),
            callable_name="m:f",
        )
