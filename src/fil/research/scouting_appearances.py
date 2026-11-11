"""Export scouting appearance rows from canonical events; never infer minutes.

Produces the exact row contract consumed by `fil.research.scouting_task`. The
caller supplies verified canonical event rows, lineup position metadata and
match metadata; this module does not read raw provider JSON and does not decide
which positions count as attackers.
"""

import json
import math
from collections import defaultdict
from typing import Any

VERSION = "fil-scouting-appearances-1"
SHOOTOUT_PERIOD = 5
EVENT_KEYS = ("event_id", "match_id", "team_id", "player_id", "event_type",
              "period", "shot_xg", "shot_type", "shot_outcome")
MATCH_KEYS = ("match_id", "match_date", "competition_stage", "home_team_id",
              "away_team_id")
LINEUP_KEYS = ("match_id", "team_id", "player_id", "positions")


def stage_of(name: Any) -> str:
    """Provider stage name to the two declared windows; no inference."""
    if not isinstance(name, str) or not name:
        raise ValueError("Match metadata needs a competition_stage name")
    return "group" if name == "Group Stage" else "knockout"


def team_matchdays(matches_meta: list[dict[str, Any]]) -> dict[tuple, int | None]:
    """Chronological group matchday per team; provider dates, ties by match id."""
    for match in matches_meta:
        missing = [k for k in MATCH_KEYS if k not in match]
        if missing:
            raise ValueError(f"Match metadata is missing fields: {missing}")
    seen: set[int] = set()
    for match in matches_meta:
        if match["match_id"] in seen:
            raise ValueError("Duplicate match metadata")
        seen.add(match["match_id"])
    by_team: dict[int, list[dict]] = defaultdict(list)
    for match in matches_meta:
        if stage_of(match["competition_stage"]) != "group":
            continue
        by_team[match["home_team_id"]].append(match)
        by_team[match["away_team_id"]].append(match)
    order: dict[tuple, int | None] = {}
    for team, matches in by_team.items():
        ordered = sorted(matches, key=lambda m: (m["match_date"], m["match_id"]))
        if len(ordered) != 3:
            raise ValueError(f"Team {team} does not have exactly three group matches")
        for index, match in enumerate(ordered, start=1):
            order[(match["match_id"], team)] = index
    for match in matches_meta:
        if stage_of(match["competition_stage"]) == "knockout":
            order[(match["match_id"], match["home_team_id"])] = None
            order[(match["match_id"], match["away_team_id"])] = None
    return order


def _finite(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite; missing source values are not zero")
    return float(value)


def _shot(event: dict[str, Any]) -> tuple[bool, bool, float, bool]:
    """Return (is_shot, is_goal, xg, is_penalty) with hard source checks."""
    if event["event_type"] != "Shot":
        return False, False, 0.0, False
    xg = _finite(event["shot_xg"], "shot_xg")
    if not 0 <= xg <= 1:
        raise ValueError("Source shot xG must lie in [0, 1]")
    penalty = event["shot_type"] == "Penalty"
    return True, event["shot_outcome"] == "Goal", xg, penalty


def _positions(lineups: list[dict[str, Any]]) -> dict[tuple, str | None]:
    labels: dict[tuple, str | None] = {}
    for entry in lineups:
        missing = [k for k in LINEUP_KEYS if k not in entry]
        if missing:
            raise ValueError(f"Lineup record is missing fields: {missing}")
        key = (entry["match_id"], entry["team_id"], entry["player_id"])
        if key in labels:
            raise ValueError("Duplicate lineup identity")
        positions = entry["positions"]
        if positions is not None and not isinstance(positions, list):
            raise ValueError("Lineup positions must be a list or null")
        labels[key] = (
            json.dumps(positions, sort_keys=True) if positions else None
        )
    return labels


def appearance_rows(
    events: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    matches_meta: list[dict[str, Any]],
    strict_unattributed: bool = True,
) -> dict[str, Any]:
    """Observed actor appearances with source shots, xG and position metadata.

    Shootout records are excluded. An unattributed shot is a hard failure by
    default because it breaks per-player team totals; callers may opt into
    reporting and excluding it instead.
    """
    order = team_matchdays(matches_meta)
    dates = {m["match_id"]: m["match_date"] for m in matches_meta}
    stages = {m["match_id"]: stage_of(m["competition_stage"]) for m in matches_meta}
    labels = _positions(lineups)
    grouped: dict[tuple, dict[str, Any]] = {}
    unattributed: list[str] = []
    penalties = 0
    for event in events:
        missing = [k for k in EVENT_KEYS if k not in event]
        if missing:
            raise ValueError(f"Canonical event is missing fields: {missing}")
        if event["match_id"] not in dates:
            raise ValueError("Event references an unknown match")
        if not isinstance(event["period"], int) or not 1 <= event["period"] <= 5:
            raise ValueError("Unsupported source period")
        if event["period"] == SHOOTOUT_PERIOD:
            continue
        is_shot, is_goal, xg, penalty = _shot(event)
        player = event["player_id"]
        if player is None:
            if is_shot:
                unattributed.append(event["event_id"])
            continue
        key = (event["match_id"], event["team_id"], player)
        row = grouped.get(key)
        if row is None:
            row = grouped[key] = {
                "source": event.get("source"),
                "match_id": event["match_id"],
                "team_id": event["team_id"],
                "player_id": player,
                "stage": stages[event["match_id"]],
                "team_matchday": order.get((event["match_id"], event["team_id"])),
                "position_label": labels.get(key),
                "shots": 0,
                "goals": 0,
                "xg": 0.0,
                "npxg": 0.0,
                "shot_event_ids": [],
            }
        if is_shot:
            row["shots"] += 1
            row["goals"] += int(is_goal)
            row["xg"] += xg
            if penalty:
                penalties += 1
            else:
                row["npxg"] += xg
            row["shot_event_ids"].append(event["event_id"])
    if unattributed and strict_unattributed:
        raise ValueError(
            f"{len(unattributed)} shot(s) have no player attribution: "
            f"{unattributed[:5]}"
        )
    rows = sorted(
        grouped.values(),
        key=lambda r: (r["team_id"], r["player_id"], dates[r["match_id"]],
                       r["match_id"]),
    )
    for row in rows:
        if row["team_matchday"] is None and row["stage"] == "group":
            raise ValueError("Group appearance without a team matchday")
    return {
        "version": VERSION,
        "rows": rows,
        "unattributed_shot_ids": unattributed,
        "coverage": {
            "players": len({(r["team_id"], r["player_id"]) for r in rows}),
            "appearances": len(rows),
            "zero_shot_appearances": sum(r["shots"] == 0 for r in rows),
            "penalty_shots": penalties,
            "null_position_appearances": sum(r["position_label"] is None for r in rows),
            "group_appearances": sum(r["stage"] == "group" for r in rows),
            "knockout_appearances": sum(r["stage"] == "knockout" for r in rows),
        },
    }


def reconcile(
    rows: list[dict[str, Any]],
    expected: dict[tuple, dict[str, float]],
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    """Per match/team shot, goal and xG totals must match verified source facts."""
    totals: dict[tuple, dict[str, float]] = defaultdict(
        lambda: {"shots": 0.0, "goals": 0.0, "xg": 0.0}
    )
    for row in rows:
        key = (row["match_id"], row["team_id"])
        totals[key]["shots"] += row["shots"]
        totals[key]["goals"] += row["goals"]
        totals[key]["xg"] += row["xg"]
    mismatches = []
    for key, want in expected.items():
        have = totals.get(key, {"shots": 0.0, "goals": 0.0, "xg": 0.0})
        for name in ("shots", "goals"):
            if have[name] != want[name]:
                mismatches.append(
                    {"match_id": key[0], "team_id": key[1], "field": name,
                     "expected": want[name], "observed": have[name]}
                )
        if abs(have["xg"] - want["xg"]) > tolerance:
            mismatches.append(
                {"match_id": key[0], "team_id": key[1], "field": "xg",
                 "expected": want["xg"], "observed": have["xg"]}
            )
    extra = sorted(set(totals) - set(expected))
    if mismatches or extra:
        raise ValueError(f"Reconciliation failed: {mismatches[:5]} extra={extra[:5]}")
    return {"version": VERSION, "match_teams": len(expected),
            "shots": sum(v["shots"] for v in expected.values()),
            "xg": math.fsum(v["xg"] for v in expected.values())}
