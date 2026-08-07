#!/usr/bin/env python3
"""
CrewAI-shaped black-box agent.

The process speaks the Holds I/O contract. In CI it uses a deterministic local
OpenAI-compatible stub. With HOLDS_LIVE_BASE_URL set it can call a real endpoint.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from examples_support.openai_stub_client import chat_completion_text


def main() -> int:
    input_path = Path(os.environ["HOLDS_INPUT_PATH"])
    result_path = Path(os.environ["HOLDS_RESULT_PATH"])
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    message = str(payload.get("customer_message", ""))

    # CrewAI-style orchestration is represented as an external process. The
    # important part for Holds is the I/O contract, not the framework import.
    prompt = (
        "Classify the support message as refund_request or other. "
        "Return only the category token.\n\n"
        f"Message: {message}"
    )
    text = chat_completion_text(prompt).strip().lower()
    category = "refund_request" if "refund" in text else "other"
    result = {
        "category": category,
        "approved_refund": False,
        "framework": "crewai-shaped",
        "model": os.environ.get("HOLDS_LIVE_MODEL", "stub-model"),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
