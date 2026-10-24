"""Exit-code gate that replaces mutmut 2's ``run`` status bits."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.check_mutation_gate import MAX_SURVIVED, exit_code_for_stats, main


def _stats(**overrides: int) -> dict[str, int]:
    payload = {
        "killed": 624,
        "survived": MAX_SURVIVED,
        "timeout": 0,
        "suspicious": 0,
        "total": 1077,
    }
    payload.update(overrides)
    return payload


def test_baseline_survivor_count_passes() -> None:
    assert exit_code_for_stats(_stats()) == 0
    assert exit_code_for_stats(_stats(survived=0, killed=100, total=100)) == 0


def test_survivors_timeouts_and_suspicious_use_mutmut2_bits() -> None:
    assert exit_code_for_stats(_stats(survived=MAX_SURVIVED + 1)) == 2
    assert exit_code_for_stats(_stats(timeout=1)) == 4
    assert exit_code_for_stats(_stats(suspicious=1)) == 8
    assert exit_code_for_stats(_stats(survived=MAX_SURVIVED + 1, timeout=1, suspicious=1)) == 14


def test_no_tests_do_not_fail_when_something_was_killed() -> None:
    assert exit_code_for_stats(_stats(killed=4, survived=0, total=9)) == 0


def test_empty_or_unkilled_run_is_fatal() -> None:
    assert exit_code_for_stats(_stats(killed=0, survived=0, total=0)) == 1
    assert exit_code_for_stats(_stats(killed=0, survived=0, total=5)) == 1


def test_missing_key_is_rejected() -> None:
    payload = _stats()
    del payload["survived"]
    with pytest.raises(ValueError, match="survived"):
        exit_code_for_stats(payload)


def test_main_reads_stats_file(tmp_path: Path) -> None:
    stats_path = tmp_path / "mutmut-cicd-stats.json"
    stats_path.write_text(json.dumps(_stats(survived=MAX_SURVIVED + 3)), encoding="utf-8")

    assert main([str(stats_path)]) == 2


def test_main_missing_file(tmp_path: Path) -> None:
    assert main([str(tmp_path / "missing.json")]) == 1
