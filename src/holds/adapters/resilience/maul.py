"""Optional Maul resilience adapter.

Starts an isolated Maul proxy per attempt, injects `MAUL_BASE_URL` /
`OPENAI_BASE_URL`, then tears the process down and attaches its report.
Holds remains independently useful when Maul is not enabled.
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from holds.domain.errors import ResilienceError
from holds.ports import ResilienceOutcome, ResilienceRequest

LISTEN_WAIT_SECONDS = 5.0
TERMINATE_WAIT_SECONDS = 5.0
AGENT_BASE_URL_KEYS = ("MAUL_BASE_URL", "OPENAI_BASE_URL")


class NoopResilienceRunner:
    """Default runner used when Maul integration is disabled."""

    def prepare(self, request: ResilienceRequest) -> ResilienceOutcome:
        del request
        return ResilienceOutcome(report_path=None, notes="maul disabled", env={})

    def collect(self, request: ResilienceRequest) -> ResilienceOutcome:
        del request
        return ResilienceOutcome(report_path=None, notes="maul disabled", env={})


@dataclass
class _LiveSession:
    process: subprocess.Popen[str]
    work_dir: Path
    report_path: Path
    address: str


class MaulResilienceRunner:
    """Launch Maul as an optional adversity condition for one attempt."""

    def __init__(self, *, maul_bin: str = "maul", work_dir: Path | None = None) -> None:
        self._maul_bin = maul_bin
        self._work_dir = work_dir
        self._sessions: dict[str, _LiveSession] = {}

    def prepare(self, request: ResilienceRequest) -> ResilienceOutcome:
        """Validate Maul, bind an isolated proxy, and return agent env vars."""
        self._require_binary()
        if not request.scenarios and request.config_path is None:
            return ResilienceOutcome(report_path=None, notes="no maul scenarios configured", env={})
        session_key = _session_key(request)
        self._stop_session(session_key)
        work_dir = self._attempt_dir(request)
        work_dir.mkdir(parents=True, exist_ok=True)
        address = _reserve_loopback_address()
        config_path = _materialize_config(request, work_dir, address)
        self._validate_config(config_path, work_dir)
        process = self._spawn(config_path, work_dir)
        if not _wait_for_listener(address):
            _terminate(process)
            msg = f"maul did not listen on {address} within {LISTEN_WAIT_SECONDS:.0f}s"
            raise ResilienceError(msg)
        report_path = work_dir / "reliability_report.json"
        self._sessions[session_key] = _LiveSession(
            process=process,
            work_dir=work_dir,
            report_path=report_path,
            address=address,
        )
        return ResilienceOutcome(
            report_path=report_path,
            notes=f"maul listening on {address}",
            env=_proxy_env(address),
        )

    def collect(self, request: ResilienceRequest) -> ResilienceOutcome:
        """Stop the attempt-scoped Maul process and attach its report."""
        session_key = _session_key(request)
        session = self._sessions.pop(session_key, None)
        if session is None:
            work_dir = self._attempt_dir(request)
            report_path = work_dir / "reliability_report.json"
            if report_path.exists():
                return _outcome_from_report(report_path, notes="maul report attached")
            return ResilienceOutcome(report_path=None, notes="maul report not found after attempt")
        _terminate(session.process)
        if not session.report_path.exists():
            return ResilienceOutcome(
                report_path=None,
                notes="maul report not found after attempt",
            )
        return _outcome_from_report(session.report_path, notes="maul report attached")

    def _require_binary(self) -> None:
        if _is_python_script(self._maul_bin):
            if Path(self._maul_bin).exists():
                return
        elif shutil.which(self._maul_bin) is not None:
            return
        msg = (
            f"`{self._maul_bin}` not found on PATH; install Maul or remove task.maul from the suite"
        )
        raise ResilienceError(msg)

    def _validate_config(self, config_path: Path, work_dir: Path) -> None:
        completed = subprocess.run(
            [*self._argv(), "--config", str(config_path), "--validate"],
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

    def _spawn(self, config_path: Path, work_dir: Path) -> subprocess.Popen[str]:
        try:
            return subprocess.Popen(
                [*self._argv(), "--config", str(config_path)],
                cwd=work_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                start_new_session=True,
            )
        except OSError as error:
            msg = f"failed to start maul: {error}"
            raise ResilienceError(msg) from error

    def _attempt_dir(self, request: ResilienceRequest) -> Path:
        base = self._work_dir or Path.cwd() / ".holds" / "maul"
        return base / _session_key(request)

    def _stop_session(self, session_key: str) -> None:
        session = self._sessions.pop(session_key, None)
        if session is not None:
            _terminate(session.process)

    def _argv(self) -> list[str]:
        if _is_python_script(self._maul_bin):
            return [sys.executable, self._maul_bin]
        return [self._maul_bin]


def _session_key(request: ResilienceRequest) -> str:
    task_id = request.task_id or "task"
    attempt_id = request.attempt_id or "attempt"
    return f"{task_id}/{attempt_id}"


def _is_python_script(maul_bin: str) -> bool:
    return maul_bin.endswith(".py")


def _reserve_loopback_address() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        host, port = listener.getsockname()[:2]
        return f"{host}:{port}"


def _wait_for_listener(address: str, timeout_seconds: float = LISTEN_WAIT_SECONDS) -> bool:
    host, port_text = address.rsplit(":", 1)
    port = int(port_text)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=TERMINATE_WAIT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def _proxy_env(address: str) -> dict[str, str]:
    base_url = f"http://{address}/v1"
    return dict.fromkeys(AGENT_BASE_URL_KEYS, base_url)


def _materialize_config(request: ResilienceRequest, work_dir: Path, address: str) -> Path:
    if request.config_path is not None:
        text = request.config_path.read_text(encoding="utf-8")
    else:
        text = _default_maul_config(request.scenarios, request.seed)
    dest = work_dir / "maul.yaml"
    dest.write_text(_rewrite_listen(text, address), encoding="utf-8")
    return dest


def _rewrite_listen(text: str, address: str) -> str:
    lines: list[str] = []
    replaced = False
    for line in text.splitlines():
        if line.startswith("proxy_listen:"):
            lines.append(f"proxy_listen: {address}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.insert(0, f"proxy_listen: {address}")
    return "\n".join(lines) + "\n"


def _default_maul_config(scenarios: tuple[str, ...], seed: int | None) -> str:
    scenario_list = ", ".join(f'"{item}"' for item in scenarios)
    seed_value = 42 if seed is None else seed
    return (
        "upstream_base_url: https://api.openai.com\n"
        f"scenarios: [{scenario_list}]\n"
        "probability: 1.0\n"
        f"seed: {seed_value}\n"
        "budget:\n"
        "  max_llm_calls: 20\n"
        "  max_cost_usd: 1.0\n"
    )


def _outcome_from_report(report_path: Path, *, notes: str) -> ResilienceOutcome:
    unrecovered, recovery = _report_session_metrics(report_path)
    return ResilienceOutcome(
        report_path=report_path,
        notes=notes,
        unrecovered_sessions=unrecovered,
        recovery_events=recovery,
    )


def _report_session_metrics(report_path: Path) -> tuple[int | None, int | None]:
    try:
        document = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    if not isinstance(document, dict):
        return None, None
    summary = document.get("summary") or {}
    if not isinstance(summary, dict):
        return None, None
    unrecovered = _optional_int(summary.get("unrecovered_sessions"))
    recovery = _optional_int(summary.get("recovery_events"))
    if recovery is None:
        recovery = _optional_int(summary.get("post_fault_successes"))
    return unrecovered, recovery


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
