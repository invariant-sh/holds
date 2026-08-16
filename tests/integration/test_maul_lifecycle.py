"""End-to-end Maul lifecycle against the deterministic adversity fixture."""

from __future__ import annotations

import shutil
from pathlib import Path

from holds.adapters.config.loader import YamlSuiteLoader
from holds.adapters.graders import default_graders
from holds.adapters.resilience.maul import MaulResilienceRunner
from holds.adapters.runner.subprocess_runner import SubprocessAgentRunner
from holds.adapters.runtime import GitRevisionProvider, SystemClock, UuidFactory
from holds.application.run import RunService


def test_adversity_example_separates_quality_and_maul_evidence(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[2] / "examples" / "maul_adversity_agent"
    work = tmp_path / "work"
    shutil.copytree(example, work)
    fake_maul = Path(__file__).resolve().parents[1] / "support" / "fake_maul.py"
    suite = YamlSuiteLoader().load(work / "holds.yaml")
    service = RunService(
        agent_runner=SubprocessAgentRunner(),
        graders=default_graders(),
        clock=SystemClock(),
        ids=UuidFactory(),
        revision_provider=GitRevisionProvider(cwd=str(work)),
        resilience_runner=MaulResilienceRunner(
            maul_bin=str(fake_maul),
            work_dir=work / ".holds" / "maul",
        ),
    )
    result = service.execute(suite)
    by_task = {attempt.task_id: attempt for attempt in result.attempts}
    healthy = by_task["classify-refund-request"]
    degraded = by_task["classify-under-force-500"]
    assert healthy.passed is True
    assert healthy.resilience_report_path is None
    assert degraded.passed is True
    assert degraded.resilience_expected_outcome == "safe_degradation"
    assert degraded.resilience_report_path is not None
    assert degraded.resilience_unrecovered_sessions == 1
    assert result.summary.threshold_passed is True
