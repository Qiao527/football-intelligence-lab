"""TEST_ONLY examples test rule compliance, not tactical or model accuracy."""

from copy import deepcopy

import pytest

from fil.research.tracking_replay import movement_candidate


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("exact_threshold", "candidate"),
        ("above_threshold", "candidate"),
        ("below_threshold", "not_candidate"),
        ("stationary", "not_candidate"),
        ("focus_carrier", "not_candidate"),
        ("missing_frame", "insufficient_data"),
        ("duplicate_frame", "insufficient_data"),
        ("period_change", "insufficient_data"),
        ("extrapolated", "insufficient_data"),
        ("missing_position", "insufficient_data"),
        ("nan_position", "insufficient_data"),
        ("duplicate_player", "insufficient_data"),
        ("unknown_carrier", "insufficient_data"),
        ("opponent_carrier", "insufficient_data"),
        ("missing_possession", "insufficient_data"),
        ("missing_phase", "insufficient_data"),
        ("phase_boundary", "insufficient_data"),
        ("clock_jump", "insufficient_data"),
        ("clock_missing", "insufficient_data"),
    ],
)
def test_independent_synthetic_rule_examples(scenario, expected):
    frames = [
        {
            "frame": n * 5,
            "period": 1,
            "timestamp": f"00:00:0{n // 2}.{500 * (n % 2):03d}",
            "possession": {"group": "home team", "player_id": 2},
            "player_data": [{"player_id": 1, "x": n, "y": 0, "is_detected": True}],
        }
        for n in range(5)
    ]
    phases = [{"period": 1, "frame_start": -1, "frame_end": 21, "team_in_possession_id": 10}]
    if scenario == "exact_threshold":
        frames[-1]["player_data"][0]["x"] = 3
    elif scenario == "below_threshold":
        frames[-1]["player_data"][0]["x"] = 2.9
    elif scenario == "stationary":
        for frame in frames:
            frame["player_data"][0]["x"] = 0
    elif scenario == "focus_carrier":
        frames[2]["possession"]["player_id"] = 1
    elif scenario == "missing_frame":
        frames.pop(2)
    elif scenario == "duplicate_frame":
        frames.insert(2, deepcopy(frames[2]))
    elif scenario == "period_change":
        frames[2]["period"] = 2
    elif scenario == "extrapolated":
        frames[2]["player_data"][0]["is_detected"] = False
    elif scenario == "missing_position":
        frames[2]["player_data"][0]["x"] = None
    elif scenario == "nan_position":
        frames[2]["player_data"][0]["x"] = float("nan")
    elif scenario == "duplicate_player":
        frames[2]["player_data"].append(deepcopy(frames[2]["player_data"][0]))
    elif scenario == "unknown_carrier":
        frames[2]["possession"]["player_id"] = 999
    elif scenario == "opponent_carrier":
        frames[2]["possession"]["player_id"] = 3
    elif scenario == "missing_possession":
        frames[2]["possession"] = None
    elif scenario == "missing_phase":
        phases = []
    elif scenario == "phase_boundary":
        phases[0]["frame_start"] = 0
    elif scenario == "clock_jump":
        frames[2]["timestamp"] = "00:00:04.000"
    elif scenario == "clock_missing":
        frames[2]["timestamp"] = None
    result = movement_candidate(frames, 1, 10, "home team", {1: 10, 2: 10, 3: 20}, phases, 20, 1)
    assert result["status"] == expected
    if expected == "candidate":
        assert result["frame_ids"] == [0, 5, 10, 15, 20]
        assert result["timestamps"] == [frame["timestamp"] for frame in frames]
    if expected == "insufficient_data":
        assert result["displacement_m"] is None
