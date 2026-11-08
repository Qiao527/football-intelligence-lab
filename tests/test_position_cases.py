"""Fictional cases verify replay selection and preserve source IDs."""

import runpy
from pathlib import Path

select = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/prepare_position_cases.py")
)["select_cases"]


def test_first_low_movement_case_per_match_is_selected():
    row = {
        "match_id": "TEST_ONLY",
        "eligibility": "comparable",
        "movement_status": "not_candidate",
        "position_screen": {"status": "candidate"},
        "period": 1,
        "frame": 100,
        "center_timestamp": "00:00:10.000",
        "player_id": 7,
    }
    rows = [
        row,
        {**row, "frame": 200},
        {**row, "match_id": "OTHER", "movement_status": "candidate"},
    ]
    result = select({"rows": rows})
    assert list(result) == ["TEST_ONLY"]
    assert result["TEST_ONLY"][0]["frame_id"] == 100
    assert result["TEST_ONLY"][0]["candidate_player_ids"] == [7]


def test_first_weak_reference_overlap_adds_one_case():
    row = {
        "match_id": "TEST_ONLY",
        "eligibility": "comparable",
        "movement_status": "not_candidate",
        "position_screen": {"status": "candidate"},
        "period": 1,
        "frame": 100,
        "center_timestamp": "00:00:10.000",
        "player_id": 7,
    }
    overlap = {**row, "frame": 200, "provider_event_ids": {"passing_option": ["TEST"]}}
    assert [x["frame_id"] for x in select({"rows": [row, overlap, overlap]})["TEST_ONLY"]] == [
        100,
        200,
    ]
