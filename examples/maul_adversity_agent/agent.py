#!/usr/bin/env python3
"""Deterministic agent that degrades when Maul injects HTTP failures."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    input_path = Path(os.environ["HOLDS_INPUT_PATH"])
    result_path = Path(os.environ["HOLDS_RESULT_PATH"])
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    message = str(payload.get("customer_message", ""))
    status = _status_from_provider(message)
    category = (
        "refund_request"
        if "charged twice" in message.lower() or "refund" in message.lower()
        else "other"
    )
    result = {
        "category": category,
        "approved_refund": False,
        "status": status,
        "model": "deterministic-stub",
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


def _status_from_provider(message: str) -> str:
    base = os.environ.get("MAUL_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    if not base:
        return "ok"
    url = base.rstrip("/") + "/chat/completions"
    body = json.dumps(
        {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": message}],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if int(response.status) >= 500:
                return "degraded"
    except urllib.error.HTTPError as error:
        if error.code >= 500:
            return "degraded"
        raise
    return "ok"


if __name__ == "__main__":
    raise SystemExit(main())
