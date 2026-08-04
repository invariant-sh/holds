#!/usr/bin/env python3
"""LangGraph-shaped black-box agent using the Holds I/O contract."""

from __future__ import annotations

import json
import os
from pathlib import Path

from examples_support.openai_stub_client import chat_completion_text


def classify_node(message: str) -> str:
    prompt = f"You are a routing node. Reply with refund_request or other.\nInput: {message}"
    text = chat_completion_text(prompt).strip().lower()
    return "refund_request" if "refund" in text else "other"


def main() -> int:
    input_path = Path(os.environ["HOLDS_INPUT_PATH"])
    result_path = Path(os.environ["HOLDS_RESULT_PATH"])
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    category = classify_node(str(payload.get("customer_message", "")))
    result = {
        "category": category,
        "approved_refund": False,
        "framework": "langgraph-shaped",
        "model": os.environ.get("HOLDS_LIVE_MODEL", "stub-model"),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
