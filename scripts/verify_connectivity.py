"""Independent raw-JSON verifier; intentionally imports no FIL extraction/calculation code."""

import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cell(point, xbins, ybins):
    if not isinstance(point, list) or len(point) != 2:
        return None
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in point):
        return None
    x, y = point
    if not 0 <= x <= 120 or not 0 <= y <= 80:
        return None
    # Different formulation including exact outer boundary.
    return (
        sum(x >= k * 120 / xbins for k in range(1, xbins)),
        sum(y >= k * 80 / ybins for k in range(1, ybins)),
    )


def verify(bundle: Path) -> dict:
    manifest = json.loads((bundle / "manifest.json").read_bytes())
    for path, expected in manifest["protected_inputs"].items():
        assert sha(path) == expected, f"Protected source changed: {path}"
    for name, expected in manifest["files"].items():
        assert sha(bundle / name) == expected, f"Derived file changed: {name}"
    inputs = json.loads((bundle / "source-inputs.json").read_bytes())
    results = json.loads((bundle / "evidence.json").read_bytes())
    assert len(inputs) == len(results) == 64
    total, chain_total, pass_total = 0, 0, 0
    for source, output in zip(inputs, results, strict=True):
        raw = json.loads(Path(source["events"]).read_bytes())
        roster = json.loads(Path(source["lineups"]).read_bytes())
        by = {e["id"]: e for e in raw}
        assert len(raw) == len(by) == output["source_event_count"]
        assert source["match_id"] == output["match_id"]
        total += len(raw)
        roster_by = {p["player_id"]: team["team_id"] for team in roster for p in team["lineup"]}
        expected_passes, sent, received = set(), defaultdict(list), defaultdict(list)
        for e in raw:
            if e["type"]["name"] == "Pass" and 1 <= e["period"] <= 4:
                p = e.get("pass", {})
                a, b = e.get("player", {}).get("id"), p.get("recipient", {}).get("id")
                if "outcome" not in p and a is not None and b is not None and a != b:
                    assert roster_by[a] == roster_by[b] == e["team"]["id"]
                    expected_passes.add(e["id"])
                    sent[a].append(e["id"])
                    received[b].append(e["id"])
        actual_passes = {p["event_id"] for p in output["passes"] if not p["exclusion_reasons"]}
        assert expected_passes == actual_passes
        assert {p["event_id"] for p in output["passes"]} == {
            e["id"] for e in raw if e["type"]["name"] == "Pass"
        }
        pass_total += len(expected_passes)
        # Independent membership and one-pass state machine. Never bridge an interruption.
        memberships = defaultdict(list)
        for n, e in enumerate(raw):
            if e.get("possession") is not None:
                memberships[e["possession"]].append(n)
        good = set()
        for pid, indices in memberships.items():
            members = [raw[n] for n in indices]
            periods = {e["period"] for e in members}
            owners = {e.get("possession_team", {}).get("id") for e in members}
            if (
                len(periods) == len(owners) == 1
                and periods <= {1, 2, 3, 4}
                and owners <= set(output["team_ids"])
                and indices[-1] - indices[0] + 1 == len(indices)
            ):
                good.add(pid)
        assert set(memberships) - good == {
            r["possession_id"] for r in output["excluded_memberships"]
        }
        pending, middle, expected_chains = None, [], {}
        for e in raw:
            if e.get("possession") not in good or e["team"]["id"] != e["possession_team"]["id"]:
                pending, middle = None, []
                continue
            if pending and e["possession"] != pending["possession"]:
                pending, middle = None, []
            if e["id"] in expected_passes:
                if pending and pending["pass"]["recipient"]["id"] == e["player"]["id"]:
                    key = pending["id"] + "/" + e["id"]
                    expected_chains[key] = (pending, e, middle)
                pending, middle = e, []
            elif pending:
                if e.get("player", {}).get("id") == pending["pass"]["recipient"]["id"] and (
                    e["type"]["name"] == "Carry"
                    or (
                        e["type"]["name"] == "Ball Receipt*"
                        and "outcome" not in e.get("ball_receipt", {})
                    )
                ):
                    middle = middle + [e["id"]]
                else:
                    pending, middle = None, []
        actual = {c["chain_id"]: c for c in output["chains"]}
        assert set(actual) == set(expected_chains)
        chain_total += len(actual)
        for key, (a, b, between) in expected_chains.items():
            c = actual[key]
            assert c["pass_event_ids"] == [a["id"], b["id"]]
            assert c["intervening_event_ids"] == between
            assert c["player_ids"] == [
                a["player"]["id"],
                b["player"]["id"],
                b["pass"]["recipient"]["id"],
            ]
            assert c["nonreturn"] == (c["player_ids"][0] != c["player_ids"][2])
            for name, x, y in (("6x4", 6, 4), ("3x2", 3, 2)):
                start, end = (
                    cell(a.get("location"), x, y),
                    cell(b["pass"].get("end_location"), x, y),
                )
                expected = None if start is None or end is None else start != end
                assert c["zone_transition"][name] is expected
            later = [
                r["id"]
                for r in raw
                if r.get("possession") == b["possession"]
                and r["team"]["id"] == b["team"]["id"]
                and r["index"] > b["index"]
                and r["type"]["name"] == "Shot"
            ]
            assert c["later_recorded_shot_ids"] == later
            assert c["source_manifest_sha256"] == source["source_manifest_sha256"]
            assert c["alternative_observed_chain_ids"] == [
                d["chain_id"]
                for d in output["chains"]
                if d["possession_id"] == c["possession_id"]
                and d["player_ids"][0] == c["player_ids"][0]
                and d["player_ids"][2] == c["player_ids"][2]
                and d["player_ids"][1] != c["player_ids"][1]
            ]
        # Exact per-roster denominators and contextual bins, including genuine zero rows.
        assert len(output["players"]) == len(roster_by)
        for player in output["players"]:
            pid, team = player["player_id"], player["team_id"]
            assert player["completed_pass_ids"] == sent[pid]
            assert player["received_pass_ids"] == received[pid]
            assert player["completed_passes"] == len(sent[pid])
            assert player["received_passes"] == len(received[pid])
            assert player["out_degree"] == len(
                {by[i]["pass"]["recipient"]["id"] for i in sent[pid]}
            )
            assert player["in_degree"] == len({by[i]["player"]["id"] for i in received[pid]})
            actions = [
                e["id"] for e in raw if e["period"] < 5 and e.get("player", {}).get("id") == pid
            ]
            assert player["original_actor_event_ids"] == actions
            assert player["actor_records"] == len(actions)
            ids = [c["chain_id"] for c in output["chains"] if c["player_ids"][1] == pid]
            assert player["chain_ids"] == ids
            chains = [actual[k] for k in ids]
            n = sum(c["zone_transition"]["6x4"] is not None for c in chains)
            s = sum(c["zone_transition"]["6x4"] is True and c["nonreturn"] for c in chains)
            assert player["observed_chains"] == len(chains)
            assert player["known_geometry_chains"] == n
            assert player["cross_zone_nonreturn"] == s
            assert player["conditional_chain_fraction"] == (s / n if n else None)
            assert player["team_completed_pass_opportunities"] == sum(
                len(events) for p, events in sent.items() if roster_by[p] == team
            )
            assert player["official_minutes"] is player["ability_estimate"] is None
            own_memberships = {
                p for p in good if raw[memberships[p][0]]["possession_team"]["id"] == team
            }
            involved = {
                p
                for p in own_memberships
                if any(
                    raw[j].get("player", {}).get("id") == pid
                    and raw[j]["team"]["id"] == team
                    or raw[j]["id"] in received[pid]
                    for j in memberships[p]
                )
            }
            assert set(player["possession_ids"]) == involved
            assert player["possession_participation"] == len(involved)
            assert player["team_eligible_possessions"] == len(own_memberships)
    assert total == 227825
    summary = json.loads((bundle / "summary.json").read_bytes())
    assert summary["original_events"] == total
    assert summary["observed_chains"] == chain_total and summary["completed_passes"] == pass_total
    assert summary["scientific_verdict"] == "INCONCLUSIVE" and not summary["ability_identified"]
    return dict(
        status="PASS",
        original_events=total,
        matches=len(results),
        completed_passes=pass_total,
        chains=chain_total,
        verifier_sha256=sha(__file__),
        bundle_manifest_sha256=sha(bundle / "manifest.json"),
    )


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1])), indent=2, sort_keys=True))
