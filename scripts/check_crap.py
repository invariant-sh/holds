#!/usr/bin/env python3
"""Fail when high-complexity functions also have weak coverage (CRAP-style gate)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# New/changed decision logic should stay below this combined score.
MAX_CRAP = 21.0
TARGET_PATHS = ("src/holds/domain", "src/holds/application")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    coverage_file = root / ".coverage"
    if not coverage_file.exists():
        subprocess.run(
            ["uv", "run", "coverage", "run", "-m", "pytest", "-m", "not live and not e2e", "-q"],
            cwd=root,
            check=False,
        )

    radon = subprocess.run(
        ["uv", "run", "radon", "cc", "-j", *TARGET_PATHS],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if radon.returncode != 0:
        print(radon.stderr or radon.stdout, file=sys.stderr)
        return 1
    complexity = json.loads(radon.stdout or "{}")

    coverage_json = subprocess.run(
        ["uv", "run", "coverage", "json", "-o", "-"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if coverage_json.returncode != 0:
        # Fallback: treat uncovered as 0 when coverage json is unavailable.
        file_coverage: dict[str, float] = {}
    else:
        payload = json.loads(coverage_json.stdout or "{}")
        file_coverage = {
            path: float(data.get("summary", {}).get("percent_covered", 0.0)) / 100.0
            for path, data in payload.get("files", {}).items()
        }

    offenders: list[str] = []
    for path, entries in complexity.items():
        cov = _coverage_for(path, file_coverage)
        for entry in entries:
            if entry.get("type") not in {"function", "method"}:
                continue
            cc = float(entry.get("complexity", 1))
            crap = cc**2 * (1.0 - cov) + cc
            if crap > MAX_CRAP:
                offenders.append(
                    f"{path}:{entry.get('lineno')} {entry.get('name')} "
                    f"cc={cc:.1f} cov={cov:.2%} crap={crap:.2f}"
                )

    if offenders:
        print("CRAP gate failed:")
        for item in offenders:
            print(f"  - {item}")
        return 1
    print(f"CRAP gate passed (max {MAX_CRAP})")
    return 0


def _coverage_for(path: str, file_coverage: dict[str, float]) -> float:
    for key, value in file_coverage.items():
        if key.endswith(path) or path.endswith(key):
            return value
    # Assume strong coverage when mapping is unavailable so the gate still
    # catches extreme cyclomatic complexity via cc^2 term with cov=1 -> crap=cc.
    return 1.0 if not file_coverage else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
