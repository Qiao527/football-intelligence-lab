"""Exercise the public release allowlist and its synthetic score boundary."""

import runpy
from pathlib import Path

import pytest

from fil.intelligence.demo import MATCHES, load_demo
from fil.intelligence.public_score import synthetic_score
from fil.research.eligibility import ordered_score

ROOT = Path(__file__).resolve().parents[1]
packager = runpy.run_path(str(ROOT / "scripts/package_public_web.py"))


def test_allowlist_and_public_score_match_local_fixture_results():
    files = packager["package"](ROOT)
    paths = {entry["file"] for entry in files}
    assert paths == set(packager["PUBLIC_FILES"])
    assert {"src/fil/intelligence/scout.py", "src/fil/intelligence/scout_fixture.py"} <= paths
    assert not any(
        p.startswith(("data/", "src/fil/research/", "src/fil/ingestion/")) for p in paths
    )
    assert {p for p in paths if p.endswith(".json")} == {"vercel.json"}
    assert len(packager["manifest"](files)["files"]) == len(paths)
    for match in MATCHES:
        raw, metadata, _ = load_demo(match)
        assert synthetic_score(raw, metadata) == ordered_score(raw, metadata)
        raw[0]["id"] = "other-source"
        with pytest.raises(ValueError, match="built-in fictional"):
            synthetic_score(raw, metadata)


def test_missing_allowlisted_source_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="Missing or unsafe"):
        packager["package"](tmp_path)
