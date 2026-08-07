"""Integration tests for subprocess runner and end-to-end local run."""

from __future__ import annotations

import shutil
from pathlib import Path

from holds.adapters.config.loader import YamlSuiteLoader
from holds.adapters.graders import default_graders
from holds.adapters.runner.subprocess_runner import SubprocessAgentRunner
from holds.adapters.runtime import GitRevisionProvider, SystemClock, UuidFactory
from holds.adapters.storage.filesystem import FilesystemArtifactStore
from holds.application.run import RunService
from holds.ports import AgentLaunchRequest


def test_subprocess_runner_writes_and_reads_artifact(tmp_path: Path) -> None:
    agent = tmp_path / "agent.py"
    agent.write_text(
        """
import json, os
from pathlib import Path
payload = json.loads(Path(os.environ['HOLDS_INPUT_PATH']).read_text())
Path(os.environ['HOLDS_RESULT_PATH']).write_text(json.dumps({'ok': True, **payload}))
""",
        encoding="utf-8",
    )
    result_path = tmp_path / "out.json"
    input_path = tmp_path / "in.json"
    launch = SubprocessAgentRunner().run(
        AgentLaunchRequest(
            command=f"python {agent.name}",
            working_directory=tmp_path,
            result_path=result_path,
            input_path=input_path,
            input_payload={"category": "refund_request"},
            task_id="t",
            attempt_id="t-001",
            timeout_seconds=10,
            seed=1,
            env={},
        )
    )
    assert launch.exit_code == 0
    assert launch.output == {"ok": True, "category": "refund_request"}


def test_full_example_suite(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[2] / "examples" / "deterministic_agent"
    work = tmp_path / "work"
    shutil.copytree(example, work)
    suite = YamlSuiteLoader().load(work / "holds.yaml")
    service = RunService(
        agent_runner=SubprocessAgentRunner(),
        graders=default_graders(),
        clock=SystemClock(),
        ids=UuidFactory(),
        revision_provider=GitRevisionProvider(cwd=str(work)),
    )
    result = service.execute(suite)
    report = tmp_path / "report.json"
    FilesystemArtifactStore().write_run(report, result)
    assert result.summary.threshold_passed is True
    assert report.exists()
