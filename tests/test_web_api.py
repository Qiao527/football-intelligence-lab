"""Public HTTP boundary tests, synthetic data only."""

import runpy
from pathlib import Path

response = runpy.run_path(str(Path(__file__).resolve().parents[1] / "web/api/index.py"))["response"]


def test_public_api_catalog_and_live_calculation():
    status, matches = response("/api/matches")
    assert status == 200 and len(matches) == 3
    for m in matches:
        status, data = response("/api/analyze?match=" + m["id"])
        assert status == 200
        assert data["report"]["provenance"]["mode"] == "synthetic"
        assert len(data["events"]) == data["report"]["source_event_count"]
    assert response("/api/analyze?match=demo-3&period=2")[1]["report"]["shot_count"] == 0


def test_public_boundary_refuses_real_matches_and_arbitrary_input():
    for query in (
        "match=8658",
        "match=demo-1&path=/etc/passwd",
        "match=demo-1&match=demo-2",
        "match=demo-1&period=5",
        "match=demo-1&team=999",
    ):
        assert response("/api/analyze?" + query)[0] == 400
    assert response("/api/unknown")[0] == 404
