# Maul adversity example

Deterministic agent that classifies locally when no proxy is configured, and writes `status: degraded` when Maul injects HTTP 5xx.

Task quality and resilience stay separate:

- `classify-refund-request` has no Maul block; graders require `status: ok`.
- `classify-under-force-500` declares `maul.expected_outcome: safe_degradation`; graders require `status: degraded`. Passing graders does not mean Maul recovered the session.

```bash
export HOLDS_MAUL_BIN=../../tests/support/fake_maul.py   # or a real `maul` on PATH
uv run holds run --suite holds.yaml --enable-maul --report artifacts/holds_report.json
```

See [`docs/stack-walkthrough.md`](../../docs/stack-walkthrough.md).
