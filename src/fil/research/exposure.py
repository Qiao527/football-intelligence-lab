"""Recorded lineup census, not official minutes or inferred physical availability."""

import json
from collections import defaultdict

import pyarrow as pa

VERSION = "fil-recorded-exposure-1"
ON_FIELD = frozenset(
    {
        "Pass",
        "Carry",
        "Shot",
        "Dribble",
        "Ball Receipt*",
        "Pressure",
        "Miscontrol",
        "Dispossessed",
        "Clearance",
        "Interception",
        "Duel",
        "Ball Recovery",
        "Shield",
        "Goal Keeper",
    }
)


def chronology(events: pa.Table, roster: list[dict]) -> dict:
    """Validate native XI/substitution/off/on/card chronology and retain boundary IDs.

    Provisional elapsed seconds include stoppages and temporary off-field episodes,
    exclude breaks and shootouts. Missing or contradictory evidence yields null
    exposure throughout; no min/max actor timestamps are substituted for playing time.
    """
    records = events.to_pylist()
    raw = {r["event_id"]: json.loads(r["source_record_json"]) for r in records}
    keys = {(r["team_id"], r["player_id"]) for r in roster}
    if len(keys) != len(roster):
        raise ValueError("Duplicate roster identities")
    teams = {r["team_id"] for r in roster}
    issues = ["duplicate_original_event_ids"] if len(raw) != len(records) else []
    active = {t: set() for t in teams}
    permanent = set()
    temporary = set()
    xi_ids = []
    role_snapshots = []
    transitions = []
    intervals = []
    for e in raw.values():
        if e["type"]["name"] in ("Starting XI", "Tactical Shift"):
            for p in e.get("tactics", {}).get("lineup", []):
                role_snapshots.append(
                    dict(
                        event_id=e["id"],
                        team_id=e["team"]["id"],
                        player_id=p["player"]["id"],
                        period=e["period"],
                        provider_index=e["index"],
                        position=p.get("position"),
                    )
                )
        if e["type"]["name"] == "Starting XI":
            t = e["team"]["id"]
            players = [p["player"]["id"] for p in e.get("tactics", {}).get("lineup", [])]
            if t not in active or active[t] or len(players) != 11 or len(set(players)) != 11:
                issues.append("missing_duplicate_or_invalid_starting_xi")
            else:
                active[t] = set(players)
                xi_ids.append(e["id"])
            if e["period"] != 1 or e["timestamp"] != "00:00:00.000":
                issues.append("starting_xi_not_at_match_start")
    if any(len(v) != 11 for v in active.values()) or len(active) != 2:
        issues.append("incomplete_starting_xi")
    if any((t, p) not in keys for t, ps in active.items() for p in ps):
        issues.append("starting_player_not_in_roster")
    periods = sorted({r["period"] for r in records if r["period"] in (1, 2, 3, 4)})
    if periods != list(range(1, max(periods, default=0) + 1)):
        issues.append("nonconsecutive_periods")
    if not periods:
        issues.append("missing_match_play_periods")
    for period in periods:
        group = sorted(
            (r for r in records if r["period"] == period), key=lambda r: r["provider_index"]
        )
        starts = [r for r in group if r["event_type"] == "Half Start"]
        ends = [r for r in group if r["event_type"] == "Half End"]
        end_values = {r["period_elapsed_ms"] for r in ends}
        end = next(iter(end_values)) if len(end_values) == 1 else None
        if not starts or any(r["period_elapsed_ms"] != 0 for r in starts) or end is None:
            issues.append(f"uncertified_period_boundaries:{period}")
        if end is not None and any(r["period_elapsed_ms"] > end for r in group):
            issues.append(f"event_after_period_end:{period}")
        opened = {
            (t, p): (0, [r["event_id"] for r in starts] + xi_ids)
            for t, ps in active.items()
            for p in ps
        }

        def close(key, ms, evidence, opened=opened, period=period):
            if key not in opened:
                issues.append("close_without_recorded_entry")
                return
            begin, entry = opened.pop(key)
            if ms is None or ms < begin:
                issues.append("invalid_interval_clock")
            intervals.append(
                dict(
                    team_id=key[0],
                    player_id=key[1],
                    period=period,
                    start_ms=begin,
                    end_ms=ms,
                    entry_event_ids=entry,
                    exit_event_ids=evidence,
                )
            )

        for r in group:
            e = raw[r["event_id"]]
            t, p = r["team_id"], r["player_id"]
            kind = r["event_type"]
            ms = r["period_elapsed_ms"]
            if kind in ON_FIELD and p is not None and p not in active.get(t, set()):
                issues.append(f"action_outside_recorded_census:{r['event_id']}")
            action = None
            other = None
            if kind == "Substitution":
                other = (e.get("substitution") or {}).get("replacement", {}).get("id")
                if (
                    p not in active.get(t, set())
                    or (t, other) not in keys
                    or other in active.get(t, set())
                    or (t, other) in permanent
                ):
                    issues.append("invalid_substitution")
                    continue
                close((t, p), ms, [r["event_id"]])
                active[t].remove(p)
                permanent.add((t, p))
                active[t].add(other)
                opened[t, other] = (ms, [r["event_id"]])
                action = "substitution"
            elif kind == "Player Off":
                if p not in active.get(t, set()):
                    issues.append("player_off_without_entry")
                    continue
                close((t, p), ms, [r["event_id"]])
                active[t].remove(p)
                if e.get("player_off", {}).get("permanent"):
                    permanent.add((t, p))
                else:
                    temporary.add((t, p))
                action = "player_off"
            elif kind == "Player On":
                if (t, p) not in temporary or (t, p) in permanent:
                    issues.append("player_on_without_temporary_off")
                    continue
                temporary.remove((t, p))
                active[t].add(p)
                opened[t, p] = (ms, [r["event_id"]])
                action = "player_on"
            card = (
                (e.get("foul_committed") or e.get("bad_behaviour") or {})
                .get("card", {})
                .get("name")
            )
            if card in ("Red Card", "Second Yellow"):
                if p in active.get(t, set()):
                    close((t, p), ms, [r["event_id"]])
                    active[t].remove(p)
                    permanent.add((t, p))
                    action = "dismissal"
                else:
                    issues.append("off_field_dismissal_context")
            if any(len(ps) > 11 for ps in active.values()):
                issues.append("census_exceeds_eleven")
            if action:
                transitions.append(
                    dict(
                        event_id=r["event_id"],
                        period=period,
                        period_elapsed_ms=ms,
                        provider_index=r["provider_index"],
                        team_id=t,
                        player_id=p,
                        replacement_player_id=other,
                        action=action,
                    )
                )
        for key in list(opened):
            close(key, end, [r["event_id"] for r in ends])
    if temporary:
        issues.append("unpaired_temporary_off")
    duration = defaultdict(float)
    for r in intervals:
        if r["end_ms"] is not None:
            duration[r["team_id"], r["player_id"]] += (r["end_ms"] - r["start_ms"]) / 1000
    rows = [
        dict(
            team_id=t,
            player_id=p,
            provisional_recorded_seconds=duration.get((t, p)) if not issues else None,
            minutes_played=None,
            per90_eligible=False,
            exposure_status="recorded_chronology_consistent"
            if not issues and (t, p) in duration
            else "insufficient_evidence",
        )
        for t, p in sorted(keys)
    ]
    return dict(
        version=VERSION,
        players=rows,
        intervals=intervals,
        transitions=transitions,
        position_snapshots=role_snapshots,
        issues=sorted(set(issues)),
        status="recorded_chronology_consistent" if not issues else "insufficient_evidence",
        limitations=(
            "Recorded census elapsed time, not official minutes, live-ball time, "
            "tracking or inferred role; no per90"
        ),
    )
