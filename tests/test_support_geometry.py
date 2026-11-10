"""Artificial points test geometry only; they are not football observations."""

from copy import deepcopy

import pytest

from fil.research.support_geometry import support_geometry


def example_frame():
    return {
        "source_id": "TEST_ONLY", "frame_id": 12, "period": 1, "timestamp": "00:00:01.200",
        "coordinate_units": "metres", "ball_in_play": True, "ball": [0, 0],
        "ball_detected": True, "possession_team_id": 10, "carrier_id": 1,
        "players": [
            {"player_id": 1, "team_id": 10, "position": [0, 0], "detected": True},
            {"player_id": 2, "team_id": 10, "position": [10, 0], "detected": True},
            {"player_id": 3, "team_id": 10, "position": [5, 0], "detected": True},
            {"player_id": 9, "team_id": 20, "position": [5, 3], "detected": True},
        ],
    }


def test_clear_and_blocked_geometry_and_frame_provenance():
    frame = example_frame()
    result = support_geometry(frame, {9})
    assert result["frame_id"] == 12 and result["source_id"] == "TEST_ONLY"
    assert result["timestamp"] == "00:00:01.200" and result["period"] == 1
    assert result["options"] == [{"player_id": 2, "distance_m": 10.0,
                                  "nearest_opponent_segment_distance_m": 3.0}]
    frame["players"][3]["position"] = [5, 1]
    assert support_geometry(frame, {9})["options"] == []
    frame["period"] = 2
    assert support_geometry(frame, {9})["period"] == 2


def test_unobserved_or_uncertified_coverage_abstains():
    frame = example_frame()
    assert support_geometry(frame, None)["options"] is None
    frame["players"][3]["detected"] = False
    assert support_geometry(frame, {9})["options"] is None
    frame = example_frame()
    assert support_geometry(frame, {9, 11})["options"] is None
    frame["ball_detected"] = False
    assert support_geometry(frame, {9})["options"] is None
    frame = example_frame()
    frame["ball_in_play"] = False
    assert support_geometry(frame, {9})["options"] is None


def test_rejects_duplicates_invalid_and_unexpected_opponents():
    frame = example_frame()
    frame["players"].append(deepcopy(frame["players"][3]))
    with pytest.raises(ValueError, match="Duplicate"):
        support_geometry(frame, {9})
    frame = example_frame()
    frame["coordinate_units"] = "statsbomb_120x80"
    with pytest.raises(ValueError):
        support_geometry(frame, {9})
    frame = example_frame()
    frame["players"][2]["team_id"] = 20
    assert support_geometry(frame, {9})["options"] is None


def test_extrapolated_teammate_is_excluded_and_coverage_disclosed():
    frame = example_frame()
    frame["players"][2]["detected"] = False
    result = support_geometry(frame, {9})
    assert result["unobserved_teammate_ids"] == [3]
    assert [o["player_id"] for o in result["options"]] == [2]
