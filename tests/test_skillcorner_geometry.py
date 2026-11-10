"""Handwritten TEST_ONLY frames verify source mapping and conservative coverage."""

import runpy
from copy import deepcopy
from pathlib import Path

from fil.research.support_geometry import support_geometry

normalize = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/probe_skillcorner_geometry.py")
)["normalize_frame"]


def source_frame():
    ids = [1, 2, *range(10, 17)]
    meta = {
        "id": 99,
        "home_team": {"id": 100},
        "away_team": {"id": 200},
        "players": [
            {
                "id": i,
                "team_id": 100 if i < 10 else 200,
                "playing_time": {
                    "sequences": [{"period": "period_1", "start_frame": 0, "end_frame": 100}]
                },
            }
            for i in ids
        ],
    }
    frame = {
        "frame": 50,
        "period": 1,
        "timestamp": "00:00:05.0",
        "possession": {"group": "home team", "player_id": 1},
        "ball_data": {"x": 0, "y": 0, "is_detected": True},
        "player_data": [
            {
                "player_id": i,
                "x": 0 if i == 1 else 10 if i == 2 else 5,
                "y": 0 if i < 10 else 3 + i - 10,
                "is_detected": True,
            }
            for i in ids
        ],
    }
    phase = [{"period": "1", "frame_start": "1", "frame_end": "99", "team_in_possession_id": "100"}]
    return frame, meta, phase


def test_provider_frame_maps_without_inventing_positions_or_losing_identity():
    source, meta, phases = source_frame()
    normalized, opponents, reason = normalize(source, meta, phases)
    assert reason is None and opponents == set(range(10, 17))
    result = support_geometry(normalized, opponents)
    assert result["source_id"] == "99" and result["frame_id"] == 50
    assert result["timestamp"] == "00:00:05.0" and result["period"] == 1
    assert [x["player_id"] for x in result["options"]] == [2]


def test_phase_boundaries_uncertified_lineups_and_extrapolation_abstain():
    source, meta, phases = source_frame()
    boundary = deepcopy(source)
    boundary["frame"] = 1
    assert normalize(boundary, meta, phases)[2] == "phase_unavailable_or_boundary"
    broken = deepcopy(meta)
    broken["players"][-1]["playing_time"]["sequences"][0]["end_frame"] = None
    assert normalize(source, broken, phases)[2] == "lineup_intervals_unavailable"
    source["player_data"][-1]["is_detected"] = False
    normalized, opponents, reason = normalize(source, meta, phases)
    assert reason is None
    assert support_geometry(normalized, opponents)["options"] is None
