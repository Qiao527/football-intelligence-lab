"""Independently reconcile possession facts against original StatsBomb JSON.

CONFIG BUNDLE. Expected membership, boundaries, paths, progression and xG are
computed from raw bytes; production extraction is never used for expected values.
"""

import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from fil.explorer.data import fingerprint, load_match
from fil.metrics.shots import MatchFilter, apply_filter
from fil.possessions.extract import PossessionFacts, select_possessions
from fil.time.clock import PeriodRange

BALL_TYPES = {
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
RESTARTS = {"Kick Off", "Goal Kick", "Throw-in", "Free Kick", "Corner"}


def ms(e):
    h, m, s = e["timestamp"].split(":")
    return round((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)


def point_zone(xy):
    if (
        not xy
        or len(xy) < 2
        or not all(math.isfinite(v) and 0 <= v <= b for v, b in zip(xy[:2], (120, 80), strict=True))
    ):
        return "UNKNOWN"
    x, y = xy[:2]
    return (
        "BOX" if x >= 102 and 18 <= y <= 62 else "ATT" if x >= 80 else "MID" if x >= 40 else "DEF"
    )


def main():
    config = json.loads(Path(sys.argv[1]).read_bytes())
    folder = Path(sys.argv[2])
    table, meta = load_match(config)
    raw = json.loads((Path(config["raw"]) / "data/events/8658.json").read_bytes())
    assert len(raw) == table.num_rows == 2978 and (meta["home_score"], meta["away_score"]) == (4, 2)
    manifest = json.loads((folder / "manifest.json").read_bytes())
    assert manifest["inputs"] == fingerprint(config)
    assert manifest["code_sha"] == folder.name
    assert manifest["source_manifest_sha256"] == meta["source_manifest_sha256"]
    assert manifest["score_manifest_sha256"] == meta["score_manifest_sha256"]
    assert set(p.name for p in folder.iterdir()) == set(manifest["files"]) | {"manifest.json"}
    for name, entry in manifest["files"].items():
        data = (folder / name).read_bytes()
        assert (
            hashlib.sha256(data).hexdigest() == entry["sha256"] and len(data) == entry["size_bytes"]
        )
    possessions = pq.read_table(folder / "possessions.parquet")
    actions = pq.read_table(folder / "possession_actions.parquet")
    assert actions["event_id"].to_pylist() == [e["id"] for e in raw]
    assert len(set(actions["event_id"].to_pylist())) == 2978
    groups = defaultdict(list)
    for e in raw:
        groups[e["possession"]].append(e)
    assert possessions["possession_id"].to_pylist() == list(groups)
    actual = {r["event_id"]: r for r in actions.to_pylist()}
    expected = {}
    for e in raw:
        a = actual[e["id"]]
        kind = e["type"]["name"]
        owner = e["team"]["id"] == e["possession_team"]["id"]
        own = owner and kind in BALL_TYPES and e["period"] in (1, 2, 3, 4)
        assert (
            a["possession_id"] == e["possession"]
            and a["possession_team_id"] == e["possession_team"]["id"]
        )
        assert (
            a["team_id"] == e["team"]["id"]
            and a["provider_index"] == e["index"]
            and a["period"] == e["period"]
        )
        assert a["is_owner_action"] is own
        assert a["event_type"] == kind and a["period_elapsed_ms"] == ms(e)
        assert a["player_id"] == (e.get("player") or {}).get("id")
        for index, name in enumerate(("x", "y")):
            xy = e.get("location") or []
            assert a[name] == (xy[index] if len(xy) > index else None)
        assert a["zone"] == point_zone(e.get("location"))
        detail = e.get("pass" if kind == "Pass" else "carry", {})
        if kind in ("Pass", "Carry"):
            for index, name in enumerate(("end_x", "end_y")):
                xy = detail.get("end_location") or []
                assert a[name] == (xy[index] if len(xy) > index else None)
        completed = kind == "Pass" and "outcome" not in detail and bool(detail.get("recipient"))
        moving = own and (completed or kind == "Carry")
        start = e.get("location")
        end = detail.get("end_location")
        valid = moving and point_zone(start) != "UNKNOWN" and point_zone(end) != "UNKNOWN"
        p = third = box = None
        if valid:
            gain = math.dist(start[:2], (120, 40)) - math.dist(end[:2], (120, 40))
            p = end[0] > start[0] and gain >= 10
            third = start[0] < 80 <= end[0]
            box = point_zone(start) != "BOX" and point_zone(end) == "BOX"
        assert (a["progressive"], a["final_third_entry"], a["box_entry"]) == (p, third, box)
        expected[e["id"]] = {
            "own": own,
            "moving": moving,
            "completed": completed,
            "progressive": p,
            "third": third,
            "box": box,
            "start_zone": point_zone(start),
            "end_zone": point_zone(end),
        }
    group_list = list(groups.values())
    for i, r in enumerate(possessions.to_pylist()):
        g = groups[r["possession_id"]]
        team = g[0]["possession_team"]["id"]
        own = [e for e in g if expected[e["id"]]["own"]]
        shots = [e for e in own if e["type"]["name"] == "Shot"]
        states = []
        previous = None
        for e in own:
            if previous is not None and previous != e["period"]:
                states.append("PERIOD_BREAK")
            candidates = [expected[e["id"]]["start_zone"]]
            if expected[e["id"]]["moving"]:
                candidates.append(expected[e["id"]]["end_zone"])
            for z in candidates:
                if not states or z != states[-1]:
                    states.append(z)
            previous = e["period"]
        assert r["zone_path"] == states
        assert r["event_ids"] == [e["id"] for e in g]
        assert r["owner_action_ids"] == [e["id"] for e in own]
        assert r["path_event_ids"] == [e["id"] for e in own if expected[e["id"]]["moving"]]
        assert [actual[e["id"]]["sequence"] for e in g] == list(range(1, len(g) + 1))
        assert r["start_event_id"] == g[0]["id"] and r["end_event_id"] == g[-1]["id"]
        assert r["event_count"] == len(g) and r["owner_actions"] == len(own)
        assert r["opponent_events"] == sum(e["team"]["id"] != team for e in g)
        assert r["shot_event_ids"] == [e["id"] for e in shots] and r["shot_count"] == len(shots)
        assert r["shot_xg_sum"] == math.fsum(e["shot"]["statsbomb_xg"] for e in shots)
        same = len({e["period"] for e in g}) == 1
        assert r["observed_span_seconds"] == (None if not same else (ms(g[-1]) - ms(g[0])) / 1000)
        assert r["time_to_first_shot_seconds"] == (
            (ms(shots[0]) - ms(g[0])) / 1000 if shots and same else None
        )
        for field, key in [
            ("progressive_actions", "progressive"),
            ("final_third_entries", "third"),
            ("box_entries", "box"),
        ]:
            assert r[field] == sum(expected[e["id"]][key] is True for e in own)
        assert r["completed_passes"] == sum(expected[e["id"]]["completed"] for e in own)
        assert r["carries"] == sum(e["type"]["name"] == "Carry" for e in own)
        assert r["reached_final_third"] is any(z in ("ATT", "BOX") for z in states)
        assert r["reached_box"] is ("BOX" in states)
        reached = [
            j + 1
            for j, e in enumerate(own)
            if expected[e["id"]]["start_zone"] in ("ATT", "BOX")
            or expected[e["id"]]["moving"]
            and expected[e["id"]]["end_zone"] in ("ATT", "BOX")
        ]
        assert r["actions_to_first_final_third"] == (reached[0] if reached else None)
        nxt = group_list[i + 1][0] if i + 1 < len(group_list) else None
        assert r["next_possession_id"] == (nxt["possession"] if nxt else None)
        assert r["next_team_id"] == (nxt["possession_team"]["id"] if nxt else None)
        last = own[-1] if own else None
        first = own[0] if own else None
        assert r["entry_event_id"] == (first["id"] if first else None)
        assert r["exit_event_id"] == (last["id"] if last else None)
        assert r["participant_ids"] == sorted({e["player"]["id"] for e in own if e.get("player")})
        assert r["start_zone"] == (expected[first["id"]]["start_zone"] if first else "UNKNOWN")
        assert r["end_zone"] == (
            expected[last["id"]]["end_zone"]
            if last and expected[last["id"]]["moving"]
            else expected[last["id"]]["start_zone"]
            if last
            else "UNKNOWN"
        )
        native_type = ((first.get("pass") or {}).get("type") or {}).get("name") if first else None
        assert r["start_reason"] == (
            f"native_restart:{native_type}"
            if native_type in RESTARTS
            else f"first_owner_record:{first['type']['name']}"
            if first
            else "unknown"
        )
        tail = [e for e in g if last and e["index"] >= last["index"]]
        out = any(
            e.get("out") is True
            or (e.get("pass", {}).get("outcome") or {}).get("name") in ("Out", "Pass Offside")
            for e in tail
        )
        foul = any(
            e["type"]["name"] in ("Foul Won", "Foul Committed")
            and not (e.get("foul_won") or e.get("foul_committed") or {}).get("advantage")
            for e in tail
        )
        boundary = (
            not same
            or any(e["type"]["name"] == "Half End" for e in g)
            or bool(nxt and nxt["period"] != g[-1]["period"])
        )
        loss = bool(
            last
            and (
                last["type"]["name"] in ("Miscontrol", "Dispossessed")
                or last["type"]["name"] == "Pass"
                and last["pass"].get("outcome") == {"id": 9, "name": "Incomplete"}
                or last["type"]["name"] == "Dribble"
                and (last["dribble"].get("outcome") or {}).get("name") == "Incomplete"
            )
        )
        next_own = (
            next((e for e in group_list[i + 1] if expected[e["id"]]["own"]), None) if nxt else None
        )
        restart = bool(
            next_own and (next_own.get("pass", {}).get("type") or {}).get("name") in RESTARTS
        )
        turnover = bool(
            loss
            and nxt
            and nxt["period"] == last["period"]
            and nxt["possession_team"]["id"] != team
            and not (out or foul or boundary or restart)
            and not (
                manifest["version"] == "fil-possession-2"
                and any(e["type"]["name"] in ("Own Goal For", "Own Goal Against") for e in g)
            )
        )
        shot_end = bool(last and last["type"]["name"] == "Shot")
        assert r["turnover"] is turnover and r["shot_ending"] is shot_end
        reason = (
            "period_boundary"
            if boundary
            else "own_goal_recorded"
            if any(e["type"]["name"] in ("Own Goal For", "Own Goal Against") for e in g)
            else "shot"
            if shot_end
            else "out_of_play"
            if out
            else "foul_observed"
            if foul
            else "turnover"
            if turnover
            else "provider_boundary_unresolved"
        )
        assert r["end_reason"] == reason
        if manifest["version"] == "fil-possession-2":
            evidence = set(r["boundary_evidence_ids"])
            allowed = {e["id"] for e in g}
            if nxt:
                allowed.update(e["id"] for e in group_list[i + 1])
            assert evidence <= allowed
            assert g[-1]["id"] in evidence
            for e in g:
                if e["type"]["name"] in ("Own Goal For", "Own Goal Against", "Half End"):
                    assert e["id"] in evidence
            for e in tail:
                if (
                    e.get("out") is True
                    or (e.get("pass", {}).get("outcome") or {}).get("name")
                    in ("Out", "Pass Offside")
                    or e["type"]["name"] in ("Foul Won", "Foul Committed")
                ):
                    assert e["id"] in evidence
            if restart:
                assert next_own["id"] in evidence
    # Actual shared-selector queries compared to independently selected native IDs.
    facts = PossessionFacts(possessions, actions, {})
    durations = {p: max(ms(e) for e in raw if e["period"] == p) for p in (1, 2)}
    scores = {771: 0, 785: 0}
    contexts = {}
    counted = set()
    by_id = {e["id"]: e for e in raw}
    for e in raw:
        team = e["team"]["id"]
        diff = scores[team] - scores[785 if team == 771 else 771]
        contexts[e["id"]] = "level" if diff == 0 else "leading" if diff > 0 else "trailing"
        if e["type"]["name"] == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            scores[team] += 1
        if e["type"]["name"] in ("Own Goal For", "Own Goal Against") and e["id"] not in counted:
            pair = [e] + [
                by_id[j]
                for j in e.get("related_events", [])
                if by_id[j]["type"]["name"] in ("Own Goal For", "Own Goal Against")
            ]
            scores[next(v["team"]["id"] for v in pair if v["type"]["name"] == "Own Goal For")] += 1
            counted.update(v["id"] for v in pair)
    assert scores == {771: 4, 785: 2}
    queries = 0
    for width in (300000, 600000, 900000):
        for period, duration in durations.items():
            for start in range(0, duration, width):
                end = min(start + width, duration)
                terminal = end == duration
                for context in (None, "level", "leading", "trailing"):
                    for team in (None, 771, 785):
                        ids = {
                            e["possession"]
                            for e in raw
                            if e["period"] == period
                            and (start <= ms(e) < end or terminal and ms(e) == end)
                            and (context is None or contexts[e["id"]] == context)
                            and (team is None or e["team"]["id"] == team)
                        }
                        chosen = apply_filter(
                            table,
                            MatchFilter(
                                (PeriodRange(period, start, end, terminal),),
                                team_id=team,
                                score_state=context,
                                home_team_id=771,
                                away_team_id=785,
                            ),
                        )
                        assert (
                            set(select_possessions(facts, chosen)["possession_id"].to_pylist())
                            == ids
                        )
                        queries += 1
    result = {
        "source_events": 2978,
        "native_possessions": len(groups),
        "opponent_records": sum(e["team"]["id"] != e["possession_team"]["id"] for e in raw),
        "shot_possessions": sum(r["shot_count"] > 0 for r in possessions.to_pylist()),
        "shot_events": sum(possessions["shot_count"].to_pylist()),
        "shot_xg_sum": math.fsum(possessions["shot_xg_sum"].to_pylist()),
        "turnover_endings": sum(possessions["turnover"].to_pylist()),
        "terminal_states": dict(Counter(possessions["end_reason"].to_pylist())),
        "window_team_score_queries": queries,
        "cross_period_native_ids": [
            r["possession_id"]
            for r in possessions.to_pylist()
            if r["start_period"] != r["end_period"]
        ],
        "official_score": [4, 2],
        "physical_directions": "unknown",
        "status": "PASS",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
