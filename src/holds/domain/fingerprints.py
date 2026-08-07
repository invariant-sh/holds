"""Compatibility fingerprints for baseline comparison."""

from __future__ import annotations

from collections.abc import Sequence

from holds.domain.models import Baseline, RunResult


def compatibility_reasons(candidate: RunResult, baseline: Baseline) -> tuple[str, ...]:
    """Return reasons why a candidate is incompatible with a baseline."""
    reasons: list[str] = []
    if candidate.suite_hash != baseline.suite_hash:
        reasons.append("suite_hash mismatch")
    if candidate.suite_version != baseline.suite_version:
        reasons.append("suite_version mismatch")
    if tuple(candidate.grader_versions) != tuple(baseline.grader_versions):
        reasons.append("grader_versions mismatch")
    if candidate.agent_command != baseline.agent_command:
        reasons.append("agent_command mismatch")
    if _normalized(candidate.model_id) != _normalized(baseline.model_id):
        reasons.append("model_id mismatch")
    if _normalized(candidate.provider) != _normalized(baseline.provider):
        reasons.append("provider mismatch")
    return tuple(reasons)


def are_compatible(candidate: RunResult, baseline: Baseline) -> bool:
    """Return True when candidate and baseline share comparable provenance."""
    return not compatibility_reasons(candidate, baseline)


def grader_version_tags(versions: Sequence[str]) -> tuple[str, ...]:
    """Normalize grader version identifiers for stable storage."""
    return tuple(sorted(versions))


def _normalized(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
