"""Exploratory observed geometry change, not tactical value or causal attribution."""

import math
from typing import Any

from fil.research.support_geometry import segment_clearance, support_geometry


def support_change(
    start: dict[str, Any], end: dict[str, Any], opponents: set[int], movement: dict[str, Any]
) -> dict[str, Any]:
    """Compare two observed ball-to-player segments after a valid movement screen."""
    result = {
        "status": "insufficient_data",
        "reason": "",
        "frames": [],
        "before": None,
        "after": None,
        "change": None,
    }
    if (
        movement.get("status") != "candidate"
        or len(movement.get("frame_ids", [])) != 5
        or len(movement.get("timestamps", [])) != 5
    ):
        return {**result, "reason": "A completed movement candidate is required."}
    player = movement["player_id"]
    if (
        start.get("source_id") != end.get("source_id")
        or start.get("period") != end.get("period")
        or start.get("period") != movement.get("period")
        or [start.get("frame_id"), end.get("frame_id")]
        != [movement["frame_ids"][0], movement["frame_ids"][-1]]
        or [start.get("timestamp"), end.get("timestamp")]
        != [movement["timestamps"][0], movement["timestamps"][-1]]
        or start.get("possession_team_id") != movement.get("team_id")
        or end.get("possession_team_id") != movement.get("team_id")
    ):
        return {**result, "reason": "Source, period, team or frame lineage differs."}
    metrics = []
    for frame, expected_position in zip(
        (start, end), (movement.get("start"), movement.get("end")), strict=True
    ):
        verified = support_geometry(frame, opponents)
        if verified["abstention"]:
            return {**result, "reason": verified["abstention"]}
        players = {p["player_id"]: p for p in frame["players"]}
        target = players.get(player)
        if (
            not target
            or target["team_id"] != movement["team_id"]
            or not target["detected"]
            or target["position"] is None
            or frame["carrier_id"] == player
        ):
            return {**result, "reason": "Off-ball target position is unavailable."}
        if expected_position is None or tuple(target["position"]) != tuple(expected_position):
            return {**result, "reason": "Target position differs from movement evidence."}
        ball, position = frame["ball"], target["position"]
        distance = math.dist(ball, position)
        if distance == 0:
            return {**result, "reason": "Ball and target form a zero-length segment."}
        metrics.append(
            {
                "ball_distance_m": distance,
                "segment_clearance_m": segment_clearance(
                    ball, position, [players[pid]["position"] for pid in opponents]
                ),
            }
        )
    return {
        **result,
        "status": "observed_geometry",
        "reason": "Not a pass or causal effect.",
        "frames": [start["frame_id"], end["frame_id"]],
        "before": metrics[0],
        "after": metrics[1],
        "change": {k: metrics[1][k] - metrics[0][k] for k in metrics[0]},
    }
