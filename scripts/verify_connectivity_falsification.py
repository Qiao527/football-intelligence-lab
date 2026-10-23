"""Independent falsification checks from immutable raw JSON; no production metric imports."""

import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from verify_connectivity import verify as verify_parent

GRIDS = {
    "6x4": (6, 4, 0),
    "3x2": (3, 2, 0),
    "shift5": (6, 4, 5),
    "shift10": (6, 4, 10),
    "shift_minus5": (6, 4, -5),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def point(value):
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(
            type(x) in (int, float) and math.isfinite(x) and 0 <= x <= bound
            for x, bound in zip(value, (120, 80), strict=True)
        )
    )


def cell(value, spec=(6, 4, 0)):
    if not point(value):
        return None
    nx, ny, offset = spec
    return tuple(
        sum(x >= k * bound / count + offset for k in range(1, count))
        for x, bound, count in zip(value, (120, 80), (nx, ny), strict=True)
    )


def checks(bundle: Path) -> dict:
    manifest = json.loads((bundle / "manifest.json").read_bytes())
    for path, expected in manifest["protected_inputs"].items():
        assert sha(path) == expected
    for name, expected in manifest["files"].items():
        assert sha(bundle / name) == expected
    parent = Path(manifest["parent_bundle"])
    assert sha(parent / "manifest.json") == manifest["parent_manifest_sha256"]
    parent_proof = verify_parent(parent)
    sources = json.loads((parent / "source-inputs.json").read_bytes())
    parents = json.loads((parent / "evidence.json").read_bytes())
    audits = json.loads((bundle / "evidence.json").read_bytes())
    count = 0
    for source, old, audit in zip(sources, parents, audits, strict=True):
        assert audit["match_id"] == old["match_id"] == source["match_id"]
        raw = json.loads(Path(source["events"]).read_bytes())
        source_passes = {p["event_id"]: p for p in old["passes"]}
        groups = defaultdict(list)
        for i, e in enumerate(raw):
            if e.get("possession") is not None:
                groups[e["possession"]].append(i)
        candidates = {}
        rows = {r["chain_id"]: r for r in audit["rows"]}
        reported = {r["chain_id"]: r for r in audit["candidates"]}
        assert len(rows) == len(audit["rows"]) and len(reported) == len(audit["candidates"])
        for indices in groups.values():
            members = [raw[i] for i in indices]
            periods = {e["period"] for e in members}
            owners = {e.get("possession_team", {}).get("id") for e in members}
            if (
                len(periods) != 1
                or not periods <= {1, 2, 3, 4}
                or len(owners) != 1
                or not owners <= set(old["team_ids"])
                or indices[-1] - indices[0] + 1 != len(indices)
            ):
                continue
            owner = next(iter(owners))
            passes = [
                i
                for i in indices
                if raw[i]["team"]["id"] == owner
                and raw[i]["type"]["name"] == "Pass"
                and "outcome" not in raw[i].get("pass", {})
                and raw[i].get("player", {}).get("id") is not None
                and raw[i]["pass"].get("recipient", {}).get("id") is not None
                and raw[i]["player"]["id"] != raw[i]["pass"]["recipient"]["id"]
            ]
            for j in range(1, len(passes)):
                ia, ib = passes[j - 1], passes[j]
                a, b = raw[ia], raw[ib]
                key = a["id"] + "/" + b["id"]
                between = raw[ia + 1 : ib]
                linked = a["pass"]["recipient"]["id"] == b["player"]["id"]
                good, relaxed = True, True
                receipts = []
                invalid = []
                for e in between:
                    same = (
                        e["team"]["id"] == owner
                        and e.get("player", {}).get("id") == b["player"]["id"]
                    )
                    kind = e["type"]["name"]
                    receipt = (
                        same
                        and kind == "Ball Receipt*"
                        and "outcome" not in e.get("ball_receipt", {})
                    )
                    if receipt:
                        receipts.append(e)
                    admissible = same and (kind == "Carry" or receipt)
                    if not admissible:
                        invalid.append(e["id"])
                        good = False
                        d = e.get("dribble")
                        complete = (
                            isinstance(d, dict)
                            and isinstance(d.get("outcome"), dict)
                            and d["outcome"].get("name") == "Complete"
                        )
                        if not (same and kind == "Dribble" and complete):
                            relaxed = False
                expected = dict(
                    original=linked and good,
                    receipt_required=linked and good and len(receipts) == 1,
                    no_carry=linked and good and all(e["type"]["name"] != "Carry" for e in between),
                    no_intervening=linked and not between,
                    permit_complete_dribble=linked and relaxed,
                )
                c = reported[key]
                assert c["eligibility"] == expected
                assert c["nonpermitted_original_event_ids"] == invalid
                assert c["intervening_event_ids"] == [e["id"] for e in between]
                candidates[key] = expected
                if not expected["permit_complete_dribble"]:
                    assert key not in rows
                    continue
                r = rows[key]
                points = [
                    a.get("location"),
                    a["pass"].get("end_location"),
                    b.get("location"),
                    b["pass"].get("end_location"),
                ]
                assert r["points"] == points and r["eligibility"] == expected
                nonreturn = a["player"]["id"] != b["pass"]["recipient"]["id"]
                assert r["nonreturn"] == nonreturn
                assert r["pass_event_ids"] == [a["id"], b["id"]]
                assert r["player_ids"] == [
                    a["player"]["id"],
                    b["player"]["id"],
                    b["pass"]["recipient"]["id"],
                ]
                assert r["source_manifest_sha256"] == source["source_manifest_sha256"]
                assert r["prior_goal_event_ids"] == source_passes[a["id"]]["prior_goal_event_ids"]
                assert r["score_state"] == source_passes[a["id"]]["score_state"]
                for name, start, end in (
                    ("original", 0, 3),
                    ("incoming", 0, 1),
                    ("b_relocation_proxy", 1, 2),
                    ("b_outgoing", 2, 3),
                ):
                    for grid, spec in GRIDS.items():
                        ca, cb = cell(points[start], spec), cell(points[end], spec)
                        assert r["outcomes"][name][grid] == (
                            None if ca is None or cb is None else nonreturn and ca != cb
                        )
                    d = (
                        sum((x - y) ** 2 for x, y in zip(points[start], points[end], strict=True))
                        ** 0.5
                        if point(points[start]) and point(points[end])
                        else None
                    )
                    assert (
                        r["separation"][name] is None
                        if d is None
                        else math.isclose(r["separation"][name], d, abs_tol=1e-12)
                    )
                rp = receipts[0].get("location") if len(receipts) == 1 else None
                assert r["receipt_event_ids"] == [e["id"] for e in receipts]
                assert r["receipt_point"] == rp
                ca, cb = cell(rp), cell(points[2])
                assert r["b_observed_receipt_release"] == (
                    None if ca is None or cb is None else nonreturn and ca != cb
                )
                annotations = [
                    dict(event_id=e["id"], index=e["index"], position=p.get("position"))
                    for e in raw[: ia + 1]
                    for p in (e.get("tactics") or {}).get("lineup", [])
                    if p["player"]["id"] == b["player"]["id"]
                ]
                assert r["position_annotation"] == (annotations[-1] if annotations else None)
                expected_position = annotations[-1].get("position") if annotations else None
                assert r["position_annotation_id"] == (
                    expected_position["id"] if expected_position else None
                )
                count += 1
        assert candidates.keys() == reported.keys()
        assert {k for k, v in candidates.items() if v["original"]} == {
            c["chain_id"] for c in old["chains"]
        }
        assert rows.keys() == {k for k, v in candidates.items() if v["permit_complete_dribble"]}
    summary = json.loads((bundle / "summary.json").read_bytes())
    primary = [r for a in audits for r in a["rows"] if r["eligibility"]["original"]]
    known = [r for r in primary if r["outcomes"]["original"]["6x4"] is not None]
    n = len(known)
    k = sum(r["outcomes"]["original"]["6x4"] for r in known)
    assert math.isclose(summary["unstratified_sse"], float(Fraction(k * (n - k), n)))
    for name, groups in summary["partitions"].items():
        members = [i for g in groups.values() for i in g["chain_ids"]]
        assert Counter(members) == Counter(r["chain_id"] for r in known)
        sse = Fraction()
        lookup = {r["chain_id"]: r for r in primary}
        for group_key, g in groups.items():
            linked = [lookup[c] for c in g["chain_ids"]]
            for r in linked:
                tm = [r["match_id"], r["team_id"]]
                context = tm + [r["period"], r["score_state"]]
                start, end = cell(r["points"][0]), cell(r["points"][3])
                keys = dict(
                    team_match=tm,
                    team_period_score=context,
                    start_zone=[start],
                    endpoint_pair=[start, end],
                    endpoint_pair_nonreturn=[start, end, r["nonreturn"]],
                    team_possession=tm + [r["possession_id"]],
                    team_period_score_start=context + [start],
                    team_period_score_start_position=context + [start, r["position_annotation_id"]],
                )
                assert group_key == json.dumps(keys[name], separators=(",", ":"))
            nn = len(linked)
            kk = sum(r["outcomes"]["original"]["6x4"] for r in linked)
            assert (g["n"], g["k"]) == (nn, kk)
            assert {str(r["player_id"]) for r in linked} == g["players"].keys()
            for player, p in g["players"].items():
                sub = [r for r in linked if str(r["player_id"]) == player]
                assert p == dict(n=len(sub), k=sum(r["outcomes"]["original"]["6x4"] for r in sub))
            sse += Fraction(kk * (nn - kk), nn)
        assert math.isclose(
            summary["partition_summary"][name]["within_stratum_sse"], float(sse), abs_tol=1e-12
        )
    lookup = defaultdict(list)
    for r in primary:
        lookup[r["match_id"], r["player_id"]].append(r)
    for d in summary["decomposition"]:
        sub = [
            r
            for r in lookup[d["match_id"], d["player_id"]]
            if r["outcomes"]["original"]["6x4"] is not None
        ]
        nn = len(sub)
        mm = sum(r["nonreturn"] for r in sub)
        kk = sum(r["outcomes"]["original"]["6x4"] for r in sub)
        assert (d["N"], d["M"], d["K"]) == (nn, mm, kk)
        assert d["conditional_fraction"] == (kk / nn if nn else None)
        assert d["nonreturn_fraction"] == (mm / nn if nn else None)
        assert d["cross_fraction_among_nonreturns"] == (kk / mm if mm else None)
        if nn and mm:
            assert math.isclose(
                nn * d["nonreturn_fraction"] * d["cross_fraction_among_nonreturns"], kk
            )
    for name in GRIDS:
        assert summary["grids"][name]["cross_zone"] == sum(
            r["outcomes"]["original"][name] is True for r in primary
        )
    assert summary["coarsening"]["mechanical_reclassifications"] == (
        summary["grids"]["6x4"]["cross_zone"] - summary["grids"]["3x2"]["cross_zone"]
    )
    assert summary["partition_summary"]["endpoint_pair_nonreturn"]["within_stratum_sse"] == 0
    for name, v in summary["variants"].items():
        selected = [r for a in audits for r in a["rows"] if r["eligibility"][name]]
        assert v["chain_ids"] == [r["chain_id"] for r in selected]
        assert v["eligible"] == len(selected)
        assert v["cross_zone"] == sum(r["outcomes"]["original"]["6x4"] is True for r in selected)
    # Independent summary arithmetic after source-by-source reconciliation.
    for name, groups in summary["partitions"].items():
        multi = [g for g in groups.values() if len(g["players"]) >= 2]
        strong = [
            g for g in groups.values() if sum(v["n"] >= 5 for v in g["players"].values()) >= 2
        ]
        row = summary["partition_summary"][name]
        assert row["strata"] == len(groups)
        assert row["opportunities_in_multi_player_strata"] == sum(g["n"] for g in multi)
        assert row["strata_with_two_players_at_least5"] == len(strong)
        assert row["opportunities_in_supported_strata"] == sum(g["n"] for g in strong)
        assert row["player_opportunities_at_least5_in_supported_strata"] == sum(
            v["n"] for g in strong for v in g["players"].values() if v["n"] >= 5
        )
        assert math.isclose(
            row["fraction_of_unstratified_sse"],
            row["within_stratum_sse"] / summary["unstratified_sse"],
            abs_tol=1e-12,
        )
    original_players = {(m["match_id"], p["player_id"]): p for m in parents for p in m["players"]}
    assert len(summary["decomposition"]) == len(original_players)
    assert {
        (d["match_id"], d["player_id"]) for d in summary["decomposition"]
    } == original_players.keys()
    for d in summary["decomposition"]:
        p = original_players[d["match_id"], d["player_id"]]
        for field in (
            "completed_passes",
            "received_passes",
            "in_degree",
            "out_degree",
            "possession_participation",
            "team_completed_pass_opportunities",
            "team_eligible_possessions",
        ):
            assert d[field] == p[field]
    active = [d for d in summary["decomposition"] if d["actor_records"] or d["received_passes"]]
    fraction = [d for d in active if d["conditional_fraction"] is not None]
    assert summary["correlation_support"] == dict(
        count_rows=len(active), fraction_rows=len(fraction)
    )
    for feature, result in summary["redundancy"].items():
        for field, sample, outcome in (
            ("count_correlation", active, "K"),
            ("fraction_correlation", fraction, "conditional_fraction"),
        ):
            x = [d[feature] for d in sample]
            y = [d[outcome] for d in sample]
            mx, my = sum(x) / len(x), sum(y) / len(y)
            denominator = math.sqrt(sum((v - mx) ** 2 for v in x) * sum((v - my) ** 2 for v in y))
            value = (
                sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / denominator
                if denominator
                else None
            )
            assert (
                result[field] is None
                if value is None
                else math.isclose(result[field], value, abs_tol=1e-12)
            )
    for definition, tab in summary["definition_cross_tabs"].items():
        counts = Counter()
        for r in primary:
            a = r["outcomes"]["original"]["6x4"]
            b = (
                r["b_observed_receipt_release"]
                if definition == "observed_receipt"
                else r["outcomes"][definition]["6x4"]
            )
            counts["unknown" if a is None or b is None else f"{int(a)}:{int(b)}"] += 1
        assert dict(counts) == tab
    for name in GRIDS:
        assert summary["grids"][name]["disagreement_with_primary"] == sum(
            r["outcomes"]["original"][name] != r["outcomes"]["original"]["6x4"] for r in primary
        )
        assert summary["grids"][name]["missing"] == sum(
            r["outcomes"]["original"][name] is None for r in primary
        )
    for threshold in (20, 40):
        assert summary["continuous_thresholds"][str(threshold)] == sum(
            r["nonreturn"]
            and r["separation"]["original"] is not None
            and r["separation"]["original"] >= threshold
            for r in primary
        )
    for name, result in summary["continuous"].items():
        values = sorted(r["separation"][name] for r in primary if r["separation"][name] is not None)
        assert result["known"] == len(values) and result["missing"] == len(primary) - len(values)
        for field, probability in (
            ("min", 0),
            ("q25", 0.25),
            ("median", 0.5),
            ("q75", 0.75),
            ("max", 1),
        ):
            index = Fraction(len(values) - 1) * Fraction(probability)
            left = index.numerator // index.denominator
            value = values[left] + float(index - left) * (
                values[min(left + 1, len(values) - 1)] - values[left]
            )
            assert math.isclose(result[field], value, abs_tol=1e-12)
    return dict(
        status="PASS",
        matches=len(audits),
        raw_events=parent_proof["original_events"],
        primary_chains=len(primary),
        all_admitted_variant_chains=count,
        parent_manifest_sha256=sha(parent / "manifest.json"),
        bundle_manifest_sha256=sha(bundle / "manifest.json"),
        verifier_sha256=sha(__file__),
    )


if __name__ == "__main__":
    print(json.dumps(checks(Path(sys.argv[1])), indent=2, sort_keys=True))
