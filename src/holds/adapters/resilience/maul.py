"""Optional Maul resilience adapter."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from holds.domain.errors import ResilienceError
from holds.ports import ResilienceOutcome, ResilienceRequest


class NoopResilienceRunner:
    """Default runner used when Maul integration is disabled."""

    def prepare(self, request: ResilienceRequest) -> ResilienceOutcome:
        del request
        return ResilienceOutcome(report_path=None, notes="maul disabled")

    def collect(self, request: ResilienceRequest) -> ResilienceOutcome:
        del request
        return ResilienceOutcome(report_path=None, notes="maul disabled")


class MaulResilienceRunner:
    """
    Launch Maul as an optional adversity condition.

    Holds remains independently useful without Maul. This adapter only activates
    when a task declares `maul.scenarios` and a `maul` binary is available.
    """

    def __init__(self, *, maul_bin: str = "maul", work_dir: Path | None = None) -> None:
        self._maul_bin = maul_bin
        self._work_dir = work_dir

    def prepare(self, request: ResilienceRequest) -> ResilienceOutcome:
        """Validate Maul availability and materialize a temporary config."""
        if shutil.which(self._maul_bin) is None:
            msg = (
                f"`{self._maul_bin}` not found on PATH; "
                "install Maul or remove task.maul from the suite"
            )
            raise ResilienceError(msg)
        if not request.scenarios:
            return ResilienceOutcome(report_path=None, notes="no maul scenarios configured")
        work_dir = self._work_dir or Path.cwd() / ".holds" / "maul"
        work_dir.mkdir(parents=True, exist_ok=True)
        config_path = request.config_path
        if config_path is None:
            config_path = work_dir / "maul.yaml"
            config_path.write_text(
                _default_maul_config(request.scenarios, request.seed),
                encoding="utf-8",
            )
        report_path = work_dir / "reliability_report.json"
        # Validate config early so suite authors get a clear failure.
        completed = subprocess.run(
            [self._maul_bin, "--config", str(config_path), "--validate"],
            cwd=work_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            msg = "maul config validation failed: " + (
                completed.stderr or completed.stdout or "unknown error"
            )
            raise ResilienceError(msg)
        marker = {
            "scenarios": list(request.scenarios),
            "config": str(config_path),
            "report": str(report_path),
        }
        (work_dir / "holds_maul_session.json").write_text(
            json.dumps(marker, indent=2) + "\n",
            encoding="utf-8",
        )
        return ResilienceOutcome(
            report_path=report_path,
            notes="maul validated; point the agent at Maul via OPENAI_BASE_URL/MAUL_BASE_URL",
        )

    def collect(self, request: ResilienceRequest) -> ResilienceOutcome:
        """Attach an existing Maul report when present."""
        work_dir = self._work_dir or Path.cwd() / ".holds" / "maul"
        report_path = work_dir / "reliability_report.json"
        if not report_path.exists():
            return ResilienceOutcome(
                report_path=None,
                notes="maul report not found after attempt",
            )
        del request
        return ResilienceOutcome(report_path=report_path, notes="maul report attached")


def _default_maul_config(scenarios: tuple[str, ...], seed: int | None) -> str:
    scenario_list = ", ".join(f'"{item}"' for item in scenarios)
    seed_value = 42 if seed is None else seed
    return (
        "proxy_listen: 127.0.0.1:0\n"
        "upstream_base_url: https://api.openai.com\n"
        f"scenarios: [{scenario_list}]\n"
        "probability: 1.0\n"
        f"seed: {seed_value}\n"
        "budget:\n"
        "  max_llm_calls: 20\n"
        "  max_cost_usd: 1.0\n"
    )
