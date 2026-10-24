# Maul adversity example

Deterministic agent that classifies locally when no proxy is configured, and writes `status: degraded` when Maul injects HTTP 5xx.

Task quality and resilience stay separate:

- `classify-refund-request` has no Maul block; graders require `status: ok`.
- `classify-under-force-500` declares `maul.expected_outcome: safe_degradation`; graders require `status: degraded`. Passing graders does not mean Maul recovered the session.

```bash
# Test stand-in. A real binary is Maul v0.1.0 from the release assets:
# https://github.com/invariant-sh/maul/releases/tag/v0.1.0
export HOLDS_MAUL_BIN=../../tests/support/fake_maul.py
uv run holds run --suite holds.yaml --enable-maul --report artifacts/holds_report.json
```

See [`docs/stack-walkthrough.md`](../../docs/stack-walkthrough.md).
