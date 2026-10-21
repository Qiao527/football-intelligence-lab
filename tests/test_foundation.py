"""Verify the installed distribution rather than adding the source tree to sys.path."""

import json
import subprocess
import sys
import tomllib
from importlib.metadata import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_imports_outside_checkout(tmp_path: Path) -> None:
    """An isolated interpreter must resolve the installed fil package from any cwd."""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import fil, json; print(json.dumps({'file': fil.__file__}))",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    package_file = Path(json.loads(result.stdout)["file"])
    assert package_file.is_file()
    assert package_file.name == "__init__.py"
    assert package_file.parent.name == "fil"


def test_installed_metadata_matches_project() -> None:
    """Catch missing packaging metadata or a stale/wrong distribution installation."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    installed = metadata("football-intelligence-lab")
    assert installed["Name"] == project["name"]
    assert installed["Version"] == project["version"]
    assert {s.strip() for s in installed["Requires-Python"].split(",")} == {
        s.strip() for s in project["requires-python"].split(",")
    }
    assert installed["License-Expression"] == "MIT"
    assert installed.get_all("License-File") == ["LICENSE"]


def test_runtime_dependencies_match_scoped_project_contract() -> None:
    """Parquet storage is the only scoped runtime dependency introduced by FIL-003."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["dependencies"] == ["pyarrow==21.0.0"]
    assert metadata("football-intelligence-lab").get_all("Requires-Dist", []) == ["pyarrow==21.0.0"]


def test_supported_python_runtime() -> None:
    """The foundation is verified on Python 3.11 only."""
    assert sys.version_info[:2] == (3, 11)
