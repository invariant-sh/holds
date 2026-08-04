"""Shared helpers for example agents and e2e tests."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def chat_completion_text(prompt: str) -> str:
    """
    Call an OpenAI-compatible chat endpoint.

    Defaults to a deterministic local stub behavior when HOLDS_LIVE_BASE_URL is
    unset, so required CI never depends on a paid provider.
    """
    base_url = os.environ.get("HOLDS_LIVE_BASE_URL")
    if not base_url:
        lowered = prompt.lower()
        return "refund_request" if "refund" in lowered or "charged" in lowered else "other"

    if not base_url.startswith(("http://", "https://")):
        raise RuntimeError("HOLDS_LIVE_BASE_URL must be an http(s) URL")

    api_key = os.environ.get("HOLDS_LIVE_API_KEY", "no-key")
    model = os.environ.get("HOLDS_LIVE_MODEL", "llama3.2")
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise RuntimeError(f"open-model request failed: {error}") from error
    return str(payload["choices"][0]["message"]["content"])
