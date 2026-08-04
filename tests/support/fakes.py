"""Shared test fakes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from holds.ports import AgentLaunchRequest, AgentLaunchResult


@dataclass
class FakeClock:
    value: str = "2026-08-04T12:00:00Z"

    def now_iso(self) -> str:
        return self.value


@dataclass
class FakeIds:
    def run_id(self) -> str:
        return "run-test0001"

    def attempt_id(self, task_id: str, index: int) -> str:
        return f"{task_id}-{index:03d}"


@dataclass
class FakeRevision:
    value: str | None = "abc123"

    def revision(self) -> str | None:
        return self.value


class FakeAgentRunner:
    def __init__(self, outputs: list[dict[str, Any]] | None = None, exit_code: int = 0) -> None:
        self.outputs = outputs or [{"category": "refund_request", "approved_refund": False}]
        self.exit_code = exit_code
        self.calls: list[AgentLaunchRequest] = []

    def run(self, request: AgentLaunchRequest) -> AgentLaunchResult:
        self.calls.append(request)
        output = self.outputs[min(len(self.calls) - 1, len(self.outputs) - 1)]
        return AgentLaunchResult(
            exit_code=self.exit_code,
            duration_ms=12,
            timed_out=False,
            stdout="",
            stderr="",
            output=output,
            artifact_error=None,
        )
