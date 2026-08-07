"""CLI contract tests."""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from holds.application.exit_codes import ExitCode
from holds.cli import app

runner = CliRunner()


def test_validate_and_run_cli(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[2] / "examples" / "deterministic_agent"
    work = tmp_path / "work"
    shutil.copytree(example, work)
    validate = runner.invoke(app, ["validate", "--suite", str(work / "holds.yaml")])
    assert validate.exit_code == ExitCode.SUCCESS

    report = work / "artifacts" / "holds_report.json"
    result = runner.invoke(
        app,
        [
            "run",
            "--suite",
            str(work / "holds.yaml"),
            "--report",
            str(report),
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS, result.output
    assert report.exists()

    baseline = work / "artifacts" / "baseline.json"
    promoted = runner.invoke(
        app,
        [
            "baseline",
            "--run",
            str(report),
            "--output",
            str(baseline),
            "--reason",
            "accepted",
        ],
    )
    assert promoted.exit_code == ExitCode.SUCCESS, promoted.output

    compared = runner.invoke(
        app,
        [
            "compare",
            "--candidate",
            str(report),
            "--baseline",
            str(baseline),
        ],
    )
    assert compared.exit_code == ExitCode.SUCCESS, compared.output


def test_invalid_suite_exit_code(tmp_path: Path) -> None:
    suite = tmp_path / "bad.yaml"
    suite.write_text("version: 99\n", encoding="utf-8")
    result = runner.invoke(app, ["validate", "--suite", str(suite)])
    assert result.exit_code == ExitCode.INVALID_SUITE
