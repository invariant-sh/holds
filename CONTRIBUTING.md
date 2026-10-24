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

## Releasing

Publishing is a tag push. Do not put a PyPI token in the repo or in GitHub secrets.

1. Bump `version` in `pyproject.toml` and `__version__` in `src/holds/__init__.py` together. Update `CHANGELOG.md`.
2. Merge to `main`.
3. Confirm the one-time [PyPI trusted publisher](#pypi-trusted-publisher) exists.
4. Tag the release commit and push the tag: `git tag v0.2.0 && git push origin v0.2.0`. The tag must be `v` plus the package version.
5. `.github/workflows/release.yml` builds the sdist and wheel with uv, publishes to PyPI, and opens a GitHub release with those artifacts.

TestPyPI is off unless the repository variable `HOLDS_PUBLISH_TESTPYPI` is `true`. Turn it on only after the TestPyPI publisher below is configured. A failed TestPyPI job blocks the PyPI upload.

### PyPI trusted publisher

The project does not exist on PyPI yet, so this is a **pending** publisher. It creates the project on first use and does not reserve the name before that.

1. Sign in to [pypi.org](https://pypi.org) as the user who should own `holds`.
2. Open [Account → Publishing](https://pypi.org/manage/account/publishing/).
3. Add a GitHub Actions pending publisher:

   | Field | Value |
   |---|---|
   | PyPI project name | `holds` |
   | Owner | `invariant-sh` |
   | Repository name | `holds` |
   | Workflow filename | `release.yml` |
   | Environment name | `pypi` |

4. On GitHub, create an Actions environment named `pypi` (Settings → Environments). Add no secrets. Protection rules are optional.

Optional TestPyPI, only if you want a dry run before PyPI. TestPyPI accounts are separate from PyPI accounts.

1. Sign in to [test.pypi.org](https://test.pypi.org).
2. Open [Account → Publishing](https://test.pypi.org/manage/account/publishing/).
3. Add a pending publisher with the same owner, repository, and workflow filename. Set the environment name to `testpypi`.
4. Create a GitHub Actions environment named `testpypi` with no secrets.
5. Set the repository variable `HOLDS_PUBLISH_TESTPYPI` to `true`.

## Security

Report vulnerabilities privately. See [SECURITY.md](./SECURITY.md).
Holds executes `agent.command` and trusted graders — treat suite changes like CI code.
