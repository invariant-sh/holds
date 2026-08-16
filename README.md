# Holds

**Continuous task evaluation and regression harness for LLM agents.**

Holds answers: **did the agent actually solve the job, consistently, for the behavior we intend to ship?**

```text
holds.yaml  →  holds run  →  report + thresholds  →  baseline / compare
```

Maul proves resilience under failure. Holds measures task quality. Vigil enforces production policy. Holds stays useful without either sibling.

Part of [Invariant Labs](https://github.com/invariant-sh). Site: [getinvariant.sh](https://getinvariant.sh).

## Status

**v0.1 local core** — suite-first evaluation with deterministic graders, repeats, baselines, CI gates, and black-box framework examples.

| Capability | Status |
|---|---|
| Versioned `holds.yaml` suite contract | ✅ |
| `holds run` / `validate` / `baseline` / `compare` | ✅ |
| Exact, JSON Schema, and trusted Python graders | ✅ |
| Repeats, timeouts, consistency metrics | ✅ |
| Threshold gates and regression comparison | ✅ |
| uv + Ruff + pytest + Astral `ty` CI | ✅ |
| Mutation and CRAP quality gates | ✅ |
| CrewAI / LangGraph / OpenAI-compatible examples | ✅ |
| Optional Maul adversity adapter | ✅ per-attempt proxy lifecycle |
| GitHub Action merge gate | ✅ `holds run` then `holds compare` |
| LLM-as-judge | 🚧 port reserved, not a default gate |

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
uv run holds --help
```

Install as a CLI from the repo:

```bash
uv pip install -e .
holds validate --suite contracts/suite.v1.example.yaml
```

## Agent I/O contract

Holds launches your agent as an external process. Frameworks are never imported by the core.

For each attempt, Holds:

1. writes a JSON input file
2. sets environment variables
3. runs `agent.command` with a timeout
4. requires the declared JSON result artifact
5. grades the artifact and records evidence

| Variable | Meaning |
|---|---|
| `HOLDS_INPUT_PATH` | Absolute path to the attempt input JSON |
| `HOLDS_RESULT_PATH` | Absolute path where the agent must write result JSON |
| `HOLDS_TASK_ID` | Task identifier |
| `HOLDS_ATTEMPT_ID` | Attempt identifier |
| `HOLDS_SEED` | Optional suite seed |
| `HOLDS_RUN_DIR` | Working directory for the attempt |

Fail-closed rule: if the result artifact is missing or not a JSON object, the attempt fails.

## Quick start

```yaml
# holds.yaml
version: 1
agent:
  command: "python agent.py"
  result_path: "artifacts/result.json"
defaults:
  repeats: 3
  timeout_seconds: 30
tasks:
  - id: classify-refund-request
    input:
      customer_message: "I was charged twice."
    expected:
      category: refund_request
    graders:
      - type: exact_field
        path: "$.category"
        equals: refund_request
    thresholds:
      pass_rate_gte: 1.0
```

```bash
uv run holds run --suite holds.yaml --report artifacts/holds_report.json
uv run holds baseline --run artifacts/holds_report.json --output artifacts/baseline.json --reason "accepted local core"
uv run holds compare --candidate artifacts/holds_report.json --baseline artifacts/baseline.json
```

## Graders

Prefer deterministic graders:

- `exact` — whole-object equality
- `exact_field` — JSON field equality (`$.path`)
- `json_schema` — Draft 2020-12 schema validation
- `python` — trusted `module:function` callable

Custom Python graders are **trusted local code**, not a sandbox. Treat them like CI scripts.

## Reports and baselines

`holds run` writes:

- JSON report (`schema_version: "1"`)
- Markdown summary beside it

Baselines are immutable accepted runs. `holds compare` rejects incompatible suite/grader/model provenance unless `--allow-incompatible` is set.

Raw agent outputs are omitted from reports by default. Pass `--include-outputs` only when you accept the sensitivity risk.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format .
uv run ty check
uv run pytest -m "not live"
uv run python scripts/check_crap.py
```

Optional mutation testing:

```bash
uv run mutmut run --paths-to-mutate src/holds/domain/ --paths-to-mutate src/holds/application/
```

## External framework examples

See [`examples/`](./examples):

- deterministic stub agent (required CI)
- CrewAI-style black-box process
- LangGraph-style black-box process
- OpenAI-compatible open-model client (Ollama/vLLM-compatible)

Required CI uses a local deterministic OpenAI-compatible stub. Live provider/open-model smoke is opt-in via workflow dispatch and repository secrets.

## Optional Maul integration

Tasks may declare Maul as an adversity condition. With `--enable-maul`, Holds starts an isolated Maul process **per attempt**, injects `MAUL_BASE_URL` / `OPENAI_BASE_URL`, waits for the proxy, then tears it down and attaches `reliability_report.json`.

```bash
uv run holds run --suite holds.yaml --enable-maul
```

```yaml
maul:
  scenarios: [force_500]
  expected_outcome: safe_degradation
  repeats: 1
```

`expected_outcome` is `task_complete` (default) or `safe_degradation`. Task `passed` is grader-only; HTTP recovery never implies task success. Resilience fields on the attempt (`resilience_report_path`, `resilience_expected_outcome`, `resilience_unrecovered_sessions`) stay separate.

Override the binary with `HOLDS_MAUL_BIN` when you are not using `maul` on `PATH`.

See [`docs/stack-walkthrough.md`](./docs/stack-walkthrough.md) and [`examples/maul_adversity_agent/`](./examples/maul_adversity_agent).

## GitHub Action merge gate

`.github/actions/holds-run` runs `holds run` then optional `holds compare` against a checked-in baseline. The suite still writes the result artifact when thresholds fail.

```yaml
- uses: invariant-sh/holds/.github/actions/holds-run@main
  with:
    working-directory: examples/deterministic_agent
    suite: holds.yaml
    baseline: baselines/accepted.json
```

Promote a reviewed report with `holds baseline --force` before committing a new `baselines/accepted.json`.

## Security

See [`SECURITY.md`](./SECURITY.md). Do not commit secrets, unredacted customer data, or raw prompt captures.

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) and the [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).

## License

Licensed under the [Apache License, Version 2.0](./LICENSE).

## Related

Part of [Invariant Labs](https://github.com/invariant-sh) — [getinvariant.sh](https://getinvariant.sh).

| Tool | Role |
|---|---|
| **[Maul](https://github.com/invariant-sh/maul)** | Adversarial proxy — find failures |
| **Holds** (this repo) | Eval harness — measure task quality |
| **[Vigil](https://github.com/invariant-sh/vigil)** | Runtime policy SDK — prevent incidents and spend |
