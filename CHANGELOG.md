# Changelog

All notable changes to Holds are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-24

First release prepared for PyPI. Nothing is published until a maintainer pushes a `v*` tag.

### Added

- PyPI metadata for the `holds` distribution: version 0.2.0, readme, Apache-2.0 license, authors, project URLs, classifiers, `requires-python`, and the `holds` console script. The import package and CLI command stay `holds`.
- GitHub Actions workflow `.github/workflows/release.yml`. A `v*` tag builds an sdist and wheel with uv, publishes them to PyPI with Trusted Publishing (OIDC, no API token), and attaches the same artifacts to a GitHub release. TestPyPI is opt-in via the `HOLDS_PUBLISH_TESTPYPI` repository variable.
- Install instructions for `pip install holds` and `uv tool install holds`.
- Maul v0.1.0 release-asset install instructions. The missing-binary error links the checksum-verified tag.

### Changed

- Package version is 0.2.0 (`pyproject.toml` and `holds.__version__`).

## [0.1.0] - 2026-08-15

### Added

- Suite-first evaluation with `holds run`, `validate`, `baseline`, and `compare`.
- Exact, JSON Schema, and trusted Python graders, plus repeats, timeouts, thresholds, and regression comparison.
- Optional per-attempt Maul adversity adapter. Task `passed` stays grader-only.
- GitHub Action merge gate, black-box framework examples, and CI quality gates.
