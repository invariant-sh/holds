"""Attempt-scoped Maul lifecycle helpers.

Kept separate from `RunService` so suite orchestration stays below the CRAP gate.
"""

from __future__ import annotations

from dataclasses import replace

from holds.domain.models import AttemptResult, MaulCondition
from holds.ports import ResilienceOutcome, ResilienceRequest, ResilienceRunner


class ResilienceAttempt:
    """Start optional Maul conditions before an attempt and tear them down after."""

    def __init__(
        self,
        *,
        runner: ResilienceRunner | None,
        request: ResilienceRequest,
        enabled: bool,
    ) -> None:
        self._runner = runner
        self._request = request
        self._enabled = enabled
        self.prepared = ResilienceOutcome(report_path=None, env={})
        self.collected = ResilienceOutcome(report_path=None, env={})

    def __enter__(self) -> ResilienceOutcome:
        if not self._enabled or self._runner is None:
            return self.prepared
        self.prepared = self._runner.prepare(self._request)
        return self.prepared

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> bool:
        del exc, traceback
        if not self._enabled or self._runner is None:
            return False
        self.collected = self._runner.collect(self._request)
        return False


def attach_resilience(
    attempt: AttemptResult,
    collected: ResilienceOutcome | None,
    maul: MaulCondition | None,
) -> AttemptResult:
    """Copy Maul evidence onto an attempt without changing task-quality `passed`."""
    if maul is None:
        return attempt
    evidence = collected or ResilienceOutcome(report_path=None)
    report_path = str(evidence.report_path) if evidence.report_path is not None else None
    return replace(
        attempt,
        resilience_report_path=report_path,
        resilience_notes=evidence.notes,
        resilience_expected_outcome=maul.expected_outcome,
        resilience_unrecovered_sessions=evidence.unrecovered_sessions,
        resilience_recovery_events=evidence.recovery_events,
    )
