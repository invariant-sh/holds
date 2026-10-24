#!/usr/bin/env python3
"""Fail the mutation job using mutmut 2's ``run`` status bits.

mutmut 3 ``run`` and ``results`` exit 0 even when mutants survive, time out,
or look suspicious. mutmut 2 failed the process with these bits (OR-ed):

* 2 — mutants survived
* 4 — mutants timed out
* 8 — mutants were suspicious

This suite is not at a 100% kill rate, so bit 2 is raised only when the
survivor count goes above the measured baseline. Timeouts and suspicious
results still fail immediately. A run that killed nothing is a setup
failure (exit 1): an empty result, or every mutant left as ``no tests``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path

SURVIVED_BIT = 2
TIMEOUT_BIT = 4
SUSPICIOUS_BIT = 8
FATAL_BIT = 1

# mutmut 3.8.0, domain + application only. Raise bit 2 above this count.
# Update after a deliberate test or mutation-set change, not to hide a drop.
MAX_SURVIVED = 435

_REQUIRED_KEYS = ("killed", "survived", "timeout", "suspicious", "total")
_DEFAULT_STATS = Path("mutants/mutmut-cicd-stats.json")


def exit_code_for_stats(stats: Mapping[str, object]) -> int:
    """Return the mutmut 2-compatible exit code for one stats payload."""
    counts = {key: _count(stats, key) for key in _REQUIRED_KEYS}
    survived = counts["survived"]
    timeout = counts["timeout"]
    suspicious = counts["suspicious"]
    killed = counts["killed"]
    total = counts["total"]

    if total <= 0 or killed <= 0:
        return FATAL_BIT

    code = 0
    if survived > MAX_SURVIVED:
        code |= SURVIVED_BIT
    if timeout > 0:
        code |= TIMEOUT_BIT
    if suspicious > 0:
        code |= SUSPICIOUS_BIT
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stats_path",
        nargs="?",
        type=Path,
        default=_DEFAULT_STATS,
        help="Path to mutmut export-cicd-stats JSON",
    )
    args = parser.parse_args(argv)
    stats_path: Path = args.stats_path

    if not stats_path.is_file():
        print(f"mutation gate: stats file not found: {stats_path}", file=sys.stderr)
        return FATAL_BIT

    try:
        payload = json.loads(stats_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"mutation gate: invalid JSON in {stats_path}: {exc}", file=sys.stderr)
        return FATAL_BIT

    if not isinstance(payload, dict):
        print(f"mutation gate: expected a JSON object in {stats_path}", file=sys.stderr)
        return FATAL_BIT

    try:
        code = exit_code_for_stats(payload)
    except ValueError as exc:
        print(f"mutation gate: {exc}", file=sys.stderr)
        return FATAL_BIT

    summary = " ".join(f"{key}={payload.get(key)}" for key in _REQUIRED_KEYS)
    print(f"mutation stats: {summary}")
    if code == 0:
        print("mutation gate passed")
        return 0

    reasons: list[str] = []
    if code & SURVIVED_BIT:
        reasons.append(f"surviving mutants above baseline {MAX_SURVIVED}")
    if code & TIMEOUT_BIT:
        reasons.append("timed-out mutants")
    if code & SUSPICIOUS_BIT:
        reasons.append("suspicious mutants")
    if code == FATAL_BIT:
        reasons.append("no killed mutants to gate on")
    print(f"mutation gate failed ({', '.join(reasons)})", file=sys.stderr)
    return code


def _count(stats: Mapping[str, object], key: str) -> int:
    if key not in stats:
        raise ValueError(f"stats missing required key {key!r}")
    value = stats[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"stats key {key!r} must be a number, got {value!r}")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"stats key {key!r} must be an integer, got {value!r}")
    count = int(value)
    if count < 0:
        raise ValueError(f"stats key {key!r} must be >= 0, got {count}")
    return count


if __name__ == "__main__":
    raise SystemExit(main())
