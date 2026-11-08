"""A conservative, single-frame geometric screen; not a player rating or pass prediction.

Input is already-audited tracking in physical metres, not event coordinates. The caller
must supply the complete active opponent IDs from independently verified lineup intervals.
No provider adapter or inferred tracking is supplied by this module.
"""

import math
from typing import Any

VERSION = "fil-support-geometry-test-1"


def segment_clearance(
    ball: list[float], target: list[float], defenders: list[list[float]]
) -> float:
    """Return nearest defender distance to the finite ball-to-target segment, in metres."""
    dx, dy = target[0] - ball[0], target[1] - ball[1]
    length2 = dx * dx + dy * dy
    if length2 == 0 or not defenders:
        raise ValueError("A nonzero segment and at least one defender are required")
    return min(
        math.hypot(p[0] - (ball[0] + t * dx), p[1] - (ball[1] + t * dy))
        for p in defenders
        for t in [max(0.0, min(1.0, ((p[0] - ball[0]) * dx + (p[1] - ball[1]) * dy) / length2))]
    )


def support_geometry(frame: dict[str, Any], active_opponents: set[int] | None) -> dict[str, Any]:
    """Screen observed teammates for a geometrically clear ball-to-player line in one frame.

    Distances 8–25 m and clearance 2 m are illustrative design parameters, not learned or
    football-validated thresholds. Incomplete player/ball coverage abstains, never returns zero.
    """
    required = {
        "source_id",
        "frame_id",
        "period",
        "timestamp",
        "coordinate_units",
        "ball_in_play",
        "ball",
        "ball_detected",
        "possession_team_id",
        "carrier_id",
        "players",
    }
    if not isinstance(frame, dict) or set(frame) != required:
        raise ValueError("Expected a complete normalized frame contract")
    if (
        not isinstance(frame["source_id"], str)
        or not frame["source_id"]
        or type(frame["frame_id"]) is not int
        or frame["frame_id"] < 0
        or type(frame["period"]) is not int
        or frame["period"] not in (1, 2, 3, 4)
        or not isinstance(frame["timestamp"], str)
        or not frame["timestamp"]
        or frame["coordinate_units"] != "metres"
        or type(frame["ball_in_play"]) is not bool
        or type(frame["ball_detected"]) is not bool
        or type(frame["possession_team_id"]) is not int
        or type(frame["carrier_id"]) is not int
        or not isinstance(frame["players"], list)
    ):
        raise ValueError("Invalid frame identity, units, possession or player list")
    result = {
        "version": VERSION,
        "source_id": frame["source_id"],
        "frame_id": frame["frame_id"],
        "period": frame["period"],
        "timestamp": frame["timestamp"],
        "options": None,
        "abstention": None,
        "definition": {
            "distance_m": [8, 25],
            "minimum_segment_clearance_m": 2,
            "domain": "Observed in-play single frame; no extrapolated player positions.",
            "meaning": "Static geometric screen only; not pass feasibility, intent or value.",
            "limits": "Illustrative thresholds; observed teammates only; no ability, "
            "success or causal claim.",
        },
    }
    if not frame["ball_in_play"]:
        result["abstention"] = "Ball is out of play."
        return result
    if active_opponents is None:
        result["abstention"] = "Active opponent coverage is uncertified."
        return result
    if (
        not isinstance(active_opponents, set)
        or not active_opponents
        or any(type(pid) is not int for pid in active_opponents)
    ):
        raise ValueError("Expected nonempty verified opponent IDs")

    def point(value: Any) -> bool:
        return (
            isinstance(value, (tuple, list))
            and len(value) == 2
            and all(type(x) in (int, float) and math.isfinite(x) for x in value)
        )

    if frame["ball"] is None or not frame["ball_detected"]:
        result["abstention"] = "Ball position is unobserved."
        return result
    if not point(frame["ball"]):
        raise ValueError("Invalid ball position")
    players = {}
    for player in frame["players"]:
        if (
            not isinstance(player, dict)
            or set(player) != {"player_id", "team_id", "position", "detected"}
            or type(player["player_id"]) is not int
            or type(player["team_id"]) is not int
            or type(player["detected"]) is not bool
        ):
            raise ValueError("Invalid tracked player")
        pid = player["player_id"]
        if pid in players:
            raise ValueError("Duplicate player identity in frame")
        if player["position"] is not None and not point(player["position"]):
            raise ValueError("Invalid player position")
        players[pid] = player
    carrier = players.get(frame["carrier_id"])
    if (
        not carrier
        or carrier["team_id"] != frame["possession_team_id"]
        or not carrier["detected"]
        or carrier["position"] is None
    ):
        result["abstention"] = "Ball carrier position is unavailable."
        return result
    if any(
        pid not in players
        or players[pid]["team_id"] == frame["possession_team_id"]
        or not players[pid]["detected"]
        or players[pid]["position"] is None
        for pid in active_opponents
    ) or any(
        p["team_id"] != frame["possession_team_id"] and pid not in active_opponents
        for pid, p in players.items()
    ):
        result["abstention"] = "Opponent identities or observed positions are incomplete."
        return result
    result["unobserved_teammate_ids"] = sorted(
        pid
        for pid, p in players.items()
        if p["team_id"] == frame["possession_team_id"]
        and (not p["detected"] or p["position"] is None)
    )
    ball = frame["ball"]
    options = []
    for pid, p in players.items():
        if (
            p["team_id"] != frame["possession_team_id"]
            or pid == frame["carrier_id"]
            or not p["detected"]
            or p["position"] is None
        ):
            continue
        dx, dy = p["position"][0] - ball[0], p["position"][1] - ball[1]
        length2 = dx * dx + dy * dy
        if not 8 <= math.sqrt(length2) <= 25:
            continue
        clearance = segment_clearance(
            ball, p["position"], [players[oid]["position"] for oid in active_opponents]
        )
        if clearance >= 2:
            options.append(
                {
                    "player_id": pid,
                    "distance_m": math.sqrt(length2),
                    "nearest_opponent_segment_distance_m": clearance,
                }
            )
    result["options"] = sorted(options, key=lambda o: o["player_id"])
    return result
