"""Unit tests for optional Maul resilience adapter boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

from holds.adapters.resilience.maul import MaulResilienceRunner, NoopResilienceRunner
from holds.domain.errors import ResilienceError
from holds.ports import ResilienceRequest


def test_maul_runner_requires_binary(tmp_path: Path) -> None:
    runner = MaulResilienceRunner(maul_bin="maul-binary-does-not-exist", work_dir=tmp_path)
    with pytest.raises(ResilienceError, match="not found"):
        runner.prepare(
            ResilienceRequest(scenarios=("force_500",), config_path=None, repeats=1, seed=1)
        )


def test_noop_resilience_runner() -> None:
    runner = NoopResilienceRunner()
    request = ResilienceRequest(scenarios=(), config_path=None, repeats=1, seed=None)
    assert runner.prepare(request).notes == "maul disabled"
