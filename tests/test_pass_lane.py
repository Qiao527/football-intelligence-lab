"""Hand-authored positions check geometry and missing-data refusal."""

from copy import deepcopy

from fil.research.pass_lane import (
    passing_line_observation,
    position_screen,
    summarize_lane_timeline,
)


def example():
    return {
        "frame": 10,
        "period": 1,
        "timestamp": "00:00:01.0",
        "possession": {"group": "home team", "player_id": 1},
        "ball_data": {"x": 0, "y": 0, "is_detected": True},
        "player_data": [
            {"player_id": 1, "x": 0, "y": 0, "is_detected": True},
            {"player_id": 2, "x": 10, "y": 0, "is_detected": True},
            {"player_id": 3, "x": 5, "y": 1, "is_detected": True},
            {"player_id": 4, "x": 5, "y": 0, "is_detected": False},
        ],
    }


def test_detected_opponent_proximity_does_not_claim_a_pass_or_view():
    result = passing_line_observation(example(), {1: 10, 2: 10, 3: 20, 4: 20}, 10, 20, 2)
    assert result["status"] == "observed_geometry"
    assert result["distance_m"] == 10 and result["nearest_detected_opponent_to_segment_m"] == 1
    assert result["nearest_detected_opponent_id"] == 3
    assert result["nearest_opponent_position_m"] == [5, 1]
    assert result["near_segment_opponent_ids"] == [3] and result["view_direction"] is None


def test_missing_or_extrapolated_positions_and_duplicate_identity_abstain():
    teams = {1: 10, 2: 10, 3: 20, 4: 20}
    for change in ("target", "ball", "carrier_distance", "duplicate"):
        frame = deepcopy(example())
        if change == "target":
            frame["player_data"][1]["is_detected"] = False
        elif change == "ball":
            frame["ball_data"]["is_detected"] = False
        elif change == "carrier_distance":
            frame["player_data"][0]["x"] = 4
        else:
            frame["player_data"].append(deepcopy(frame["player_data"][2]))
        assert passing_line_observation(frame, teams, 10, 20, 2)["status"] == "insufficient_data"


def test_sampled_cue_and_followup_are_not_claimed_as_reaction_time():
    teams = {1: 10, 2: 10, 3: 20, 4: 20}
    timeline = []
    for n in range(5):
        frame = deepcopy(example())
        frame["frame"] = n * 5
        frame["timestamp"] = f"00:00:0{n // 2}.{500 * (n % 2):03d}"
        frame["player_data"][1]["x"] = 12 if n >= 3 else 10
        frame["player_data"][2]["y"] = 3 if n < 2 else 1
        timeline.append(passing_line_observation(frame, teams, 10, 20, 2))
    phases = [{"period": 1, "frame_start": -1, "frame_end": 21, "team_in_possession_id": 10}]
    result = summarize_lane_timeline(timeline, phases)
    assert result["status"] == "observed_geometry" and result["cue_frame"] == 10
    assert result["first_observed_displacement_after_cue_s"] == 0.5
    assert "reaction" not in result
    changed = deepcopy(timeline)
    changed[-1]["detected_opponent_ids"] = [3, 4]
    assert summarize_lane_timeline(changed, phases)["status"] == "insufficient_data"
    changed = deepcopy(timeline)
    changed[-1]["carrier_id"] = 9
    assert summarize_lane_timeline(changed, phases)["status"] == "insufficient_data"
    changed = deepcopy(timeline)
    changed[-1]["timestamp"] = "00:00:09.000"
    assert summarize_lane_timeline(changed, phases)["status"] == "insufficient_data"
    changed = deepcopy(timeline)
    for row in changed[:-1]:
        row["nearest_detected_opponent_to_segment_m"] = 3
    changed[-1]["nearest_detected_opponent_to_segment_m"] = 1
    assert (
        summarize_lane_timeline(changed, phases)["cue_followup"] == "no_followup_samples_after_cue"
    )


def test_position_screen_does_not_require_three_metre_movement():
    samples = [
        {"frame_id": n * 5, "ball_distance_m": 10, "nearest_detected_opponent_to_segment_m": 3}
        for n in range(5)
    ]
    temporal = {"status": "observed_geometry", "samples": samples}
    assert position_screen(temporal)["status"] == "candidate"
    samples[0]["nearest_detected_opponent_to_segment_m"] = float("nan")
    assert position_screen(temporal)["status"] == "insufficient_data"
    for sample in samples[:3]:
        sample["nearest_detected_opponent_to_segment_m"] = 1
    assert position_screen(temporal)["status"] == "not_candidate"
    assert position_screen(temporal, minimum_samples=2)["status"] == "candidate"
