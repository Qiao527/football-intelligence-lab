"""PROPOSED conditional source-marker envelopes, separate from every v1 clock."""

from collections import defaultdict
from fractions import Fraction

from fil.research.exposure import ON_FIELD
from fil.time.clock import parse_period_timestamp

VERSION = "fil-period-envelope-proposal-1"
ASSUMPTION = (
    "Sensitivity scenarios assume each period end lies between its paired source markers. "
    "The provider has not certified that the physical whistle lies inside this envelope."
)


def envelopes(records: list[dict], teams: set[int]) -> dict:
    """Retain source order/times; never choose a marker, round conflicts or repair clocks."""
    if len(teams) != 2 or not records:
        raise ValueError("Nonempty two-team match required")
    ids = [e["id"] for e in records]
    indices = [e["index"] for e in records]
    if len(set(ids)) != len(ids) or any(b <= a for a, b in zip(indices, indices[1:], strict=False)):
        raise ValueError("Duplicate identity or reversing provider index")
    if [e["period"] for e in records] != sorted(e["period"] for e in records):
        raise ValueError("Reversing source period")
    groups = defaultdict(list)
    for e in records:
        groups[e["period"]].append(e)
    play = sorted(p for p in groups if p in (1, 2, 3, 4))
    missing_periods = play != list(range(1, max(play, default=0) + 1))
    output = []
    offset = [0, 0]
    for period, group in sorted(groups.items()):
        times = [parse_period_timestamp(e["timestamp"]) for e in group]
        starts = [e for e in group if e["type"]["name"] == "Half Start"]
        ends = [e for e in group if e["type"]["name"] == "Half End"]
        reasons = ["nonconsecutive_periods"] if missing_periods else []
        for kind, markers in [("start", starts), ("end", ends)]:
            if len(markers) != 2 or {e["team"]["id"] for e in markers} != teams:
                reasons.append(f"missing_or_ambiguous_{kind}_pair")
            elif any(
                other["id"] not in e.get("related_events", [])
                for e, other in [(markers[0], markers[1]), (markers[1], markers[0])]
            ):
                reasons.append(f"unlinked_{kind}_pair")
        if period not in (1, 2, 3, 4):
            reasons.append("unsupported_period")
        if any(b < a for a, b in zip(times, times[1:], strict=False)):
            reasons.append("reversing_period_clock")
        if any(parse_period_timestamp(e["timestamp"]) != 0 for e in starts):
            reasons.append("nonzero_recorded_start")
        if any(
            (e.get("half_end") or {}).get(k)
            for e in ends
            for k in ("early_video_end", "match_suspended")
        ) or any((e.get("half_start") or {}).get("late_video_start") for e in starts):
            reasons.append("incomplete_or_suspended_video")
        bounds = (
            [
                min(parse_period_timestamp(e["timestamp"]) for e in ends),
                max(parse_period_timestamp(e["timestamp"]) for e in ends),
            ]
            if ends
            else None
        )
        nonmarkers = [e for e in group if e["type"]["name"] not in ("Half Start", "Half End")]
        edge = [
            e["id"]
            for e in nonmarkers
            if bounds and parse_period_timestamp(e["timestamp"]) >= bounds[0]
        ]
        if bounds and bounds[0] <= 0:
            reasons.append("nonpositive_period_end")
        if edge:
            reasons.append("nonmarker_at_or_after_earliest_end")
        spanning = []
        for e in nonmarkers:
            if (
                e.get("duration") is not None
                and bounds
                and Fraction(str(e["duration"])) * 1000 + parse_period_timestamp(e["timestamp"])
                > bounds[0]
            ):
                spanning.append(e["id"])
        row = dict(
            period=period,
            start_evidence=starts,
            end_evidence=ends,
            source_event_ids=[e["id"] for e in group],
            observed_end_envelope_ms=bounds,
            recorded_start_ms=0
            if starts and not any(parse_period_timestamp(e["timestamp"]) != 0 for e in starts)
            else None,
            exact_physical_end_ms=None,
            physical_end_certified=False,
            event_phase_offset_scenario_ms=offset.copy() if offset is not None else None,
            conditional_eligible=not reasons,
            exclusion_reasons=reasons,
            nonmarker_boundary_zone_ids=edge,
            known_duration_overlap_ids=spanning,
        )
        output.append(row)
        offset = (
            [offset[i] + bounds[i] for i in (0, 1)] if not reasons and offset is not None else None
        )
    return dict(
        version=VERSION,
        status="PROPOSED_NOT_ACCEPTED",
        assumption=ASSUMPTION,
        periods=output,
        event_ids=ids,
        exact_match_duration_ms=None,
        conditional_recorded_match_duration_ms=offset,
        expansion_authorized=False,
    )


def exposure_sensitivity(records: list[dict], roster: list[dict], model: dict) -> dict:
    """Integrate recorded census analytically at both envelope endpoints; no official minutes."""
    active = {r["team_id"]: set() for r in roster}
    keys = {(r["team_id"], r["player_id"]) for r in roster}
    if len(keys) != len(roster):
        raise ValueError("Duplicate roster identity")
    temporary = set()
    permanent = set()
    issues = []
    totals = defaultdict(lambda: [0, 0])
    transitions = []
    for e in records:
        if e["type"]["name"] == "Starting XI":
            t = e["team"]["id"]
            players = {p["player"]["id"] for p in e["tactics"]["lineup"]}
            if t not in active or active[t] or len(players) != 11:
                issues.append("invalid_starting_xi")
            else:
                active[t] = players
    if any(len(p) != 11 for p in active.values()):
        issues.append("incomplete_starting_xi")
    for envelope in model["periods"]:
        period = envelope["period"]
        if not envelope["conditional_eligible"]:
            issues.append(f"inadmissible_envelope:{period}")
            continue
        prior = 0
        for e in [
            e
            for e in records
            if e["period"] == period and e["type"]["name"] not in ("Half Start", "Half End")
        ]:
            now = parse_period_timestamp(e["timestamp"])
            for t, players in active.items():
                for p in players:
                    for i in (0, 1):
                        totals[t, p][i] += now - prior
            prior = now
            t = e["team"]["id"]
            p = e.get("player", {}).get("id")
            kind = e["type"]["name"]
            if kind in ON_FIELD and p is not None and p not in active.get(t, set()):
                issues.append(f"actor_outside_census:{e['id']}")
            transition = False
            if kind == "Substitution":
                new = e["substitution"]["replacement"]["id"]
                if (
                    p not in active[t]
                    or new in active[t]
                    or (t, new) not in keys
                    or (t, new) in permanent
                ):
                    issues.append("invalid_substitution")
                else:
                    active[t].remove(p)
                    permanent.add((t, p))
                    active[t].add(new)
                transition = True
            if kind == "Player Off":
                if p not in active[t]:
                    issues.append("off_without_entry")
                else:
                    active[t].remove(p)
                    (permanent if (e.get("player_off") or {}).get("permanent") else temporary).add(
                        (t, p)
                    )
                transition = True
            if kind == "Player On":
                if (t, p) not in temporary or (t, p) in permanent:
                    issues.append("on_without_temporary_off")
                else:
                    temporary.remove((t, p))
                    active[t].add(p)
                transition = True
            card = (
                (e.get("foul_committed") or e.get("bad_behaviour") or {})
                .get("card", {})
                .get("name")
            )
            if card in ("Red Card", "Second Yellow"):
                if p in active[t]:
                    active[t].remove(p)
                    permanent.add((t, p))
                else:
                    issues.append("off_field_dismissal_unresolved")
                transition = True
            if transition:
                transitions.append(e["id"])
            if any(len(ps) > 11 for ps in active.values()):
                issues.append("census_exceeds_eleven")
        for t, players in active.items():
            for p in players:
                for i in (0, 1):
                    totals[t, p][i] += envelope["observed_end_envelope_ms"][i] - prior
    if temporary:
        issues.append("unpaired_temporary_absence")
    if set(totals) - keys:
        issues.append("unrostered_active_player")
    return dict(
        version=VERSION,
        assumption=ASSUMPTION,
        issues=sorted(set(issues)),
        transition_event_ids=transitions,
        players=[
            dict(
                team_id=t,
                player_id=p,
                conditional_recorded_exposure_ms=totals.get((t, p)) if not issues else None,
                official_minutes=None,
                per90_eligible=False,
            )
            for t, p in sorted(keys)
        ],
        status="conditional_sensitivity_only" if not issues else "unresolved",
    )
