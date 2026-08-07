"""Trusted custom Python graders."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from holds.domain.errors import GraderError
from holds.domain.models import GraderEvidence, GraderSpec

GraderCallable = Callable[[dict[str, Any], dict[str, Any]], bool | GraderEvidence | dict[str, Any]]


class PythonGrader:
    """
    Invoke a trusted `module:function` callable.

    Holds is not a sandbox. Custom graders execute with the privileges of the
    local Python environment and must be treated as trusted code.
    """

    @property
    def version_tag(self) -> str:
        return "python:1"

    def grade(
        self,
        *,
        spec: GraderSpec,
        output: dict[str, Any],
        expected: dict[str, Any],
        suite_dir: Path,
    ) -> GraderEvidence:
        grader_id = spec.id or (spec.callable or "python")
        if not spec.callable:
            return GraderEvidence(
                grader_id=grader_id,
                grader_type="python",
                passed=False,
                message="python grader requires `callable` in module:function form",
            )
        try:
            func = load_callable(spec.callable, suite_dir=suite_dir)
            result = func(output, expected)
        except Exception as error:
            msg = f"custom grader `{spec.callable}` failed: {error}"
            raise GraderError(msg) from error
        return normalize_python_result(
            grader_id=grader_id, result=result, callable_name=spec.callable
        )


def load_callable(path: str, *, suite_dir: Path) -> GraderCallable:
    """Import `module:function`, adding the suite directory to import path."""
    if ":" not in path:
        msg = "callable must use module:function form"
        raise GraderError(msg)
    module_name, func_name = path.split(":", 1)
    if not module_name or not func_name:
        msg = "callable must use module:function form"
        raise GraderError(msg)

    import sys

    suite_dir_str = str(suite_dir.resolve())
    inserted = False
    if suite_dir_str not in sys.path:
        sys.path.insert(0, suite_dir_str)
        inserted = True
    try:
        module = importlib.import_module(module_name)
    finally:
        if inserted and sys.path and sys.path[0] == suite_dir_str:
            sys.path.pop(0)
    try:
        func = getattr(module, func_name)
    except AttributeError as error:
        msg = f"callable `{path}` not found"
        raise GraderError(msg) from error
    if not callable(func):
        msg = f"callable `{path}` is not callable"
        raise GraderError(msg)
    return func


def normalize_python_result(
    *,
    grader_id: str,
    result: bool | GraderEvidence | dict[str, Any],
    callable_name: str,
) -> GraderEvidence:
    """Normalize custom grader return values into GraderEvidence."""
    if isinstance(result, GraderEvidence):
        return result
    if isinstance(result, bool):
        return GraderEvidence(
            grader_id=grader_id,
            grader_type="python",
            passed=result,
            message="custom grader passed" if result else "custom grader failed",
            details={"callable": callable_name},
        )
    if isinstance(result, dict):
        passed = bool(result.get("passed"))
        message = str(result.get("message") or ("passed" if passed else "failed"))
        details = result.get("details")
        if details is not None and not isinstance(details, dict):
            msg = "custom grader details must be a mapping"
            raise GraderError(msg)
        return GraderEvidence(
            grader_id=grader_id,
            grader_type="python",
            passed=passed,
            message=message,
            details=details or {"callable": callable_name},
        )
    msg = "custom grader must return bool, GraderEvidence, or dict"
    raise GraderError(msg)
