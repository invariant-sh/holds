#!/usr/bin/env python3
"""Deterministic agent used by unit/integration fixtures."""

from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> int:
    input_path = Path(os.environ["HOLDS_INPUT_PATH"])
    result_path = Path(os.environ["HOLDS_RESULT_PATH"])
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    message = str(payload.get("customer_message", "")).lower()
    category = "refund_request" if "charged twice" in message or "refund" in message else "other"
    result = {
        "category": category,
        "approved_refund": False,
        "model": "deterministic-stub",
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
