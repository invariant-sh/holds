"""Suite loader tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from holds.adapters.config.loader import YamlSuiteLoader
from holds.domain.errors import SuiteValidationError


def test_load_valid_suite(tmp_path: Path) -> None:
    path = tmp_path / "holds.yaml"
    path.write_text(
        """
version: 1
agent:
  command: "python agent.py"
  result_path: "artifacts/result.json"
defaults:
  repeats: 2
  timeout_seconds: 30
  seed: 9
tasks:
  - id: demo
    input: {x: 1}
    graders:
      - type: exact_field
        path: "$.category"
        equals: refund_request
""",
        encoding="utf-8",
    )
    suite = YamlSuiteLoader().load(path)
    assert suite.version == 1
    assert suite.repeats_for(suite.tasks[0]) == 2
    assert len(suite.content_hash) == 64


def test_reject_unsupported_version(tmp_path: Path) -> None:
    path = tmp_path / "holds.yaml"
    path.write_text(
        """
version: 99
agent:
  command: "python agent.py"
  result_path: "out.json"
tasks:
  - id: demo
    input: {}
""",
        encoding="utf-8",
    )
    with pytest.raises(SuiteValidationError, match="unsupported suite version"):
        YamlSuiteLoader().load(path)


def test_reject_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "holds.yaml"
    path.write_text(
        """
version: 1
agent:
  command: "python agent.py"
  result_path: "out.json"
unexpected: true
tasks:
  - id: demo
    input: {}
""",
        encoding="utf-8",
    )
    with pytest.raises(SuiteValidationError, match="unknown top-level fields"):
        YamlSuiteLoader().load(path)
