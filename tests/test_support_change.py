"""Synthetic snapshots test geometry and refusal, not football outcomes."""

from copy import deepcopy
from math import sqrt

import pytest

from fil.research.support_change import support_change


def fixtures():
    start = {
        "source_id": "TEST_ONLY",
        "frame_id": 10,
        "period": 1,
        "timestamp": "00:00:01.000",
        "coordinate_units": "metres",
        "ball_in_play": True,
        "ball": [0, 0],
        "ball_detected": True,
        "possession_team_id": 10,
        "carrier_id": 1,
        "players": [
            {"player_id": 1, "team_id": 10, "position": [0, 0], "detected": True},
            {"player_id": 2, "team_id": 10, "position": [10, 0], "detected": True},
            {"player_id": 9, "team_id": 20, "position": [5, 1], "detected": True},
        ],
    }
    end = deepcopy(start)
    end.update(frame_id=30, timestamp="00:00:03.000")
    end["players"][1]["position"] = [10, 4]
    end["players"][2]["position"] = [5, 5]
    movement = {
        "status": "candidate",
        "player_id": 2,
        "team_id": 10,
        "period": 1,
        "start": [10, 0],
        "end": [10, 4],
        "frame_ids": [10, 15, 20, 25, 30],
        "timestamps": [
            "00:00:01.000",
            "00:00:01.500",
            "00:00:02.000",
            "00:00:02.500",
            "00:00:03.000",
        ],
    }
    return start, end, movement


def test_geometry_comparison_is_measured_not_attributed():
    start, end, movement = fixtures()
    result = support_change(start, end, {9}, movement)
    assert result["status"] == "observed_geometry"
    assert result["before"]["segment_clearance_m"] == 1
    assert result["after"]["segment_clearance_m"] == pytest.approx(15 / sqrt(29))
    assert result["change"]["segment_clearance_m"] == pytest.approx(15 / sqrt(29) - 1)
    assert result["frames"] == [10, 30]
    assert "causal" in result["reason"]


def test_same_player_movement_can_have_opposite_clearance_outcomes():
    start, end, movement = fixtures()
    clearer = support_change(start, end, {9}, movement)
    end["players"][2]["position"] = [5, 2]
    blocked = support_change(start, end, {9}, movement)
    assert clearer["change"]["segment_clearance_m"] > 0
    assert blocked["change"]["segment_clearance_m"] < 0


def test_missing_defender_or_provenance_refuses_comparison():
    start, end, movement = fixtures()
    end["players"][2]["detected"] = False
    assert support_change(start, end, {9}, movement)["status"] == "insufficient_data"
    start, end, movement = fixtures()
    end["timestamp"] = "00:00:03.100"
    assert support_change(start, end, {9}, movement)["status"] == "insufficient_data"
    start, end, movement = fixtures()
    movement["status"] = "insufficient_data"
    assert support_change(start, end, {9}, movement)["status"] == "insufficient_data"
    start, end, movement = fixtures()
    movement["end"] = [11, 4]
    assert support_change(start, end, {9}, movement)["status"] == "insufficient_data"
