"""Shared infrastructure adapters."""

from __future__ import annotations

import subprocess
import uuid
from datetime import UTC, datetime


class SystemClock:
    """UTC clock for report timestamps."""

    def now_iso(self) -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class UuidFactory:
    """Identifier factory for runs and attempts."""

    def run_id(self) -> str:
        return f"run-{uuid.uuid4().hex[:12]}"

    def attempt_id(self, task_id: str, index: int) -> str:
        return f"{task_id}-{index:03d}"


class GitRevisionProvider:
    """Resolve the current git revision when available."""

    def __init__(self, cwd: str | None = None) -> None:
        self._cwd = cwd

    def revision(self) -> str | None:
        try:
            completed = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self._cwd,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        if completed.returncode != 0:
            return None
        value = completed.stdout.strip()
        return value or None
