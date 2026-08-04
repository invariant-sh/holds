"""Black-box external framework compatibility tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"


def _run_holds(example_dir: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    work = tmp_path / example_dir.name
    shutil.copytree(example_dir, work)
    # Copy shared example support next to the workdir root expectations.
    support_src = EXAMPLES / "examples_support"
    support_dst = work / "examples_support"
    if support_src.exists() and not support_dst.exists():
        shutil.copytree(support_src, support_dst)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(ROOT / "src"),
            str(work),
            str(EXAMPLES),
            env.get("PYTHONPATH", ""),
        ]
    )
    report = work / "artifacts" / "holds_report.json"
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "holds",
            "run",
            "--suite",
            str(work / "holds.yaml"),
            "--report",
            str(report),
        ],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.e2e
@pytest.mark.parametrize(
    "example_name",
    [
        "deterministic_agent",
        "crewai_agent",
        "langgraph_agent",
        "openai_compat_agent",
    ],
)
def test_framework_examples_via_cli(example_name: str, tmp_path: Path) -> None:
    completed = _run_holds(EXAMPLES / example_name, tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = tmp_path / example_name / "artifacts" / "holds_report.json"
    assert report.exists()


@pytest.mark.live
def test_live_open_model_optional(tmp_path: Path) -> None:
    if not os.environ.get("HOLDS_LIVE_BASE_URL"):
        pytest.skip("HOLDS_LIVE_BASE_URL not configured")
    completed = _run_holds(EXAMPLES / "openai_compat_agent", tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
