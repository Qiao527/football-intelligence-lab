"""Only original, same-period frames enter the local replay."""

import json
from copy import deepcopy

from fil.research.tracking_replay import (
    detected_trail,
    frame_distances,
    movement_candidate,
    tracking_window,
)


def test_tracking_window_preserves_source_frames_and_period(tmp_path):
    path = tmp_path / "TEST_ONLY.jsonl"
    rows = [{"frame": i, "period": 1 if i < 15 else 2} for i in range(26)]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert tracking_window(path, 10, 1, radius=10) == [rows[i] for i in (0, 5, 10)]


def test_detected_trail_breaks_on_extrapolation_missing_and_frame_gaps():
    frames = [
        {"frame": i, "player_data": points}
        for i, points in [
            (0, [{"player_id": 7, "x": 0, "y": 0, "is_detected": True}]),
            (5, [{"player_id": 7, "x": 1, "y": 1, "is_detected": False}]),
            (10, [{"player_id": 7, "x": 2, "y": 2, "is_detected": True}]),
            (20, [{"player_id": 7, "x": 4, "y": 4, "is_detected": True}]),
        ]
    ]
    assert detected_trail(frames, 7, 20) == ([0, None, 2, None, 4], [0, None, 2, None, 4])


def test_distances_do_not_treat_extrapolation_as_detected():
    frame = {
        "ball_data": {"x": 3, "y": 4, "is_detected": True},
        "player_data": [
            {"player_id": 1, "x": 0, "y": 0, "is_detected": True},
            {"player_id": 2, "x": 1, "y": 0, "is_detected": False},
            {"player_id": 3, "x": 0, "y": 4, "is_detected": True},
        ],
    }
    assert frame_distances(frame, 1, {1: 10, 2: 20, 3: 20}) == (5, 4)
    frame["ball_data"]["is_detected"] = False
    frame["player_data"][2]["is_detected"] = False
    assert frame_distances(frame, 1, {1: 10, 2: 20, 3: 20}) == (None, None)


def test_movement_screen_requires_observed_same_phase_off_ball_samples():
    frames = [
        {
            "frame": i,
            "period": 1,
            "timestamp": f"00:00:{i // 10:02d}.{(i % 10) * 100:03d}",
            "possession": {"group": "home team", "player_id": 2},
            "player_data": [{"player_id": 1, "x": i / 5, "y": 0, "is_detected": True}],
        }
        for i in (0, 5, 10, 15, 20)
    ]
    teams = {1: 10, 2: 10, 3: 20}
    phases = [
        {"period": "1", "frame_start": "-1", "frame_end": "21", "team_in_possession_id": "10"}
    ]

    def run(rows, intervals=phases):
        return movement_candidate(rows, 1, 10, "home team", teams, intervals, 20, 1)

    result = run(frames)
    assert result["status"] == "candidate" and result["displacement_m"] == 4
    assert result["frame_ids"] == [0, 5, 10, 15, 20]
    little = deepcopy(frames)
    for row in little:
        row["player_data"][0]["x"] /= 4
    assert run(little)["status"] == "not_candidate"
    assert run(frames[:-1])["status"] == "insufficient_data"
    extrapolated = deepcopy(frames)
    extrapolated[1]["player_data"][0]["is_detected"] = False
    assert run(extrapolated)["status"] == "insufficient_data"
    carried = deepcopy(frames)
    carried[2]["possession"]["player_id"] = 1
    assert run(carried)["status"] == "not_candidate"
    conflict = deepcopy(frames)
    conflict[2]["possession"]["player_id"] = 3
    assert run(conflict)["status"] == "insufficient_data"
    boundary = deepcopy(phases)
    boundary[0]["frame_start"] = "0"
    assert run(frames, boundary)["status"] == "insufficient_data"
    assert run(frames, phases * 2)["status"] == "insufficient_data"
    overlap = {**phases[0], "frame_start": "15", "frame_end": "25"}
    assert run(frames, phases + [overlap])["status"] == "insufficient_data"
    wrong_time = deepcopy(frames)
    wrong_time[2]["timestamp"] = "00:00:03.000"
    assert (
        run(wrong_time)["reason"] == "Source timestamps conflict with the sampled frame interval."
    )
    wrong_time[2]["timestamp"] = None
    assert run(wrong_time)["reason"] == "Source timestamps are missing or malformed."
    invalid_phase = deepcopy(phases)
    invalid_phase[0]["team_in_possession_id"] = ""
    assert run(frames, invalid_phase)["reason"] == "Provider phase boundaries are malformed."


def test_movement_clock_uses_source_period_not_minute_guess():
    teams = {1: 10, 2: 10}
    for period, minute in ((1, 47), (2, 0)):
        frames = [
            {
                "frame": n * 5,
                "period": period,
                "timestamp": f"00:{minute:02d}:0{n // 2}.{500 * (n % 2):03d}",
                "possession": {"group": "home team", "player_id": 2},
                "player_data": [{"player_id": 1, "x": n, "y": 0, "is_detected": True}],
            }
            for n in range(5)
        ]
        phase = [
            {"period": period, "frame_start": -1, "frame_end": 21, "team_in_possession_id": 10}
        ]
        assert (
            movement_candidate(frames, 1, 10, "home team", teams, phase, 20, period)["status"]
            == "candidate"
        )
    assert (
        movement_candidate([], 1, 10, "home team", teams, [], 20, 5)["status"]
        == "insufficient_data"
    )
