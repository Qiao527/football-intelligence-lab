"""Offline original-release JSON adapter contract, pending primary-source audit.

Deliberately TEST_ONLY: no downloader, production registration or provider pooling.
Tag mappings remain provisional until original release documentation is verified.
"""

import hashlib
import json
import math
from collections import Counter

import pyarrow as pa

VERSION = "fil-wyscout-original-testonly-1"
PERIODS = frozenset({"1H", "2H", "E1", "E2", "P"})


def _id(value):
    if type(value) is not int or value <= 0:
        raise ValueError("Malformed original provider ID")
    return value


def adapt_test_only(
    events: list[dict], match: dict, teams: list[dict], players: list[dict], *, provenance: dict
) -> tuple[pa.Table, dict]:
    """Preserve original JSON, numeric IDs and array order; never infer recipients.

    Original playerId=0 is preserved as a sentinel, with a null actor identity.
    No lineups, minutes, possession labels, xG or physical orientation are invented.
    Payload SHA-256 is over the supplied canonical JSON serialization, not a claim
    about an upstream file hash. Production bytes must get a separate raw manifest.
    """
    if provenance.get("classification") != "TEST_ONLY":
        raise ValueError("Primary source/owner scope unapproved: TEST_ONLY input required")
    mid = _id(match.get("wyId"))
    team_ids = [_id(t.get("wyId")) for t in teams]
    player_ids = [_id(p.get("wyId")) for p in players]
    if len(team_ids) != len(set(team_ids)) or len(player_ids) != len(set(player_ids)):
        raise ValueError("Duplicate team/player metadata identity")
    members = match.get("teamsData", {})
    if len(members) != 2 or any(str(_id(v.get("teamId"))) != k for k, v in members.items()):
        raise ValueError("Malformed match team identity")
    match_teams = {v["teamId"] for v in members.values()}
    if not match_teams <= set(team_ids):
        raise ValueError("Match team metadata missing")
    rosters = {}
    transitions = []
    for v in members.values():
        formation = v.get("formation") or {}
        lineup, bench = formation.get("lineup"), formation.get("bench")
        roster = (lineup or []) + (bench or [])
        ids = [_id(r.get("playerId")) for r in roster]
        if len(ids) != len(set(ids)) or not set(ids) <= set(player_ids):
            raise ValueError("Invalid lineup/bench player identity")
        rosters[v["teamId"]] = set(ids)
        substitutions = formation.get("substitutions")
        if substitutions is not None:
            if not isinstance(substitutions, list):
                raise ValueError("Malformed substitution records")
            for s in substitutions:
                if any(_id(s.get(k)) not in set(ids) for k in ("playerIn", "playerOut")):
                    raise ValueError("Unrostered substitution identity")
            transitions.extend(dict(team_id=v["teamId"], source_record=s) for s in substitutions)
    team_a, team_b = sorted(match_teams)
    if rosters[team_a] & rosters[team_b]:
        raise ValueError("Player rostered on both match teams")
    rows, seen, clocks, unrostered = [], set(), {}, set()
    for sequence, e in enumerate(events, 1):
        eid = _id(e.get("id"))
        if eid in seen or _id(e.get("matchId")) != mid:
            raise ValueError("Duplicate event ID or foreign match")
        seen.add(eid)
        team = _id(e.get("teamId"))
        actor = e.get("playerId")
        if team not in match_teams or type(actor) is not int or actor < 0:
            raise ValueError("Invalid event team/player identity")
        if actor and actor not in player_ids:
            raise ValueError("Event player metadata missing")
        if actor and actor not in rosters[team]:
            unrostered.add((team, actor))
        period, sec = e.get("matchPeriod"), e.get("eventSec")
        if (
            period not in PERIODS
            or type(sec) not in (int, float)
            or not math.isfinite(sec)
            or sec < 0
        ):
            raise ValueError("Malformed native period/clock")
        ordering = (
            "clock_reversal" if period in clocks and sec < clocks[period] else "array_order_only"
        )
        clocks[period] = sec
        positions = e.get("positions")
        if not isinstance(positions, list):
            raise ValueError("Malformed native positions")
        for p in positions:
            if any(
                type(p.get(k)) not in (int, float)
                or not math.isfinite(p[k])
                or not 0 <= p[k] <= 100
                for k in ("x", "y")
            ):
                raise ValueError("Out-of-domain native coordinates")
        tags = e.get("tags")
        if not isinstance(tags, list) or any(type(t.get("id")) is not int for t in tags):
            raise ValueError("Malformed native tags")
        tag_ids = {t["id"] for t in tags}
        _id(e.get("eventId"))
        status = "unknown"
        if e["eventId"] == 8:
            status = (
                "conflicting_tags"
                if {1801, 1802} <= tag_ids
                else "accurate_tag"
                if 1801 in tag_ids
                else "inaccurate_tag"
                if 1802 in tag_ids
                else "unknown"
            )
        rows.append(
            dict(
                source="wyscout_figshare_TEST_ONLY",
                match_id=mid,
                original_event_id=eid,
                original_array_sequence=sequence,
                team_id=team,
                original_player_id=actor,
                actor_player_id=actor or None,
                match_period=period,
                event_seconds=sec,
                event_type_id=e["eventId"],
                subevent_type_id=e.get("subEventId"),
                native_positions_json=json.dumps(positions, sort_keys=True),
                source_record_json=json.dumps(e, sort_keys=True),
                provisional_pass_tag_status=status,
                ordering_status=ordering,
            )
        )
    if not rows:
        raise ValueError("Empty source match")
    payload = json.dumps(events, sort_keys=True, separators=(",", ":")).encode()
    return pa.Table.from_pylist(rows), dict(
        adapter_version=VERSION,
        classification="TEST_ONLY",
        production_eligible=False,
        match_id=mid,
        raw_count=len(events),
        output_count=len(rows),
        test_payload_sha256=hashlib.sha256(payload).hexdigest(),
        coordinate_system="raw_wyscout_percent_0_100; physical orientation unverified",
        unknown_type_count=sum(e["eventId"] not in range(1, 11) for e in events),
        pass_tag_counts=dict(Counter(r["provisional_pass_tag_status"] for r in rows)),
        unrostered_actors=sorted(unrostered),
        missing_actor_count=sum(r["actor_player_id"] is None for r in rows),
        missing_positions=sum(not e["positions"] for e in events),
        lineups_and_substitutions=members,
        substitution_records=transitions,
        exposure_seconds=None,
        exposure_status="unverified period boundaries and substitution clock semantics",
        source_metadata=dict(match=match, teams=teams, players=players),
        possession_status="not supplied; no StatsBomb-style segmentation inferred",
        source_xg_status="not supplied; no model generated",
        training_eligible=False,
    )
