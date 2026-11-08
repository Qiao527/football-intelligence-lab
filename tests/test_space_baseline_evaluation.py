"""TEST_ONLY counts verify same-cohort comparisons without claiming accuracy."""

import runpy
import sys
from pathlib import Path

import pytest

scripts = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(scripts))
try:
    summarize = runpy.run_path(str(scripts / "evaluate_space_baselines.py"))["summarize"]
finally:
    sys.path.remove(str(scripts))


def test_comparison_uses_identical_comparable_cohort():
    cases = [
        {
            "split": "development",
            "eligibility": "comparable",
            "movement_status": "candidate",
            "clearance_change_m": 1.2,
            "provider_event_ids": {"off_ball_run": ["1"], "passing_option": []},
        },
        {
            "split": "development",
            "eligibility": "comparable",
            "movement_status": "not_candidate",
            "position_screen": {"status": "candidate"},
            "clearance_change_m": 2.3,
            "provider_event_ids": {"off_ball_run": [], "passing_option": []},
        },
        {
            "split": "development",
            "eligibility": "space_unavailable",
            "movement_status": "candidate",
            "clearance_change_m": None,
            "provider_event_ids": {"off_ball_run": ["2"], "passing_option": []},
        },
    ]
    result = summarize(cases)["development"]
    assert result["coverage"] == {"comparable": 2, "space_unavailable": 1}
    assert result["by_provider_role_group"]["unavailable"]["comparable"] == 2
    assert result["independent_position_unavailable"] == 1
    assert result["independent_position_rule"] == [
        {"movement": False, "position": True, "provider_overlap": False, "count": 1}
    ]
    assert sum(c["count"] for c in result["rules"]["1.0"]) == 2
    assert any(
        c["movement"] and c["spatial"] and c["provider_overlap"] for c in result["rules"]["1.0"]
    )
    assert not any(c["spatial"] for c in result["rules"]["2.0"])


def test_sampling_interval_rejects_ambiguous_grid():
    import survey_space_coverage

    with pytest.raises(ValueError):
        list(survey_space_coverage.sampled_windows([], interval=7))
