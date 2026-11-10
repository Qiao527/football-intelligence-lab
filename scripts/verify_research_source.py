"""Independently recompute the current authorised corpus/case from original JSON.

CONFIG BUNDLE. No production case, exposure or corpus extraction is used for
expected values. All outputs stay local under unchanged provider-use restrictions.
"""

import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from fil.ingestion.statsbomb import verify_bundle


def ms(e):
    h, m, s = e["timestamp"].split(":")
    return round((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)


def main():
    c = json.loads(Path(sys.argv[1]).read_bytes())
    folder = Path(sys.argv[2])
    verify_bundle(Path(c["raw"]))
    raw = json.loads((Path(c["raw"]) / "data/events/8658.json").read_bytes())
    roster = json.loads((Path(c["raw"]) / "data/lineups/8658.json").read_bytes())
    manifest = json.loads((folder / "manifest.json").read_bytes())
    assert {p.name for p in folder.iterdir()} == set(manifest["files"]) | {"manifest.json"}
    for name, h in manifest["files"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == h
    table = pq.ParquetFile(folder / "events.parquet").read()
    corpus = json.loads((folder / "corpus.json").read_bytes())
    case = json.loads((folder / "case.json").read_bytes())
    assert table.num_rows == len(raw) == 2978 and corpus["match_count"] == 1
    assert table["event_id"].to_pylist() == [e["id"] for e in raw]
    assert [json.loads(s) for s in table["source_record_json"].to_pylist()] == raw
    assert not corpus["identity_conflicts"]
    identities = {p["provider_player_id"]: p for p in corpus["identities"]}
    assert set(identities) == {p["player_id"] for t in roster for p in t["lineup"]}
    assert len(identities) == 45
    for player, identity in identities.items():
        aliases = {
            p["player_name"] for t in roster for p in t["lineup"] if p["player_id"] == player
        }
        aliases.update(e["player"]["name"] for e in raw if e.get("player", {}).get("id") == player)
        assert identity["aliases"] == sorted(aliases)

    scores = {771: 0, 785: 0}
    counted = set()
    states = {}
    for e in raw:
        states[e["id"]] = (
            "leading"
            if scores[771] > scores[785]
            else "trailing"
            if scores[771] < scores[785]
            else "level"
        )
        if e["type"]["name"] == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            scores[e["team"]["id"]] += 1
        if e["type"]["name"] in ("Own Goal For", "Own Goal Against") and e["id"] not in counted:
            team = (
                e["team"]["id"]
                if e["type"]["name"] == "Own Goal For"
                else (785 if e["team"]["id"] == 771 else 771)
            )
            scores[team] += 1
            counted.add(e["id"])
            counted.update(e.get("related_events", []))
    assert scores == {771: 4, 785: 2}
    shots = defaultdict(list)
    for e in raw:
        if e["type"]["name"] == "Shot" and e["team"]["id"] == e["possession_team"]["id"]:
            shots[e["possession"], e["team"]["id"], e["period"]].append(e)
    rows = []
    for e in raw:
        kind = e["type"]["name"]
        if (
            e["team"]["id"] != 771
            or e["possession_team"]["id"] != 771
            or e["period"] not in (1, 2, 3, 4)
        ):
            continue
        if kind not in ("Pass", "Carry"):
            continue
        detail = e[kind.lower()]
        if kind == "Pass" and ("outcome" in detail or not detail.get("recipient")):
            continue
        start, end = e.get("location"), detail.get("end_location")
        valid = all(
            p
            and len(p) >= 2
            and all(
                math.isfinite(v) and 0 <= v <= bound
                for v, bound in zip(p[:2], (120, 80), strict=True)
            )
            for p in (start, end)
        )
        delta = end[0] - start[0] if valid else None
        gain = math.dist(start[:2], (120, 40)) - math.dist(end[:2], (120, 40)) if valid else None
        rows.append(
            dict(
                event_id=e["id"],
                player_id=e["player"]["id"],
                period=e["period"],
                state=states[e["id"]],
                delta=delta,
                gain=gain,
                later=[
                    s["id"]
                    for s in shots[e["possession"], 771, e["period"]]
                    if s["index"] > e["index"]
                ],
            )
        )

    def check_summary(actual, subset):
        for rule, a in actual.items():
            threshold = int(rule.rsplit("_", 1)[1]) if rule.startswith("progression_gain") else None
            selected = [
                r
                for r in subset
                if rule == "all_completed_moves"
                or r["delta"] is not None
                and r["delta"] > 0
                and (threshold is None or r["gain"] >= threshold)
            ]
            assert a["event_ids"] == [r["event_id"] for r in selected]
            assert a["n"] == len(selected)
            hits = [r["event_id"] for r in selected if r["later"]]
            assert a["shot_followed_n"] == len(hits) and a["shot_followed_ids"] == hits
            assert a["shot_followed_fraction"] == (len(hits) / len(selected) if selected else None)

    native_shots = [
        e for e in raw if e["type"]["name"] == "Shot" and e.get("player", {}).get("id") == 20004
    ]
    assert case["conventional"]["shot_event_ids"] == [e["id"] for e in native_shots]
    assert case["conventional"]["shot_goals"] == sum(
        e["shot"]["outcome"]["name"] == "Goal" for e in native_shots
    )
    assert math.isclose(
        case["conventional"]["source_shot_xg"],
        math.fsum(e["shot"]["statsbomb_xg"] for e in native_shots),
        abs_tol=1e-12,
    )
    own = [r for r in rows if r["player_id"] == 20004]
    check_summary(case["player_baselines"], own)
    check_summary(case["team_baselines"], rows)
    for period, a in case["period_comparison"].items():
        check_summary(a, [r for r in own if r["period"] == int(period)])
    for state, a in case["pre_event_state_comparison"].items():
        check_summary(a, [r for r in own if r["state"] == state])
    for a in case["player_moves"]:
        r = next(r for r in own if r["event_id"] == a["event_id"])
        assert a["later_shot_ids"] == r["later"] and a["delta_x"] == r["delta"]
        assert a["score_state"] == r["state"]
    eligible10 = set(case["player_baselines"]["progression_gain_10"]["event_ids"])
    assert case["shot_context_moves_excluded_by_gain10"] == [
        r["event_id"] for r in own if r["later"] and r["event_id"] not in eligible10
    ]
    assert case["gain10_moves_without_later_shot"] == [
        r["event_id"] for r in own if not r["later"] and r["event_id"] in eligible10
    ]
    # Independently integrate the team census over transition-to-transition time.
    active = {
        e["team"]["id"]: {p["player"]["id"] for p in e["tactics"]["lineup"]}
        for e in raw
        if e["type"]["name"] == "Starting XI"
    }
    durations = defaultdict(float)
    transitions = []
    for period in (1, 2):
        end = max(ms(e) for e in raw if e["period"] == period and e["type"]["name"] == "Half End")
        cursor = 0
        changes = [
            e
            for e in raw
            if e["period"] == period
            and e["type"]["name"] in ("Substitution", "Player Off", "Player On")
        ]
        for e in changes + [None]:
            stop = ms(e) if e else end
            assert stop >= cursor
            for t, ps in active.items():
                for player in ps:
                    durations[t, player] += (stop - cursor) / 1000
            cursor = stop
            if e is None:
                continue
            t, p = e["team"]["id"], e["player"]["id"]
            kind = e["type"]["name"]
            if kind in ("Substitution", "Player Off"):
                active[t].remove(p)
            if kind == "Substitution":
                active[t].add(e["substitution"]["replacement"]["id"])
            if kind == "Player On":
                active[t].add(p)
            transitions.append(e["id"])
    census = corpus["matches"][0]["exposure"]
    assert census["status"] == "recorded_chronology_consistent" and not census["issues"]
    assert [r["event_id"] for r in census["transitions"]] == transitions
    for p in census["players"]:
        expected = durations.get((p["team_id"], p["player_id"]))
        assert p["minutes_played"] is None and p["per90_eligible"] is False
        if expected is None:
            assert p["provisional_recorded_seconds"] is None
        else:
            assert math.isclose(p["provisional_recorded_seconds"], expected, abs_tol=1e-8)
    assert math.isclose(
        case["source_xg"],
        math.fsum(e["shot"]["statsbomb_xg"] for e in raw if e["type"]["name"] == "Shot"),
        abs_tol=1e-12,
    )
    assert case["status"] == "inconclusive" and not case["scientifically_validated"]
    print(
        json.dumps(
            dict(
                status="PASS",
                source_events=2978,
                roster_identities=45,
                source_transition_records=len(transitions),
                official_score=[4, 2],
                case="inconclusive",
                player_baselines={
                    k: {n: v for n, v in r.items() if n not in ("event_ids", "shot_followed_ids")}
                    for k, r in case["player_baselines"].items()
                },
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
