"""Baseline comparison use case."""

from __future__ import annotations

from pathlib import Path

from holds.domain.errors import IncompatibleBaselineError
from holds.domain.fingerprints import are_compatible, compatibility_reasons
from holds.domain.models import ComparisonDelta, ComparisonResult, Thresholds
from holds.domain.thresholds import evaluate_regression
from holds.ports import ArtifactStore


class CompareService:
    """Compares a candidate run against an immutable baseline."""

    def __init__(self, *, store: ArtifactStore) -> None:
        self._store = store

    def compare(
        self,
        *,
        candidate_path: Path,
        baseline_path: Path,
        thresholds: Thresholds | None = None,
        allow_incompatible: bool = False,
    ) -> ComparisonResult:
        """Compare candidate and baseline, rejecting incompatible provenance by default."""
        candidate = self._store.read_run(candidate_path)
        baseline = self._store.read_baseline(baseline_path)
        reasons = compatibility_reasons(candidate, baseline)
        if reasons and not allow_incompatible:
            raise IncompatibleBaselineError("; ".join(reasons))
        if not are_compatible(candidate, baseline) and not allow_incompatible:
            return ComparisonResult(
                compatible=False,
                passed=False,
                deltas=(),
                incompatibility_reasons=reasons,
            )

        effective = thresholds or baseline.thresholds
        allowed = effective.max_regression_points
        deltas: list[ComparisonDelta] = []

        pass_ok, pass_msg, pass_delta = evaluate_regression(
            name="pass_rate",
            candidate=candidate.summary.pass_rate,
            baseline=baseline.summary.pass_rate,
            allowed_points=allowed,
        )
        deltas.append(
            ComparisonDelta(
                name="pass_rate",
                candidate=candidate.summary.pass_rate,
                baseline=baseline.summary.pass_rate,
                delta_points=pass_delta,
                allowed_regression_points=allowed,
                passed=pass_ok,
                message=pass_msg,
            )
        )

        schema_ok, schema_msg, schema_delta = evaluate_regression(
            name="schema_valid_rate",
            candidate=candidate.summary.schema_valid_rate,
            baseline=baseline.summary.schema_valid_rate,
            allowed_points=allowed,
        )
        # Only gate on schema regression when both sides reported the metric.
        schema_required = (
            candidate.summary.schema_valid_rate is not None
            and baseline.summary.schema_valid_rate is not None
        )
        deltas.append(
            ComparisonDelta(
                name="schema_valid_rate",
                candidate=candidate.summary.schema_valid_rate,
                baseline=baseline.summary.schema_valid_rate,
                delta_points=schema_delta,
                allowed_regression_points=allowed,
                passed=True if not schema_required else schema_ok,
                message=(
                    "schema_valid_rate: skipped (metric unavailable)"
                    if not schema_required
                    else schema_msg
                ),
            )
        )

        passed = all(delta.passed for delta in deltas)
        return ComparisonResult(
            compatible=not reasons,
            passed=passed,
            deltas=tuple(deltas),
            incompatibility_reasons=reasons,
        )
