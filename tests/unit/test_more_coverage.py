"""Broader suite-loader and failure-path coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from holds.adapters.config.loader import YamlSuiteLoader
from holds.adapters.graders.python_callable import normalize_python_result
from holds.adapters.runner.subprocess_runner import SubprocessAgentRunner
from holds.domain.errors import GraderError, SuiteValidationError
from holds.domain.models import GraderEvidence
from holds.ports import AgentLaunchRequest


def test_loader_rejects_bad_yaml_and_empty_tasks(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("version: 1\nagent: [\n", encoding="utf-8")
    with pytest.raises(SuiteValidationError, match="invalid YAML"):
        YamlSuiteLoader().load(bad)

    empty = tmp_path / "empty.yaml"
    empty.write_text(
        """
version: 1
agent:
  command: "python agent.py"
  result_path: "out.json"
tasks: []
""",
        encoding="utf-8",
    )
    with pytest.raises(SuiteValidationError, match="non-empty"):
        YamlSuiteLoader().load(empty)


def test_loader_parses_maul_block(tmp_path: Path) -> None:
    path = tmp_path / "holds.yaml"
    path.write_text(
        """
version: 1
agent:
  command: "python agent.py"
  result_path: "out.json"
tasks:
  - id: demo
    input: {x: 1}
    maul:
      scenarios: [force_500]
      repeats: 2
      expected_outcome: safe_degradation
    graders:
      - type: exact
        equals: {ok: true}
""",
        encoding="utf-8",
    )
    suite = YamlSuiteLoader().load(path)
    assert suite.tasks[0].maul is not None
    assert suite.tasks[0].maul.scenarios == ("force_500",)
    assert suite.tasks[0].maul.expected_outcome == "safe_degradation"
    assert suite.repeats_for(suite.tasks[0]) == 2


def test_normalize_python_dict_and_evidence() -> None:
    evidence = normalize_python_result(
        grader_id="g",
        result={"passed": True, "message": "ok", "details": {"x": 1}},
        callable_name="m:f",
    )
    assert evidence.passed is True
    wrapped = normalize_python_result(
        grader_id="g",
        result=GraderEvidence(
            grader_id="g",
            grader_type="python",
            passed=False,
            message="no",
        ),
        callable_name="m:f",
    )
    assert wrapped.passed is False
    with pytest.raises(GraderError):
        normalize_python_result(
            grader_id="g",
            result={"passed": True, "details": "bad"},
            callable_name="m:f",
        )


def test_subprocess_timeout_and_invalid_artifact(tmp_path: Path) -> None:
    agent = tmp_path / "slow.py"
    agent.write_text("import time\ntime.sleep(2)\n", encoding="utf-8")
    launch = SubprocessAgentRunner().run(
        AgentLaunchRequest(
            command=f"python {agent.name}",
            working_directory=tmp_path,
            result_path=tmp_path / "out.json",
            input_path=tmp_path / "in.json",
            input_payload={},
            task_id="t",
            attempt_id="t-001",
            timeout_seconds=0.2,
            seed=None,
            env={},
        )
    )
    assert launch.timed_out is True

    bad_agent = tmp_path / "bad_out.py"
    bad_agent.write_text(
        "from pathlib import Path\nimport os\n"
        "Path(os.environ['HOLDS_RESULT_PATH']).write_text('[1,2,3]')\n",
        encoding="utf-8",
    )
    launch2 = SubprocessAgentRunner().run(
        AgentLaunchRequest(
            command=f"python {bad_agent.name}",
            working_directory=tmp_path,
            result_path=tmp_path / "bad.json",
            input_path=tmp_path / "in2.json",
            input_payload={},
            task_id="t",
            attempt_id="t-002",
            timeout_seconds=5,
            seed=1,
            env={},
        )
    )
    assert launch2.artifact_error is not None
