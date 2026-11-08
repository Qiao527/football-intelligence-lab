"""Synthetic matched snapshots check denominators and cluster resampling."""

import runpy
from pathlib import Path

summarize = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/evaluate_future_actions.py")
)["summarize"]
features_match = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/evaluate_future_actions.py")
)["features_match"]


def test_matched_snapshot_difference_and_unknown_are_separate():
    rows = [
        {
            "split": "development",
            "status": "matched_pass",
            "match_id": "A",
            "target_position_candidate": True,
            "action": {"pass_outcome": "successful"},
            "position_candidates": 2,
            "position_controls": 1,
            "movement_candidates": 1,
            "movement_controls": 2,
            "target_movement_candidate": False,
        },
        {
            "split": "development",
            "status": "matched_pass",
            "match_id": "B",
            "target_position_candidate": False,
            "action": {"pass_outcome": "unsuccessful"},
            "position_candidates": 1,
            "position_controls": 2,
            "movement_candidates": 1,
            "movement_controls": 2,
            "target_movement_candidate": True,
        },
        {"split": "development", "status": "insufficient_data"},
    ]
    summary = summarize(rows, draws=100)["development"]
    assert summary["matched_snapshots"] == 2
    assert summary["snapshot_status"]["insufficient_data"] == 1
    assert summary["within_snapshot_rate_difference"] == 0
    assert summary["position_exposures"] == 3 and summary["control_exposures"] == 3
    assert summary["same_snapshot_rule_comparison"] == {
        "snapshots": 2,
        "position_delta": 0,
        "movement_delta": 0.25,
        "paired_delta_difference": -0.25,
        "cluster_bootstrap_95_interval": None,
    }
    assert summary["cluster_bootstrap_95_interval"] is None
    rows.extend([{**rows[0], "match_id": name} for name in ("C", "D", "E")])
    assert summarize(rows, draws=100)["development"]["cluster_bootstrap_95_interval"] is not None


def test_source_features_are_recomputed_before_outcome_comparison():
    from fil.research.pass_lane import (
        passing_line_observation,
        position_screen,
        summarize_lane_timeline,
    )
    from fil.research.tracking_replay import movement_candidate

    teams = {1: 10, 2: 10, 3: 20}
    phases = [{"period": 1, "frame_start": -1, "frame_end": 21, "team_in_possession_id": 10}]
    frames = [
        {
            "frame": n * 5,
            "period": 1,
            "timestamp": f"00:00:0{n // 2}.{500 * (n % 2):03d}",
            "possession": {"group": "home team", "player_id": 1},
            "ball_data": {"x": 0, "y": 0, "is_detected": True},
            "player_data": [
                {"player_id": 1, "x": 0, "y": 0, "is_detected": True},
                {"player_id": 2, "x": 10, "y": 0, "is_detected": True},
                {"player_id": 3, "x": 5, "y": 3, "is_detected": True},
            ],
        }
        for n in range(5)
    ]
    movement = movement_candidate(frames, 2, 10, "home team", teams, phases, 20, 1)
    temporal = summarize_lane_timeline(
        [passing_line_observation(f, teams, 10, 20, 2) for f in frames], phases
    )
    pair = {
        "player_id": 2,
        "movement_status": movement["status"],
        "movement_displacement_m": movement["displacement_m"],
        "temporal": temporal,
        "position_screen": position_screen(temporal),
    }
    assert features_match(frames, pair, 10, "home team", teams, phases, 10, 20, 20, 1, 3)
    pair["movement_displacement_m"] = 99
    assert not features_match(frames, pair, 10, "home team", teams, phases, 10, 20, 20, 1, 3)
