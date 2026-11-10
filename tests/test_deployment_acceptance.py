"""Acceptance-validator tests for scripts/check_deployment.py."""

import runpy
from pathlib import Path

checks_path = Path(__file__).resolve().parents[1] / "scripts" / "check_deployment.py"
checks = runpy.run_path(str(checks_path))
health_problems = checks["health_problems"]
scout_problems = checks["scout_problems"]
index_problems = checks["index_problems"]


def test_health_accepts_the_synthetic_contract_and_checks_identity():
    deployed = {"status": "ok", "mode": "synthetic-only", "commit": "a" * 40}
    assert health_problems(deployed, "a" * 40) == []
    assert health_problems(deployed, "b" * 40)
    assert health_problems({"status": "ok", "mode": "synthetic-only", "commit": None}, "a" * 40)
    assert health_problems({"status": "error", "mode": "synthetic-only"})
    assert health_problems({"status": "ok", "mode": "provider"})


def test_scout_accepts_candidate_evidence_and_rejects_abstention():
    candidates = [{"name": "Mara Vale"}, {"name": "Tess Rowe"}]
    assert scout_problems({"source_mode": "synthetic", "candidates": candidates}) == []
    assert scout_problems({"source_mode": "synthetic", "candidates": [{"name": "Mara Vale"}]})
    assert scout_problems(
        {"source_mode": "synthetic", "candidates": candidates, "abstention": "No records"}
    )
    assert scout_problems({"source_mode": "provider", "candidates": candidates})


def test_index_requires_the_find_candidates_control():
    assert index_problems("<button>Find candidates</button>") == []
    assert index_problems("<h1>Match Intelligence</h1>")
