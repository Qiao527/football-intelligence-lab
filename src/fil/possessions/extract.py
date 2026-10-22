"""Provider-ID possession processes v1; full sequences precede any UI filtering."""

import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass

import pyarrow as pa

from fil.ingestion.statsbomb_possessions import source_records
from fil.ingestion.statsbomb_tactics import extract_tactics
from fil.metrics.tactics import PROGRESSION_VERSION, valid_point
from fil.metrics.tactics import VERSION as TACTICS_VERSION

VERSION = "fil-possession-1"
OWNER_ACTIONS = frozenset(
    {
        "Pass",
        "Carry",
        "Ball Receipt*",
        "Dribble",
        "Shot",
        "Miscontrol",
        "Dispossessed",
        "Clearance",
        "Ball Recovery",
        "Interception",
        "Duel",
        "Shield",
        "Goal Keeper",
    }
)
ACTION_SCHEMA = pa.schema(
    [
        *[
            (n, pa.int64())
            for n in (
                "match_id",
                "possession_id",
                "possession_team_id",
                "sequence",
                "provider_index",
                "period",
                "period_elapsed_ms",
                "team_id",
                "player_id",
            )
        ],
        *[
            (n, pa.string())
            for n in (
                "event_id",
                "event_type",
                "display_clock",
                "role",
                "zone",
                "end_zone",
                "action_status",
                "progression_reason",
                "coordinate_system",
                "source_manifest_sha256",
            )
        ],
        *[(n, pa.float64()) for n in ("x", "y", "end_x", "end_y", "shot_xg")],
        *[
            (n, pa.bool_())
            for n in ("is_owner_action", "progressive", "final_third_entry", "box_entry")
        ],
    ],
    metadata={
        b"fil.possession_version": VERSION.encode(),
        b"fil.progression_version": PROGRESSION_VERSION.encode(),
    },
)
POSSESSION_SCHEMA = pa.schema(
    [
        *[
            (n, pa.int64())
            for n in (
                "match_id",
                "possession_id",
                "possession_team_id",
                "start_period",
                "end_period",
                "start_ms",
                "end_ms",
                "event_count",
                "owner_actions",
                "opponent_events",
                "completed_passes",
                "carries",
                "progressive_actions",
                "final_third_entries",
                "box_entries",
                "shot_count",
                "actions_to_first_final_third",
                "next_possession_id",
                "next_team_id",
            )
        ],
        *[
            (n, pa.string())
            for n in (
                "start_event_id",
                "end_event_id",
                "entry_event_id",
                "exit_event_id",
                "start_zone",
                "end_zone",
                "start_reason",
                "end_reason",
                "spec_version",
            )
        ],
        *[
            (n, pa.float64())
            for n in ("observed_span_seconds", "shot_xg_sum", "time_to_first_shot_seconds")
        ],
        *[
            (n, pa.bool_())
            for n in ("reached_final_third", "reached_box", "shot_ending", "turnover")
        ],
        *[
            (n, pa.list_(pa.string()))
            for n in (
                "event_ids",
                "owner_action_ids",
                "shot_event_ids",
                "path_event_ids",
                "zone_path",
                "boundary_evidence_ids",
                "quality_flags",
            )
        ],
        ("participant_ids", pa.list_(pa.int64())),
    ],
    metadata={
        b"fil.possession_version": VERSION.encode(),
        b"fil.progression_version": PROGRESSION_VERSION.encode(),
    },
)


@dataclass(frozen=True)
class PossessionFacts:
    possessions: pa.Table
    actions: pa.Table
    quality: dict


def zone(x: float | None, y: float | None) -> str:
    """Native +x geometric zones, not certified physical attacking orientation."""
    if not valid_point(x, y):
        return "UNKNOWN"
    if x >= 102 and 18 <= y <= 62:
        return "BOX"
    return "DEF" if x < 40 else "MID" if x < 80 else "ATT"


def reconstruct(events: pa.Table, home: int, away: int) -> PossessionFacts:
    """Keep all native members including opponent/admin events; unknown labels stay unassigned."""
    if not events.num_rows or len(set(events["match_id"].to_pylist())) != 1:
        raise ValueError("Expected a complete single-match event table")
    native = {e["id"]: e for e in source_records(events)}
    tactical = {r["event_id"]: r for r in extract_tactics(events, home, away).actions.to_pylist()}
    fields = [
        "match_id",
        "event_id",
        "possession_id",
        "possession_team_id",
        "provider_index",
        "period",
        "period_elapsed_ms",
        "display_clock",
        "team_id",
        "player_id",
        "event_type",
        "x",
        "y",
        "end_x",
        "end_y",
        "shot_xg",
        "coordinate_system",
        "source_manifest_sha256",
    ]
    ordered = sorted(events.select(fields).to_pylist(), key=lambda r: r["provider_index"])
    groups = defaultdict(list)
    closed = set()
    previous = None
    for r in ordered:
        key = (r["match_id"], r["possession_id"]) if r["possession_id"] is not None else None
        if key is None:
            continue  # Preserve unassigned actions; never manufacture a new ID.
        if key != previous:
            if key is not None and key in closed:
                raise ValueError("Noncontiguous native possession ID")
            if previous is not None:
                closed.add(previous)
            previous = key
        if key is not None:
            groups[key].append(r)
    output, actions = [], []
    entries = list(groups.items())
    sequence_by_id = {r["event_id"]: i + 1 for _, g in entries for i, r in enumerate(g)}
    for r in ordered:
        t = tactical.get(r["event_id"], {})
        owner = r["possession_team_id"] in (home, away) and r["team_id"] == r["possession_team_id"]
        is_action = (
            owner
            and r["possession_id"] is not None
            and r["event_type"] in OWNER_ACTIONS
            and r["period"] in (1, 2, 3, 4)
        )
        actions.append(
            {
                **r,
                "sequence": sequence_by_id.get(r["event_id"]),
                "role": "unassigned"
                if r["possession_id"] is None
                else "unknown_owner_context"
                if r["possession_team_id"] not in (home, away)
                else "owner_action"
                if is_action
                else "owner_context"
                if owner
                else "opponent_context",
                "is_owner_action": is_action,
                "zone": zone(r["x"], r["y"]),
                "end_zone": zone(r["end_x"], r["end_y"]),
                "action_status": t.get("status"),
                "progression_reason": t.get("progression_reason"),
                **{
                    k: t.get(k) if is_action else None
                    for k in ("progressive", "final_third_entry", "box_entry")
                },
            }
        )
    by_id = {r["event_id"]: r for r in actions}
    for gi, ((match, pid), group) in enumerate(entries):
        teams = {r["possession_team_id"] for r in group}
        if len(teams) != 1:
            raise ValueError("Inconsistent native possession team")
        team = next(iter(teams))
        if team is not None and team not in (home, away):
            raise ValueError("Unknown native possession team")
        start, end = group[0], group[-1]
        own = [by_id[r["event_id"]] for r in group if by_id[r["event_id"]]["is_owner_action"]]
        first, last = (own[0], own[-1]) if own else (None, None)
        next_group = entries[gi + 1][1] if gi + 1 < len(entries) else []
        nxt = next_group[0] if next_group else None
        next_owner = next(
            (
                r
                for r in next_group
                if r["team_id"] == r["possession_team_id"] and r["event_type"] in OWNER_ACTIONS
            ),
            None,
        )
        next_restart = bool(
            next_owner
            and ((native[next_owner["event_id"]].get("pass") or {}).get("type") or {}).get("name")
            in ("Kick Off", "Goal Kick", "Throw-in", "Free Kick", "Corner")
        )
        flags = []
        periods = {r["period"] for r in group}
        if len(periods) > 1:
            flags.append("cross_period_provider_id; no continuous duration/path")
        if team is None:
            flags.append("missing_possession_team")
        if any(
            r["possession_id"] is None
            and start["provider_index"] < r["provider_index"] < end["provider_index"]
            for r in ordered
        ):
            flags.append("unassigned_record_gap; membership_unresolved")
        if not own:
            flags.append("no_owner_ball_actions")
        if any(not valid_point(r["x"], r["y"]) for r in own):
            flags.append("missing_owner_positions")
        if any(r["period"] == 5 for r in group):
            flags.append("shootout_excluded_from_process_metrics")
        flags.append("physical_attacking_direction_unknown")
        path, path_ids, prev_period = [], [], None
        for r in own:
            if prev_period is not None and prev_period != r["period"]:
                path.append("PERIOD_BREAK")
            states = [r["zone"]]
            if r["action_status"] in ("completed", "observed_carry"):
                states.append(r["end_zone"])
                path_ids.append(r["event_id"])
            # Repeated records within a zone are collapsed; backwards revisits stay.
            for state in states:
                if not path or path[-1] != state:
                    path.append(state)
            prev_period = r["period"]
        reached = any(
            r["zone"] in ("ATT", "BOX")
            or r["action_status"] in ("completed", "observed_carry")
            and r["end_zone"] in ("ATT", "BOX")
            for r in own
        )
        box = any(
            r["zone"] == "BOX"
            or r["action_status"] in ("completed", "observed_carry")
            and r["end_zone"] == "BOX"
            for r in own
        )
        first_reach = next(
            (
                i + 1
                for i, r in enumerate(own)
                if r["zone"] in ("ATT", "BOX")
                or r["action_status"] in ("completed", "observed_carry")
                and r["end_zone"] in ("ATT", "BOX")
            ),
            None,
        )
        shots = [r for r in own if r["event_type"] == "Shot"]
        if any(
            r["shot_xg"] is None or not math.isfinite(r["shot_xg"]) or not 0 <= r["shot_xg"] <= 1
            for r in shots
        ):
            raise ValueError("Missing/unsupported source shot xG")
        same_period = len(periods) == 1
        shot_ending = bool(last and last["event_type"] == "Shot")
        tail = [
            native[r["event_id"]]
            for r in group
            if last and r["provider_index"] >= last["provider_index"]
        ]
        out = any(
            e.get("out") is True
            or ((e.get("pass") or {}).get("outcome") or {}).get("name") in ("Out", "Pass Offside")
            for e in tail
        )
        foul = any(
            e["type"]["name"] in ("Foul Won", "Foul Committed")
            and not (e.get("foul_won") or e.get("foul_committed") or {}).get("advantage")
            for e in tail
        )
        loss = last and (
            last["event_type"] in ("Dispossessed", "Miscontrol")
            or last["event_type"] == "Pass"
            and native[last["event_id"]]["pass"].get("outcome") == {"id": 9, "name": "Incomplete"}
            or last["event_type"] == "Dribble"
            and native[last["event_id"]]["dribble"].get("outcome", {}).get("name") == "Incomplete"
        )
        boundary = (
            not same_period
            or nxt is not None
            and nxt["period"] != end["period"]
            or any(r["event_type"] == "Half End" for r in group)
        )
        turnover = bool(
            loss
            and nxt
            and nxt["period"] == last["period"]
            and nxt["possession_team_id"] in (home, away)
            and nxt["possession_team_id"] != team
            and not (out or foul or boundary)
            and not next_restart
            and not any(
                r["possession_id"] is None
                and last["provider_index"] < r["provider_index"] < nxt["provider_index"]
                for r in ordered
            )
        )
        own_goal = any(r["event_type"] in ("Own Goal For", "Own Goal Against") for r in group)
        reason = (
            "period_boundary"
            if boundary
            else "own_goal_recorded"
            if own_goal
            else "shot"
            if shot_ending
            else "out_of_play"
            if out
            else "foul_observed"
            if foul
            else "turnover"
            if turnover
            else "provider_boundary_unresolved"
        )
        evidence = (
            [end["event_id"]]
            + ([last["event_id"]] if last else [])
            + ([nxt["event_id"]] if nxt else [])
        )
        entry = native[first["event_id"]] if first else {}
        pass_type = (entry.get("pass") or {}).get("type", {}).get("name")
        output.append(
            {
                "match_id": match,
                "possession_id": pid,
                "possession_team_id": team,
                "start_event_id": start["event_id"],
                "end_event_id": end["event_id"],
                "entry_event_id": first["event_id"] if first else None,
                "exit_event_id": last["event_id"] if last else None,
                "start_period": start["period"],
                "end_period": end["period"],
                "start_ms": start["period_elapsed_ms"],
                "end_ms": end["period_elapsed_ms"],
                "observed_span_seconds": (end["period_elapsed_ms"] - start["period_elapsed_ms"])
                / 1000
                if same_period
                else None,
                "start_zone": first["zone"] if first else "UNKNOWN",
                "end_zone": last["end_zone"]
                if last and last["action_status"] in ("completed", "observed_carry")
                else last["zone"]
                if last
                else "UNKNOWN",
                "start_reason": f"native_restart:{pass_type}"
                if pass_type in ("Kick Off", "Goal Kick", "Throw-in", "Free Kick", "Corner")
                else f"first_owner_record:{first['event_type']}"
                if first
                else "unknown",
                "end_reason": reason,
                "event_count": len(group),
                "owner_actions": len(own),
                "opponent_events": sum(r["team_id"] != team for r in group),
                "participant_ids": sorted(
                    {r["player_id"] for r in own if r["player_id"] is not None}
                ),
                "completed_passes": sum(r["action_status"] == "completed" for r in own),
                "carries": sum(r["action_status"] == "observed_carry" for r in own),
                "progressive_actions": sum(r["progressive"] is True for r in own),
                "final_third_entries": sum(r["final_third_entry"] is True for r in own),
                "box_entries": sum(r["box_entry"] is True for r in own),
                "reached_final_third": reached,
                "reached_box": box,
                "actions_to_first_final_third": first_reach,
                "shot_count": len(shots),
                "shot_xg_sum": math.fsum(r["shot_xg"] for r in shots) if team is not None else None,
                "time_to_first_shot_seconds": (
                    shots[0]["period_elapsed_ms"] - start["period_elapsed_ms"]
                )
                / 1000
                if shots and same_period
                else None,
                "shot_ending": shot_ending,
                "turnover": turnover,
                "next_possession_id": nxt["possession_id"] if nxt else None,
                "next_team_id": nxt["possession_team_id"] if nxt else None,
                "event_ids": [r["event_id"] for r in group],
                "owner_action_ids": [r["event_id"] for r in own],
                "shot_event_ids": [r["event_id"] for r in shots],
                "path_event_ids": path_ids,
                "zone_path": path,
                "boundary_evidence_ids": list(dict.fromkeys(evidence)),
                "quality_flags": flags,
                "spec_version": VERSION,
            }
        )
    return PossessionFacts(
        pa.Table.from_pylist(output, schema=POSSESSION_SCHEMA),
        pa.Table.from_pylist(actions, schema=ACTION_SCHEMA),
        {
            "version": VERSION,
            "progression_version": PROGRESSION_VERSION,
            "native_action_version": TACTICS_VERSION,
            "source_events": len(ordered),
            "possessions": len(output),
            "unassigned_events": sum(r["possession_id"] is None for r in ordered),
            "end_reasons": dict(Counter(r["end_reason"] for r in output)),
            "cross_period_native_ids": [
                r["possession_id"] for r in output if r["start_period"] != r["end_period"]
            ],
            "opponent_context_events": sum(r["role"] == "opponent_context" for r in actions),
            "physical_directions": "unknown; native +x geometric convention only",
        },
    )


def select_possessions(facts: PossessionFacts, selected: pa.Table) -> pa.Table:
    """Full native possessions touched by selected original IDs; never truncate chains."""
    ids = set(selected["event_id"].to_pylist())
    return facts.possessions.filter(
        pa.array(
            [bool(ids.intersection(r)) for r in facts.possessions["event_ids"].to_pylist()],
            type=pa.bool_(),
        )
    )


def process_summary(possessions: pa.Table) -> dict:
    """Possession-grain denominators, zero/unknown policies and shot-subset time bias explicit."""
    rows = [
        r
        for r in possessions.to_pylist()
        if r["owner_actions"] > 0 and r["possession_team_id"] is not None
    ]
    reached = [r for r in rows if r["reached_final_third"]]
    times = sorted(
        r["time_to_first_shot_seconds"] for r in rows if r["time_to_first_shot_seconds"] is not None
    )
    return {
        "eligible_possessions": len(rows),
        "final_third_possessions": len(reached),
        "shot_after_final_third_numerator": sum(r["shot_count"] > 0 for r in reached),
        "shot_after_final_third_denominator": len(reached),
        "p_shot_given_final_third": sum(r["shot_count"] > 0 for r in reached) / len(reached)
        if reached
        else None,
        "p_box_given_final_third": sum(r["reached_box"] for r in reached) / len(reached)
        if reached
        else None,
        "box_after_final_third_numerator": sum(r["reached_box"] for r in reached),
        "xg_per_possession": math.fsum(r["shot_xg_sum"] for r in rows) / len(rows)
        if rows
        else None,
        "median_elapsed_to_shot_seconds": statistics.median(times) if times else None,
        "timed_shot_possessions": len(times),
        "time_bias": "shot-producing same-period possessions only",
    }
