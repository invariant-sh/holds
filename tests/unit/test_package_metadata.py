"""Release metadata stays aligned with the import package and CLI."""

from __future__ import annotations

import tomllib
from pathlib import Path

from holds import __version__


def test_pyproject_release_metadata() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]

    assert project["name"] == "holds"
    assert project["version"] == "0.2.0"
    assert __version__ == "0.2.0"
    assert project["description"]
    assert project["readme"] == "README.md"
    assert project["license"] == "Apache-2.0"
    assert "LICENSE" in project["license-files"]
    assert project["requires-python"] == ">=3.12"
    assert project["authors"] == [{"name": "Invariant Labs"}]
    assert project["scripts"]["holds"] == "holds.cli:app"
    assert project["urls"]["Repository"] == "https://github.com/invariant-sh/holds"
    assert project["urls"]["Changelog"].endswith("/CHANGELOG.md")
