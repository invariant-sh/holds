"""Exact value and JSON-path field graders."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from holds.domain.models import GraderEvidence, GraderSpec


class ExactGrader:
    """Compare the full output object, or a selected field, to an expected value."""

    @property
    def version_tag(self) -> str:
        return "exact:1"

    def grade(
        self,
        *,
        spec: GraderSpec,
        output: dict[str, Any],
        expected: dict[str, Any],
        suite_dir: Path,
    ) -> GraderEvidence:
        del suite_dir
        grader_id = spec.id or spec.type
        if spec.type == "exact":
            target = expected if spec.equals is None else spec.equals
            passed = output == target
            return GraderEvidence(
                grader_id=grader_id,
                grader_type="exact",
                passed=passed,
                message="exact match" if passed else "output did not exactly match expected",
                details={"expected": target, "actual": output},
            )

        if not spec.path:
            return GraderEvidence(
                grader_id=grader_id,
                grader_type="exact_field",
                passed=False,
                message="exact_field grader requires `path`",
            )
        try:
            actual = resolve_path(output, spec.path)
        except KeyError as error:
            return GraderEvidence(
                grader_id=grader_id,
                grader_type="exact_field",
                passed=False,
                message=f"path not found: {error}",
                details={"path": spec.path},
            )
        expected_value = spec.equals
        if expected_value is None and spec.path.startswith("$."):
            field = spec.path[2:]
            expected_value = expected.get(field)
        passed = actual == expected_value
        return GraderEvidence(
            grader_id=grader_id,
            grader_type="exact_field",
            passed=passed,
            message="field matched" if passed else "field mismatch",
            details={"path": spec.path, "expected": expected_value, "actual": actual},
        )


def resolve_path(payload: dict[str, Any], path: str) -> Any:
    """Resolve a minimal JSONPath-like selector: `$.a.b` or `a.b`."""
    normalized = path[2:] if path.startswith("$.") else path.lstrip("$.")
    if not normalized:
        return payload
    current: Any = payload
    for part in normalized.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current
