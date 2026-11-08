"""Read a bounded local tracking window without interpolating missing positions."""

import json
import math
from pathlib import Path
from typing import Any

from fil.time.clock import ClockError, parse_period_timestamp

MOVEMENT_SCREEN_VERSION = "fil-tracking-movement-2"


def tracking_window(path: Path, center: int, period: int, radius: int = 50) -> list[dict[str, Any]]:
    """Return source frames at 2 Hz within five seconds either side of a candidate."""
    frames = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            frame = json.loads(line)
            index = frame["frame"]
            if index > center + radius:
                break
            if (
                center - radius <= index <= center + radius
                and index % 5 == 0
                and frame.get("period") == period
            ):
                frames.append(frame)
    return frames


def detected_trail(
    frames: list[dict[str, Any]], player_id: int, through_frame: int, length: int = 40
) -> tuple[list[float | None], list[float | None]]:
    """Return detected positions only; break the trail at missing sampled observations."""
    x: list[float | None] = []
    y: list[float | None] = []
    previous = None
    for frame in frames:
        index = frame["frame"]
        if not through_frame - length <= index <= through_frame:
            continue
        matches = [p for p in frame["player_data"] if p.get("player_id") == player_id]
        point = matches[0] if len(matches) == 1 else {}
        coords = (point.get("x"), point.get("y"))
        valid = point.get("is_detected") is True and all(
            type(v) in (int, float) and math.isfinite(v) for v in coords
        )
        if not valid:
            previous = None
            if x and x[-1] is not None:
                x.append(None)
                y.append(None)
            continue
        if previous is not None and index - previous != 5:
            x.append(None)
            y.append(None)
        x.append(coords[0])
        y.append(coords[1])
        previous = index
    return x, y


def frame_distances(
    frame: dict[str, Any], player_id: int, teams: dict[int, int]
) -> tuple[float | None, float | None]:
    """Distance to detected ball and nearest detected opponent; neither implies coverage."""

    def xy(item: dict[str, Any]) -> tuple[float, float] | None:
        coords = (item.get("x"), item.get("y"))
        if item.get("is_detected") is True and all(
            type(v) in (int, float) and math.isfinite(v) for v in coords
        ):
            return coords
        return None

    matches = [p for p in frame["player_data"] if p.get("player_id") == player_id]
    if len(matches) != 1 or player_id not in teams or (origin := xy(matches[0])) is None:
        return None, None
    ball = xy(frame.get("ball_data") or {})
    ball_distance = math.dist(origin, ball) if ball is not None else None
    opponents = [
        pos
        for p in frame["player_data"]
        if p.get("player_id") in teams
        and teams[p["player_id"]] != teams[player_id]
        and (pos := xy(p)) is not None
    ]
    return ball_distance, min((math.dist(origin, pos) for pos in opponents), default=None)


def movement_candidate(
    frames: list[dict[str, Any]],
    player_id: int,
    team_id: int,
    team_group: str,
    teams: dict[int, int],
    phases: list[dict[str, Any]],
    center: int,
    period: int,
) -> dict[str, Any]:
    """Screen five 2 Hz samples ending at a frame; never infer unobserved motion."""
    base = {
        "version": MOVEMENT_SCREEN_VERSION,
        "player_id": player_id,
        "team_id": team_id,
        "period": period,
        "center_frame": center,
        "minimum_displacement_m": 3,
        "status": "insufficient_data",
        "reason": "",
        "frame_ids": [],
        "displacement_m": None,
        "start": None,
        "end": None,
        "timestamps": [],
    }
    if type(period) is not int or period not in (1, 2, 3, 4):
        return {**base, "reason": "Period is unavailable or is a shootout."}
    wanted = list(range(center - 20, center + 1, 5))
    sample = [f for f in frames if f.get("frame") in wanted and f.get("period") == period]
    if [f["frame"] for f in sample] != wanted:
        return {**base, "reason": "Five consecutive sampled frames are unavailable."}
    base["frame_ids"] = wanted
    base["timestamps"] = [f.get("timestamp") for f in sample]
    try:
        times = [parse_period_timestamp(f.get("timestamp")) for f in sample]
    except ClockError:
        return {**base, "reason": "Source timestamps are missing or malformed."}
    if any(b - a != 500 for a, b in zip(times, times[1:], strict=False)):
        return {**base, "reason": "Source timestamps conflict with the sampled frame interval."}
    try:
        matching = [
            p
            for p in phases
            if int(p["period"]) == period
            and int(p["frame_start"]) < wanted[-1]
            and wanted[0] < int(p["frame_end"])
        ]
        phase_team = int(matching[0]["team_in_possession_id"]) if len(matching) == 1 else None
    except (ValueError, TypeError, KeyError):
        return {**base, "reason": "Provider phase boundaries are malformed."}
    if (
        len(matching) != 1
        or int(matching[0]["frame_start"]) >= wanted[0]
        or int(matching[0]["frame_end"]) <= wanted[-1]
        or phase_team != team_id
        or teams.get(player_id) != team_id
    ):
        return {**base, "reason": "One matching in-play phase and player team are required."}
    positions = []
    for frame in sample:
        possession = frame.get("possession") or {}
        carrier = possession.get("player_id")
        if possession.get("group") != team_group or carrier not in teams:
            return {**base, "reason": "Provider possession is unknown or inconsistent."}
        if teams[carrier] != team_id:
            return {**base, "reason": "Provider possession conflicts with carrier team."}
        if carrier == player_id:
            return {**base, "status": "not_candidate", "reason": "Focus player is the carrier."}
        matches = [p for p in frame.get("player_data", []) if p.get("player_id") == player_id]
        point = matches[0] if len(matches) == 1 else {}
        coords = (point.get("x"), point.get("y"))
        if point.get("is_detected") is not True or not all(
            type(v) in (int, float) and math.isfinite(v) for v in coords
        ):
            return {**base, "reason": "Focus position is missing, duplicated or extrapolated."}
        positions.append(coords)
    distance = math.dist(positions[0], positions[-1])
    return {
        **base,
        "status": "candidate" if distance >= 3 else "not_candidate",
        "reason": "Displacement at least 3 m." if distance >= 3 else "Displacement below 3 m.",
        "frame_ids": wanted,
        "displacement_m": distance,
        "start": positions[0],
        "end": positions[-1],
    }
