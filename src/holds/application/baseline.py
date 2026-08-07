"""Baseline promotion use case."""

from __future__ import annotations

from pathlib import Path

from holds.domain.baseline import baseline_from_run
from holds.domain.errors import BaselineError
from holds.domain.models import Baseline, Thresholds
from holds.ports import ArtifactStore, Clock


class BaselineService:
    """Promotes accepted runs into immutable baselines."""

    def __init__(self, *, store: ArtifactStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def promote(
        self,
        *,
        run_path: Path,
        baseline_path: Path,
        reviewer: str | None,
        reason: str | None,
        thresholds: Thresholds | None = None,
        force: bool = False,
    ) -> Baseline:
        """Promote a run report into a baseline artifact."""
        run = self._store.read_run(run_path)
        if not run.summary.threshold_passed and not force:
            msg = "refusing to promote a run that failed thresholds; pass force=True to override"
            raise BaselineError(msg)
        baseline = baseline_from_run(
            run,
            promoted_at=self._clock.now_iso(),
            reviewer=reviewer,
            reason=reason,
            thresholds=thresholds,
        )
        if baseline_path.exists() and not force:
            msg = f"baseline already exists at `{baseline_path}`; pass --force to replace"
            raise BaselineError(msg)
        if force and baseline_path.exists():
            baseline_path.unlink()
        self._store.write_baseline(baseline_path, baseline)
        return baseline
