"""Conservative 2D passing-line observations; no orientation, intent or pass prediction."""

import math
from typing import Any

from fil.research.support_geometry import segment_clearance
from fil.time.clock import ClockError, parse_period_timestamp


def passing_line_observation(
    frame: dict[str, Any], teams: dict[int, int], home_id: int, away_id: int, target_id: int
) -> dict[str, Any]:
    """Measure visible blockers; never infer unseen defenders or a player's field of view."""
    result = {
        "status": "insufficient_data",
        "reason": "",
        "frame_id": frame.get("frame"),
        "period": frame.get("period"),
        "timestamp": frame.get("timestamp"),
        "target_id": target_id,
        "carrier_id": None,
        "possession_team_id": None,
        "distance_m": None,
        "nearest_detected_opponent_to_segment_m": None,
        "nearest_detected_opponent_id": None,
        "ball_position_m": None,
        "carrier_position_m": None,
        "target_position_m": None,
        "nearest_opponent_position_m": None,
        "near_segment_opponent_ids": [],
        "detected_opponent_count": 0,
        "detected_opponent_ids": [],
        "view_direction": None,
    }
    possession = frame.get("possession") or {}
    own = {"home team": home_id, "away team": away_id}.get(possession.get("group"))
    carrier_id = possession.get("player_id")
    result["carrier_id"] = carrier_id
    result["possession_team_id"] = own
    if (
        own is None
        or teams.get(carrier_id) != own
        or teams.get(target_id) != own
        or carrier_id == target_id
    ):
        return {**result, "reason": "Provider carrier or teammate identity is unavailable."}
    tracked = frame.get("player_data")
    if not isinstance(tracked, list):
        return {**result, "reason": "Player tracking is unavailable."}
    ids = [p.get("player_id") for p in tracked]
    if len(ids) != len(set(ids)) or any(pid not in teams for pid in ids):
        return {**result, "reason": "Duplicate or unknown player identity."}

    def point(p: dict) -> list[float] | None:
        values = [p.get("x"), p.get("y")]
        if p.get("is_detected") is True and all(
            type(v) in (int, float) and math.isfinite(v) for v in values
        ):
            return values
        return None

    positions = {p["player_id"]: point(p) for p in tracked}
    carrier, target = positions.get(carrier_id), positions.get(target_id)
    ball = point(frame.get("ball_data") or {})
    if carrier is None or target is None or ball is None:
        return {**result, "reason": "Carrier, target or ball is not detected."}
    if math.dist(ball, carrier) > 3.5:
        return {**result, "reason": "Ball is more than 3.5 m from the recorded carrier."}
    distance = math.dist(ball, target)
    if distance == 0:
        return {**result, "reason": "Ball-to-target segment has zero length."}
    defenders = {
        pid: pos for pid, pos in positions.items() if teams[pid] != own and pos is not None
    }
    if not defenders:
        return {**result, "reason": "No opposing player is detected."}
    clearances = {pid: segment_clearance(ball, target, [pos]) for pid, pos in defenders.items()}
    closest = min(clearances, key=lambda pid: (clearances[pid], pid))
    return {
        **result,
        "status": "observed_geometry",
        "reason": "Detected-opponent proximity only; no field-of-view or pass-feasibility claim.",
        "distance_m": distance,
        "nearest_detected_opponent_to_segment_m": clearances[closest],
        "nearest_detected_opponent_id": closest,
        "ball_position_m": ball,
        "carrier_position_m": carrier,
        "target_position_m": target,
        "nearest_opponent_position_m": defenders[closest],
        "near_segment_opponent_ids": sorted(pid for pid, d in clearances.items() if d <= 2),
        "detected_opponent_count": len(defenders),
        "detected_opponent_ids": sorted(defenders),
    }


def summarize_lane_timeline(timeline: list[dict], phases: list[dict]) -> dict:
    """Describe sampled geometry and a cue-relative displacement, not reaction time."""
    base = {
        "status": "insufficient_data",
        "reason": "",
        "frames": [],
        "clearance_change_m": None,
        "cue_frame": None,
        "first_observed_displacement_after_cue_s": None,
        "cue_followup": None,
    }
    if len(timeline) != 5 or any(o.get("status") != "observed_geometry" for o in timeline):
        return {**base, "reason": "Five measurable observations are required."}
    try:
        frames = [o["frame_id"] for o in timeline]
        times = [parse_period_timestamp(o["timestamp"]) for o in timeline]
        period = timeline[0]["period"]
        team = timeline[0]["possession_team_id"]
        if type(period) is not int or period not in (1, 2, 3, 4):
            return {**base, "reason": "Period is unavailable or is a shootout."}
        overlaps = [
            p
            for p in phases
            if int(p["period"]) == period
            and int(p["frame_start"]) < frames[-1]
            and frames[0] < int(p["frame_end"])
        ]
        if (
            len(overlaps) != 1
            or int(overlaps[0]["frame_start"]) >= frames[0]
            or int(overlaps[0]["frame_end"]) <= frames[-1]
            or int(overlaps[0]["team_in_possession_id"]) != team
        ):
            return {**base, "reason": "Single matching provider phase is unavailable."}
    except (ClockError, TypeError, ValueError, KeyError):
        return {**base, "reason": "Frame, clock or phase metadata is malformed."}
    if (
        any(type(f) is not int for f in frames)
        or any(b - a != 5 for a, b in zip(frames, frames[1:], strict=False))
        or any(b - a != 500 for a, b in zip(times, times[1:], strict=False))
        or any(o["period"] != period or o["possession_team_id"] != team for o in timeline)
        or len({o["carrier_id"] for o in timeline}) != 1
        or len({o["target_id"] for o in timeline}) != 1
    ):
        return {**base, "reason": "Frame, clock, possession or player identity changes."}
    ids = timeline[0]["detected_opponent_ids"]
    if not ids or any(o["detected_opponent_ids"] != ids for o in timeline):
        return {**base, "reason": "Detected opponent set changes across the window."}
    clearance = [o["nearest_detected_opponent_to_segment_m"] for o in timeline]
    result = {
        **base,
        "status": "observed_geometry",
        "reason": "Same detected opponent set only; unobserved players may exist. Not causation.",
        "frames": frames,
        "clearance_change_m": clearance[-1] - clearance[0],
        "detected_opponent_ids": ids,
        "samples": [
            {
                "frame_id": o["frame_id"],
                "timestamp": o["timestamp"],
                "ball_distance_m": o["distance_m"],
                "nearest_detected_opponent_to_segment_m": o[
                    "nearest_detected_opponent_to_segment_m"
                ],
            }
            for o in timeline
        ],
    }
    for i in range(1, len(timeline)):
        if clearance[i - 1] > 2 and clearance[i] <= 2:
            result["cue_frame"] = frames[i]
            cue_position = timeline[i]["target_position_m"]
            result["cue_followup"] = (
                "no_followup_samples_after_cue"
                if i == len(timeline) - 1
                else "no_1m_displacement_observed_in_remaining_samples"
            )
            for j in range(i + 1, len(timeline)):
                if math.dist(cue_position, timeline[j]["target_position_m"]) >= 1:
                    result["first_observed_displacement_after_cue_s"] = (times[j] - times[i]) / 1000
                    result["cue_followup"] = "displacement_observed_after_cue"
                    break
            break
    return result


def position_screen(temporal: dict, minimum_samples: int = 3) -> dict:
    """Flag observed geometry without a movement threshold or pass-feasibility claim."""
    base = {"status": "insufficient_data", "qualifying_frames": [], "reason": ""}
    if type(minimum_samples) is not int or minimum_samples not in range(1, 6):
        raise ValueError("Minimum samples must be an integer from one to five")
    samples = temporal.get("samples")
    if (
        temporal.get("status") != "observed_geometry"
        or not isinstance(samples, list)
        or len(samples) != 5
    ):
        return {**base, "reason": "Five comparable observed samples are required."}
    try:
        for s in samples:
            if type(s["frame_id"]) is not int or any(
                type(s[k]) not in (int, float) or not math.isfinite(s[k]) or s[k] < 0
                for k in ("ball_distance_m", "nearest_detected_opponent_to_segment_m")
            ):
                return {**base, "reason": "Observed spatial measurements are invalid."}
        if any(
            b["frame_id"] - a["frame_id"] != 5 for a, b in zip(samples, samples[1:], strict=False)
        ):
            return {**base, "reason": "Sample frame continuity is invalid."}
        qualifying = [
            s["frame_id"]
            for s in samples
            if 8 <= s["ball_distance_m"] <= 25 and s["nearest_detected_opponent_to_segment_m"] >= 2
        ]
    except (KeyError, TypeError):
        return {**base, "reason": "Observed spatial measurements are missing."}
    return {
        "status": "candidate" if len(qualifying) >= minimum_samples else "not_candidate",
        "qualifying_frames": qualifying,
        "reason": "Illustrative observed geometry only; unseen defenders may exist.",
    }
