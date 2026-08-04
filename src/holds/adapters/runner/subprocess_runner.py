"""Subprocess agent runner."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from subprocess import TimeoutExpired, run
from typing import Any

from holds.ports import AgentLaunchRequest, AgentLaunchResult

# Environment contract documented for external agents.
ENV_INPUT_PATH = "HOLDS_INPUT_PATH"
ENV_RESULT_PATH = "HOLDS_RESULT_PATH"
ENV_TASK_ID = "HOLDS_TASK_ID"
ENV_ATTEMPT_ID = "HOLDS_ATTEMPT_ID"
ENV_SEED = "HOLDS_SEED"
ENV_RUN_DIR = "HOLDS_RUN_DIR"


class SubprocessAgentRunner:
    """Run an agent command in a bounded subprocess."""

    def run(self, request: AgentLaunchRequest) -> AgentLaunchResult:
        """Execute one attempt and collect the declared JSON artifact."""
        request.working_directory.mkdir(parents=True, exist_ok=True)
        request.input_path.parent.mkdir(parents=True, exist_ok=True)
        request.input_path.write_text(
            json.dumps(request.input_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if request.result_path.exists():
            request.result_path.unlink()

        env = os.environ.copy()
        env.update(request.env)
        env[ENV_INPUT_PATH] = str(request.input_path)
        env[ENV_RESULT_PATH] = str(request.result_path)
        env[ENV_TASK_ID] = request.task_id
        env[ENV_ATTEMPT_ID] = request.attempt_id
        env[ENV_RUN_DIR] = str(request.working_directory)
        if request.seed is not None:
            env[ENV_SEED] = str(request.seed)

        started = time.perf_counter()
        try:
            completed = run(
                ["sh", "-c", request.command],
                cwd=request.working_directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                check=False,
            )
        except TimeoutExpired as error:
            duration_ms = int((time.perf_counter() - started) * 1000)
            stdout = error.stdout if isinstance(error.stdout, str) else ""
            stderr = error.stderr if isinstance(error.stderr, str) else "agent timed out"
            return AgentLaunchResult(
                exit_code=-1,
                duration_ms=duration_ms,
                timed_out=True,
                stdout=stdout or "",
                stderr=stderr or "agent timed out",
                output=None,
                artifact_error="agent timed out before writing result artifact",
            )

        duration_ms = int((time.perf_counter() - started) * 1000)
        output, artifact_error = _load_result_artifact(request.result_path)
        return AgentLaunchResult(
            exit_code=completed.returncode,
            duration_ms=duration_ms,
            timed_out=False,
            stdout=completed.stdout,
            stderr=completed.stderr,
            output=output,
            artifact_error=artifact_error,
        )


def _load_result_artifact(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"result artifact missing at `{path}`"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return None, f"result artifact at `{path}` is not valid JSON: {error}"
    if not isinstance(payload, dict):
        return None, f"result artifact at `{path}` must be a JSON object"
    return payload, None
