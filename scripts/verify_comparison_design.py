"""Independent raw-source extraction and BFS/spanning-forest verification; no production imports."""

import hashlib
import json
import sys
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path

from verify_connectivity import verify as verify_attribute_parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def key(record, design):
    if design == "team":
        return (record["team_id"],)
    result = (record["team_id"], record["match_id"])
    if design != "team_match":
        if record["native_cell"] is None:
            return None
        result += (record["period"], record["score_state"], record["native_cell"])
    if design == "known_position_context":
        if record["position_id"] is None:
            return None
        result += (record["position_id"],)
    return result


def connected(edges):
    adjacent = defaultdict(set)
    for a, b in edges:
        adjacent[a].add(b)
        adjacent[b].add(a)
    seen = set()
    groups = []
    forest = []
    for start in sorted(adjacent):
        if start in seen:
            continue
        queue = deque([start])
        seen.add(start)
        group = []
        while queue:
            node = queue.popleft()
            group.append(node)
            for other in sorted(adjacent[node]):
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
                    forest.append((node, other))
        groups.append(sorted(group))
    groups.sort(key=lambda g: g[0])
    assert len(forest) == len(adjacent) - len(groups)
    # A spanning tree identifies all columns relative to one component offset;
    # every edge has one player and one context. Independent null vectors attain the bound.
    component = {n: i for i, g in enumerate(groups) for n in g}
    for a, b in edges:
        assert component[a] == component[b] and a.startswith("p:") and b.startswith("c:")
    return groups, len(forest)


def verify(folder: Path):
    manifest = json.loads((folder / "manifest.json").read_bytes())
    for name, expected in manifest["files"].items():
        assert sha(folder / name) == expected
    for name, expected in manifest["protected_inputs"].items():
        assert sha(name) == expected
    parent = Path(manifest["parent_bundle"])
    assert sha(parent / "manifest.json") == (
        "0f45169769931d49167b2e6ce38ebf9b4848caef40161d0a6543673148d98f71"
    )
    assert sha(Path("docs/research/COMPARISON_DESIGN_PROTOCOL.md")) == manifest["protocol_sha256"]
    pm = json.loads((parent / "manifest.json").read_bytes())
    attribute = Path(pm["parent_bundle"])
    proof = verify_attribute_parent(attribute)
    inputs = json.loads((attribute / "source-inputs.json").read_bytes())
    old = json.loads((attribute / "evidence.json").read_bytes())
    records = json.loads((folder / "evidence.json").read_bytes())
    observed = {r["record_id"]: r for r in records}
    assert len(observed) == len(records)
    expected_ids = set()
    roster = set()
    exclusions = []
    for source, previous in zip(inputs, old, strict=True):
        raw = json.loads(Path(source["events"]).read_bytes())
        teams = previous["team_ids"]
        roster.update(previous["player_ids"])
        source_pass = {p["event_id"]: p for p in previous["passes"]}
        eligible = {p["event_id"] for p in previous["passes"] if not p["exclusion_reasons"]}
        chain = {c["pass_event_ids"][1]: c for c in previous["chains"]}
        annotations = defaultdict(list)
        for e in raw:
            for p in (e.get("tactics") or {}).get("lineup", []):
                annotations[p["player"]["id"]].append(
                    dict(event_id=e["id"], index=e["index"], position=p.get("position"))
                )
            if e["type"]["name"] != "Pass":
                continue
            reasons = []
            if not 1 <= e["period"] <= 4:
                reasons.append("unsupported_period")
            actor = e.get("player", {}).get("id")
            if actor is None:
                reasons.append("missing_actor")
            if reasons:
                exclusions.append(
                    dict(match_id=source["match_id"], event_id=e["id"], reasons=reasons)
                )
                continue
            rid = f"{source['match_id']}:{e['id']}"
            expected_ids.add(rid)
            r = observed[rid]
            assert r["event_id"] == e["id"] and r["player_id"] == actor
            assert r["team_id"] == e["team"]["id"]
            assert r["match_id"] == source["match_id"] and r["provider_index"] == e["index"]
            assert r["period"] == e["period"] and r["timestamp"] == e["timestamp"]
            assert r["chain_id"] == (chain[e["id"]]["chain_id"] if e["id"] in chain else None)
            assert r["outcome_key_present"] == ("outcome" in e.get("pass", {}))
            assert r["opponent_id"] == next(t for t in teams if t != e["team"]["id"])
            assert r["native_start"] == e.get("location")
            point = e.get("location")
            expected_cell = (
                None
                if point is None
                else (
                    f"{sum(point[0] >= x for x in (20, 40, 60, 80, 100))}:"
                    f"{sum(point[1] >= y for y in (20, 40, 60))}"
                )
            )
            assert r["native_cell"] == expected_cell
            assert r["score_state"] == source_pass[e["id"]]["score_state"]
            assert r["prior_goal_event_ids"] == source_pass[e["id"]]["prior_goal_event_ids"]
            assert r["position_annotation"] == (
                annotations[actor][-1] if annotations[actor] else None
            )
            position = annotations[actor][-1]["position"] if annotations[actor] else None
            assert r["position_id"] == (position["id"] if position else None)
            assert r["memberships"] == dict(
                pass_attempt=True,
                verified_completed=e["id"] in eligible,
                chain_release=e["id"] in chain,
            )
            assert r["unknown_outcome"] == (
                "outcome" in e.get("pass", {}) and e["pass"]["outcome"] is None
            )
            assert r["source_manifest_sha256"] == source["source_manifest_sha256"]
    assert expected_ids == observed.keys()
    summary = json.loads((folder / "summary.json").read_bytes())
    assert summary["source_exclusions"] == exclusions
    assert summary["source_events_read"] == proof["original_events"]
    for population, data in summary["populations"].items():
        selected = [r for r in records if r["memberships"][population]]
        assert data["observations"] == len(selected)
        assert data["players"] == len({r["player_id"] for r in selected})
        assert data["roster_without_observations"] == sorted(
            roster - {r["player_id"] for r in selected}
        )
        assert data["missing_position"] == sum(r["position_id"] is None for r in selected)
        for design, result in data["designs"].items():
            grouping = defaultdict(list)
            dropped = []
            for r in selected:
                value = key(r, design)
                if value is None:
                    dropped.append(r["record_id"])
                    continue
                grouping[
                    f"p:{r['player_id']}", "c:" + json.dumps(value, separators=(",", ":"))
                ].append(r)
            edges = set(grouping)
            groups, rank = connected(edges)
            assert result["components"] == groups
            assert result["exact_rank"] == rank and result["nullity"] == len(groups)
            assert result["vertices"] == rank + len(groups)
            assert result["unique_edges"] == len(edges) and result["dropped_record_ids"] == dropped
            assert result["observations"] == sum(len(v) for v in grouping.values())
            expected_edges = {
                (a, b): [r["record_id"] for r in rs] for (a, b), rs in grouping.items()
            }
            assert {
                (e["player"], e["context"]): e["record_ids"] for e in result["edge_evidence"]
            } == expected_edges
            counts = [sum(n.startswith("p:") for n in g) for g in groups]
            within = sum(n * (n - 1) // 2 for n in counts)
            players = sum(counts)
            assert result["within_component_player_contrasts"] == within
            assert (
                result["across_component_player_contrasts"] == players * (players - 1) // 2 - within
            )
            direct = defaultdict(
                lambda: dict(n=0, matches=set(), supported=0, supported_matches=set())
            )
            contexts = defaultdict(list)
            for (player, c), rs in grouping.items():
                contexts[c].append((player, rs))
            for members in contexts.values():
                for (a, aa), (b, bb) in combinations(members, 2):
                    pair = tuple(sorted((a, b)))
                    g = direct[pair]
                    g["n"] += 1
                    ca = Counter(r["match_id"] for r in aa)
                    cb = Counter(r["match_id"] for r in bb)
                    g["matches"].update(set(ca) & set(cb))
                    if len(aa) >= 5 and len(bb) >= 5:
                        g["supported"] += 1
                        g["supported_matches"].update(
                            m for m in set(ca) & set(cb) if ca[m] >= 5 and cb[m] >= 5
                        )
            assert len(result["direct_pairs"]) == len(direct)
            for p in result["direct_pairs"]:
                g = direct[tuple(p["players"])]
                assert p["shared_contexts"] == g["n"] and p["shared_match_ids"] == sorted(
                    g["matches"]
                )
                assert p["supported_contexts"] == g["supported"]
                assert p["supported_match_ids"] == sorted(g["supported_matches"])
            assert result["pairs_with_at_least5_in_two_matches"] == sum(
                len(g["supported_matches"]) >= 2 for g in direct.values()
            )
        original = data["designs"]["team_match"]["within_component_player_contrasts"]
        for deletion in data["leave_match_out"]:
            kept = [r for r in selected if r["match_id"] != deletion["excluded_match_id"]]
            edges = {(f"p:{r['player_id']}", f"c:{r['team_id']}:{r['match_id']}") for r in kept}
            groups, _ = connected(edges)
            sizes = [sum(n.startswith("p:") for n in g) for g in groups]
            assert deletion["originally_supported_contrasts_lost"] == original - sum(
                n * (n - 1) // 2 for n in sizes
            )
            assert deletion["missing_player_ids"] == sorted(
                {r["player_id"] for r in selected} - {r["player_id"] for r in kept}
            )
    return dict(
        status="PASS",
        original_events=proof["original_events"],
        actor_pass_records=len(records),
        designs_checked=sum(len(v["designs"]) for v in summary["populations"].values()),
        manifest_sha256=sha(folder / "manifest.json"),
        verifier_sha256=sha(__file__),
    )


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1])), indent=2, sort_keys=True))
