"""The evaluation must detect fabricated citations, numbers and missing contrary evidence."""

import copy
import json
import runpy
from pathlib import Path

from fil.intelligence.scout import search
from fil.intelligence.scout_fixture import scout_fixture

ROOT = Path(__file__).resolve().parents[1]
evaluation = runpy.run_path(str(ROOT / "scripts/evaluate_scout.py"))


def test_reference_benchmark_and_grader_detect_corruption():
    cases = json.loads((ROOT / "docs/benchmarks/scout-copilot/cases.json").read_text())
    assert len(cases) == 36
    assert len({case["id"] for case in cases}) == len(cases)
    case = next(c for c in cases if c["id"] == "SC-10")
    events, _, _ = scout_fixture()
    result = search(case["prompt"])
    assert evaluation["grade"](case, result, events)["task_complete"]
    corrupted = copy.deepcopy(result)
    corrupted["candidates"][0]["counts"]["passes"] += 1
    corrupted["candidates"][0]["supporting_event_ids"].append("invented")
    corrupted["candidates"][0]["opposing_event_ids"] = []
    corrupted["candidates"][0]["explanation"] = "Invented superstar rating: 99"
    grades = evaluation["grade"](case, corrupted, events)
    assert not grades["numeric_correct"]
    assert not grades["citation_correct"]
    assert not grades["contradiction_correct"]
    assert not grades["explanation_whitelisted"]
    assert not grades["task_complete"]


def test_fallback_and_existing_filter_use_the_same_cases():
    cases = json.loads((ROOT / "docs/benchmarks/scout-copilot/cases.json").read_text())
    report = evaluation["evaluate"](cases)
    assert len(report["outcomes"]) == 36
    assert report["fallback_metrics"]["task_complete"]["total"] == 36
    assert report["discovery_proxy_task_completion"]["total"] == 36
    assert report["live_model_latency"] is None
    assert report["live_model_cost"] is None
