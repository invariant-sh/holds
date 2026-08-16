# Holds Run GitHub Action

Reusable merge gate: `holds run` then optional `holds compare` against a checked-in baseline.

The suite always writes the result artifact before exiting. Threshold and regression failures still fail the job.

## Usage

```yaml
- uses: invariant-sh/holds/.github/actions/holds-run@main
  with:
    working-directory: examples/deterministic_agent
    suite: holds.yaml
    report: artifacts/holds_report.json
    baseline: baselines/accepted.json
```

This repository dogfoods the action from a relative path in `.github/workflows/ci.yml`.

## Promoting a baseline

Review the uploaded `holds_report.json`. If the quality is accepted:

```bash
uv run holds baseline \
  --run artifacts/holds_report.json \
  --output examples/deterministic_agent/baselines/accepted.json \
  --reviewer "$USER" \
  --reason "accepted deterministic fixture" \
  --force
```

Commit the new baseline. `holds compare` rejects suite, grader, agent command, model, and provider mismatches unless `--allow-incompatible` is set.
