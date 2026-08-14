# Contributing to Holds

By participating you agree to the [Code of Conduct](./CODE_OF_CONDUCT.md).
Org-wide process lives in [invariant-sh/.github](https://github.com/invariant-sh/.github/blob/main/CONTRIBUTING.md).

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest -m "not live" --cov=holds --cov-report=term-missing
uv run python scripts/check_crap.py
```

Optional black-box examples:

```bash
uv sync --extra dev --extra e2e
uv run pytest -m "e2e and not live" -q
```

## Pull requests

Target `main`. Keep PRs small. Do not commit `.env`, live suite secrets, or
unredacted agent outputs.

## Security

Report vulnerabilities privately. See [SECURITY.md](./SECURITY.md).
Holds executes `agent.command` and trusted graders — treat suite changes like CI code.
