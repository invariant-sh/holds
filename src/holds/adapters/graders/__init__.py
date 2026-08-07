"""Grader registry."""

from __future__ import annotations

from holds.adapters.graders.exact import ExactGrader
from holds.adapters.graders.json_schema import JsonSchemaGrader
from holds.adapters.graders.python_callable import PythonGrader
from holds.ports import Grader


def default_graders() -> dict[str, Grader]:
    """Return the built-in grader adapters."""
    exact = ExactGrader()
    return {
        "exact": exact,
        "exact_field": exact,
        "json_schema": JsonSchemaGrader(),
        "python": PythonGrader(),
    }
