"""Original StatsBomb JSON reconciliation of player involvement. CONFIG BUNDLE."""

import hashlib
import json
import math
import sys
from pathlib import Path

import pyarrow.parquet as pq

from fil.explorer.data import fingerprint, load_match

# Independent vocabulary frozen by the documented metric definition.
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


def main():
    config = json.loads(Path(sys.argv[1]).read_bytes())
    folder = Path(sys.argv[2])
    table, meta = load_match(config)
    raw = json.loads((Path(config["raw"]) / "data/events/8658.json").read_bytes())
    by_id = {e["id"]: e for e in raw}
    roster = json.loads((Path(config["raw"]) / "data/lineups/8658.json").read_bytes())
    manifest = json.loads((folder / "manifest.json").read_bytes())
    assert manifest["inputs"] == fingerprint(config)
    for name, entry in manifest["files"].items():
        body = (folder / name).read_bytes()
        assert hashlib.sha256(body).hexdigest() == entry["sha256"]
    players = pq.read_table(folder / "players.parquet").to_pylist()
    links = pq.read_table(folder / "shot_links.parquet").to_pylist()
    assert len(raw) == table.num_rows == 2978 and (meta["home_score"], meta["away_score"]) == (4, 2)
    roster_by_id = {(t["team_id"], p["player_id"]): p for t in roster for p in t["lineup"]}
    assert {(r["team_id"], r["player_id"]) for r in players} == set(roster_by_id)
    expected_links = {
        (e["id"], e["pass"]["assisted_shot_id"])
        for e in raw
        if e["type"]["name"] == "Pass"
        and e["pass"].get("assisted_shot_id")
        and by_id[e["pass"]["assisted_shot_id"]]["shot"].get("key_pass_id") == e["id"]
    }
    assert {
        (r["pass_event_id"], r["shot_event_id"]) for r in links if r["status"] == "verified"
    } == expected_links
    for r in players:
        native = roster_by_id[r["team_id"], r["player_id"]]
        rows = [
            e
            for e in raw
            if e["team"]["id"] == r["team_id"]
            and (e.get("player") or {}).get("id") == r["player_id"]
        ]
        own = [
            e
            for e in rows
            if e["possession_team"]["id"] == e["team"]["id"]
            and e["type"]["name"] in OWNER_ACTIONS
            and e["period"] in (1, 2, 3, 4)
        ]
        passes = [e for e in rows if e["type"]["name"] == "Pass"]
        complete = [e for e in passes if "outcome" not in e["pass"] and e["pass"].get("recipient")]
        failed = [
            e for e in passes if (e["pass"].get("outcome") or {}).get("id") in (9, 74, 75, 76)
        ]
        progressive = []
        for e in rows:
            kind = e["type"]["name"]
            if kind not in ("Pass", "Carry") or kind == "Pass" and e not in complete:
                continue
            start = e.get("location")
            end = e[kind.lower()].get("end_location")
            if (
                start
                and end
                and end[0] > start[0]
                and math.dist(start[:2], (120, 40)) - math.dist(end[:2], (120, 40)) >= 10
            ):
                progressive.append(e)
        assert r["event_ids"] == [e["id"] for e in rows] and r["selected_events"] == len(rows)
        assert r["owner_action_ids"] == [e["id"] for e in own] and r["owner_actions"] == len(own)
        assert r["possession_ids"] == sorted({e["possession"] for e in own})
        assert r["completed_pass_ids"] == [e["id"] for e in complete] and r[
            "completed_passes"
        ] == len(complete)
        assert r["failed_passes"] == len(failed) and r["unknown_passes"] == len(passes) - len(
            complete
        ) - len(failed)
        assert r["known_pass_completion_fraction"] == (
            len(complete) / (len(complete) + len(failed)) if complete or failed else None
        )
        assert r["progression_ids"] == [e["id"] for e in progressive]
        count = sum(e in own for e in progressive)
        assert r["owner_progressive_actions"] == count
        assert r["owner_progressions_per100_actions"] == (100 * count / len(own) if own else None)
        own_preshot = []
        shots = []
        for e in own:
            following = [
                s
                for s in raw
                if s["type"]["name"] == "Shot"
                and s["team"]["id"] == e["team"]["id"]
                and s["possession"] == e["possession"]
                and s["period"] == e["period"]
                and s["index"] > e["index"]
            ]
            if following:
                own_preshot.append(e["id"])
                shots.extend(s["id"] for s in following)
        assert set(r["pre_shot_action_ids"]) == set(own_preshot) and set(
            r["context_shot_ids"]
        ) == set(shots)
        assert r["pre_shot_possessions"] == len({by_id[i]["possession"] for i in own_preshot})
        direct = [(p, s) for p, s in expected_links if p in {e["id"] for e in rows}]
        assert r["native_shot_links"] == len(direct)
        assert set(r["linked_pass_ids"]) == {p for p, s in direct}
        assert set(r["linked_shot_ids"]) == {s for p, s in direct}
        assert r["native_linked_shot_xg"] == math.fsum(
            by_id[s]["shot"]["statsbomb_xg"] for p, s in direct
        )
        assert r["minutes_played"] is None
        assert (json.loads(r["position_metadata"]) if r["position_metadata"] else []) == native[
            "positions"
        ]
    print(
        json.dumps(
            {
                "source_events": 2978,
                "roster_records": len(players),
                "observed_players": sum(r["selected_events"] > 0 for r in players),
                "attributed_actor_events": sum(r["selected_events"] for r in players),
                "unattributed_actor_events": 2978 - sum(r["selected_events"] for r in players),
                "verified_native_shot_links": len(expected_links),
                "linked_shot_xg": math.fsum(r["native_linked_shot_xg"] for r in players),
                "completed_passes": sum(r["completed_passes"] for r in players),
                "progressive_passes": sum(r["progressive_passes"] for r in players),
                "progressive_carries": sum(r["progressive_carries"] for r in players),
                "minutes": "uncertified; no per90",
                "status": "PASS",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
