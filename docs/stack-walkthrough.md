# Stack walkthrough: Maul → Holds → Vigil

This is the shortest path through the Invariant developer wedge. Maul finds operational failures, Holds measures task quality, and Vigil turns reviewed evidence into **non-enforcing** policy suggestions.

The products stay independent. Holds judges task outcomes even when Maul is absent. Vigil does not enforce live traffic until a future gateway exists.

## Shared evidence

A useful handoff includes:

| Field | Source |
|---|---|
| Report schema and version | Maul `schema_version` (`0.1` or `0.2`) |
| Scenario, seed, and config | Maul report / Holds `task.maul` |
| Session or workflow correlation | Maul `session_id` / `run_id` when present |
| Budget and cost outcome | Maul `budget_decision`, `budget_snapshot` |
| Artifact path | Maul `reliability_report.json`, Holds run report |
| Task quality | Holds graders, `passed`, thresholds |
| Fallback-model quality | Holds baseline `threshold_passed` + `model_id` |

HTTP recovery never implies task success. Model-routing suggestions require a Holds baseline that proves the fallback model meets the quality threshold. Maul-only evidence can still suggest call caps, cost caps, circuit breakers, and tool guards.

## 1. Measure task quality with Holds

```bash
uv run holds validate --suite examples/deterministic_agent/holds.yaml
uv run holds run \
  --suite examples/deterministic_agent/holds.yaml \
  --report artifacts/holds_report.json
uv run holds compare \
  --candidate artifacts/holds_report.json \
  --baseline examples/deterministic_agent/baselines/accepted.json
```

CI packages the same sequence as [`.github/actions/holds-run`](../.github/actions/holds-run). Promote a new baseline only after reviewing the report:

```bash
uv run holds baseline \
  --run artifacts/holds_report.json \
  --output examples/deterministic_agent/baselines/accepted.json \
  --reviewer "$USER" \
  --reason "accepted quality" \
  --force
```

## 2. Attach Maul adversity without mixing outcomes

The `examples/maul_adversity_agent` suite has a healthy task and a `force_500` task whose expected outcome is `safe_degradation`.

```bash
# Real Maul on PATH, or a test stand-in:
export HOLDS_MAUL_BIN=tests/support/fake_maul.py

uv run holds run \
  --suite examples/maul_adversity_agent/holds.yaml \
  --enable-maul \
  --report artifacts/holds_adversity.json
```

Holds starts an isolated Maul process per attempt, injects `MAUL_BASE_URL` and `OPENAI_BASE_URL`, then attaches the Maul report. Task `passed` stays grader-only. Resilience fields (`resilience_report_path`, `resilience_expected_outcome`, `resilience_unrecovered_sessions`) are recorded separately.

## 3. Suggest Vigil policy from Maul 0.2 evidence

From the Vigil repository. Schema `0.1` and `0.2` are supported; other versions exit `21`.

```bash
# Caps and breakers from Maul alone
uv run vigil policy from-maul \
  contracts/maul/reliability_report.v0.2.example.json \
  --output artifacts/vigil.suggestions.yaml \
  --project support-agent

# Routing suggestions also need a Holds baseline that passed
uv run vigil policy from-maul \
  contracts/maul/reliability_report.v0.2.example.json \
  --output artifacts/vigil.suggestions.yaml \
  --project support-agent \
  --holds-baseline contracts/holds/baseline.v1.example.json
```

The draft is `status: suggested` with no owner. Review it; do not deploy it automatically.

## Boundaries

| Product | Owns | Does not own |
|---|---|---|
| Maul | Injected faults and `reliability_report.json` | Task correctness |
| Holds | Graders, thresholds, baselines, optional Maul lifecycle | Production enforcement |
| Vigil SDK | Policy schema, dry-run, suggestions | Live gateway (later) |
