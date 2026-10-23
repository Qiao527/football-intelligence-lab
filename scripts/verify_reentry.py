"""Independent raw-record/landmark verification. No production re-entry imports."""

import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from verify_comparison_design import verify as verify_parent


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def point(p):
    return (
        isinstance(p, list)
        and len(p) == 2
        and all(type(v) in (float, int) and math.isfinite(v) for v in p)
        and 0 <= p[0] <= 120
        and 0 <= p[1] <= 80
    )


def move(e):
    name = e["type"]["name"]
    data = e.get(name.lower())
    if name not in ("Carry", "Pass") or not isinstance(data, dict):
        return None
    if name == "Pass" and "outcome" in data:
        return None
    a, b = e.get("location"), data.get("end_location")
    return (a, b) if point(a) and point(b) else None


def reference(raw, source, boundary, drop, pass_only):
    positions = defaultdict(list)
    for i, e in enumerate(raw):
        if e.get("possession") is not None:
            positions[e["possession"]].append(i)
    teams = {source["metadata"][k][k + "_id"] for k in ("home_team", "away_team")}
    scores, used, score_before = dict.fromkeys(teams, 0), set(), {}
    goals = []
    for e in raw:
        score_before[e["id"]] = dict(scores)
        kind = e["type"]["name"]
        if e["period"] == 5 or e["id"] in used:
            continue
        if kind == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            scores[e["team"]["id"]] += 1
            goals.append((e["index"], [e["id"]]))
        elif kind in ("Own Goal For", "Own Goal Against"):
            linked = [
                x
                for x in raw
                if x["id"] in e.get("related_events", [])
                and x["type"]["name"] in ("Own Goal For", "Own Goal Against")
            ]
            ids = [e["id"]] + [x["id"] for x in linked]
            used.update(ids)
            beneficiary = (
                e["team"]["id"]
                if kind == "Own Goal For"
                else next(t for t in teams if t != e["team"]["id"])
            )
            scores[beneficiary] += 1
            goals.append((e["index"], ids))
    assert [scores[source["metadata"][k][k + "_id"]] for k in ("home_team", "away_team")] == [
        source["metadata"][k + "_score"] for k in ("home", "away")
    ]
    expected = {}
    for pid, ix in positions.items():
        es = [raw[i] for i in ix]
        owner, period = es[0].get("possession_team", {}).get("id"), es[0]["period"]
        reasons = set()
        if {e["period"] for e in es} != {period} or period not in range(1, 5):
            reasons.add("unsupported_or_cross_period")
        if {e.get("possession_team", {}).get("id") for e in es} != {owner} or owner not in teams:
            reasons.add("ambiguous_owner")
        if len(ix) != ix[-1] - ix[0] + 1:
            reasons.add("noncontiguous_or_unassigned")
        r = dict(
            reasons=reasons,
            source_event_ids=[e["id"] for e in es],
            feature=None,
            outcome=None,
            full_segment_outcome=None,
        )
        expected[pid] = r
        if reasons:
            continue
        own = [e for e in es if e["team"]["id"] == owner]
        kinds = {"Pass"} if pass_only else {"Pass", "Carry"}
        steps = [e for e in own if e["type"]["name"] in kinds]
        crosses = [
            j
            for j, e in enumerate(steps)
            if move(e) and move(e)[0][0] < boundary and move(e)[1][0] >= boundary
        ]
        if not crosses:
            reasons.add("no_observed_entry")
            continue
        j = crosses[0]
        entry = steps[j]
        r.update(entry_event_id=entry["id"], entry_provider_index=entry["index"])
        if not all(move(e) for e in steps[:j]):
            reasons.add("first_entry_ambiguous_after_failed_or_unknown_move")
        if (entry.get("play_pattern") or {}).get("name") not in {"Regular Play", "From Counter"}:
            reasons.add("nonqualifying_native_play_pattern")
        ws = steps[j + 1 : j + 4]
        r["landmark_window_ids"] = [e["id"] for e in ws]
        if len(ws) != 3:
            reasons.add("short_before_landmark")
        if not all(move(e) for e in ws):
            reasons.add("failed_or_unknown_landmark_geometry")
        if ws and any(
            e["type"]["name"] == "Shot" and entry["index"] < e["index"] <= ws[-1]["index"]
            for e in own
        ):
            reasons.add("shot_before_landmark")
        if reasons:
            continue
        last = ws[2]
        retreats = [e for e in ws if move(e)[0][0] >= boundary and move(e)[1][0] <= boundary - drop]
        returns = [e for e in ws if move(e)[0][0] < boundary <= move(e)[1][0]]
        witnesses = [
            [a["id"], b["id"]] for a in retreats for b in returns if a["index"] < b["index"]
        ]
        future = [
            e
            for e in own
            if e["index"] > last["index"] and e["type"]["name"] in {"Pass", "Carry", "Shot"}
        ][:3]
        shots = [e for e in future if e["type"]["name"] == "Shot"]
        all_shots = [e for e in own if e["index"] > last["index"] and e["type"]["name"] == "Shot"]
        ends = [e for e in raw if e["period"] == period and e["type"]["name"] == "Half End"]
        closure = []
        incomplete = any(
            (e.get("half_end") or {}).get(key)
            for e in ends
            for key in ("early_video_end", "match_suspended")
        )
        after = raw[ix[-1] + 1] if ix[-1] + 1 < len(raw) else None
        if (
            not incomplete
            and after
            and after["period"] == period
            and after.get("possession") is not None
        ):
            closure = [after["id"]]
        elif not incomplete and len(ends) == 2:
            nonmarkers = [
                e for e in es if e["type"]["name"] not in {"Half Start", "Half End", "Starting XI"}
            ]
            if (
                len({e["team"]["id"] for e in ends}) == 2
                and all(a["id"] in b.get("related_events", []) for a, b in (ends, ends[::-1]))
                and nonmarkers
                and all(e["index"] > nonmarkers[-1]["index"] for e in ends)
                and all(
                    e.get("possession") == pid or e["type"]["name"] == "Half End"
                    for e in raw
                    if nonmarkers[-1]["index"] < e["index"] <= ends[-1]["index"]
                )
            ):
                closure = [e["id"] for e in ends]
        prefix = sum(
            e["type"]["name"] == "Pass" and bool(move(e))
            for e in own
            if e["index"] <= last["index"]
        )
        end = move(last)[1]
        s = score_before[last["id"]]
        difference = s[owner] - s[next(t for t in teams if t != owner)]
        r.update(
            feature=bool(witnesses),
            cooccurrence=bool(retreats and returns),
            landmark_event_id=last["id"],
            landmark_provider_index=last["index"],
            landmark_endpoint=end,
            landmark_cell=[min(int(end[0] // 40), 2), min(int(end[1] // 40), 1)],
            score_state="level" if difference == 0 else "leading" if difference > 0 else "trailing",
            prior_goal_event_ids=[eid for i, ids in goals if i < last["index"] for eid in ids],
            retreat_ids=[e["id"] for e in retreats],
            reentry_ids=[e["id"] for e in returns],
            ordered_witnesses=witnesses,
            future_horizon_ids=[e["id"] for e in future],
            shot_event_ids=[e["id"] for e in shots],
            all_later_shot_ids=[e["id"] for e in all_shots],
            closure_ids=closure,
            prefix_passes=prefix,
            pass_volume_bin="0-2" if prefix < 3 else "3-5" if prefix < 6 else "6+",
            window_passes=sum(e["type"]["name"] == "Pass" for e in ws),
            source_play_pattern=entry["play_pattern"]["name"],
            outcome=1 if shots else 0 if len(future) >= 3 or closure else None,
            full_segment_outcome=1 if all_shots else 0 if closure else None,
            source_known_horizon_xg_sum=math.fsum(
                e["shot"]["statsbomb_xg"]
                for e in shots
                if e["shot"].get("statsbomb_xg") is not None
            ),
            missing_horizon_xg_ids=[
                e["id"] for e in shots if e["shot"].get("statsbomb_xg") is None
            ],
        )
    return expected


def verify_summary(rows, s):
    eligible = [r for r in rows if r["feature"] is not None]
    assert s["memberships"] == len(rows) and s["eligible"] == len(eligible)
    assert s["exclusions"] == dict(Counter(q for r in rows for q in r["exclusion_reasons"]))
    for flag, key in ((True, "motif"), (False, "nonmotif")):
        arm = [r for r in eligible if r["feature"] == flag]
        c = Counter(r["outcome"] for r in arm)
        assert s[key]["n"] == len(arm)
        assert [s[key][x] for x in ("positive", "negative", "unresolved")] == [c[1], c[0], c[None]]
        assert s[key]["observed_rate"] == (
            c[1] / (len(arm) - c[None]) if len(arm) > c[None] else None
        )
        assert s[key]["prevalence_bounds"] == (
            [c[1] / len(arm), (c[1] + c[None]) / len(arm)] if arm else None
        )
    for context, field in ((False, "volume_location"), (True, "team_match_context")):
        groups = defaultdict(lambda: [[], []])
        for r in eligible:
            key = (r["pass_volume_bin"], *r["landmark_cell"], r["window_passes"])
            if context:
                key += (r["team_id"], r["match_id"], r["period"], r["score_state"])
            groups[key][int(r["feature"])].append(r)
        actual = {tuple(g["stratum"]): g for g in s[field]["shared_strata"]}
        shared = {k: arms for k, arms in groups.items() if all(arms)}
        assert set(actual) == set(shared)
        effects, denominator, lower, upper = [], 0, 0, 0
        for k, arms in shared.items():
            g = actual[k]
            weight = min(map(len, arms))
            assert g["weight"] == weight
            rates, bounds = [], []
            for records, key in zip(arms, ("nonmotif", "motif"), strict=True):
                p = sum(r["outcome"] == 1 for r in records)
                u = sum(r["outcome"] is None for r in records)
                assert g[key]["n"] == len(records) and g[key]["positive"] == p
                assert g[key]["unresolved"] == u
                bounds.append([p / len(records), (p + u) / len(records)])
                rates.append(p / (len(records) - u) if len(records) > u else None)
            effect = rates[1] - rates[0] if all(r is not None for r in rates) else None
            assert g["effect"] == effect
            if effect is not None:
                effects.append((weight, effect))
            lo, hi = bounds[1][0] - bounds[0][1], bounds[1][1] - bounds[0][0]
            assert g["difference_bounds"] == [lo, hi]
            lower += weight * lo
            upper += weight * hi
            denominator += weight
        expected = sum(w * e for w, e in effects) / sum(w for w, _ in effects) if effects else None
        if expected is None:
            assert s[field]["observed_difference"] is None
        else:
            assert math.isclose(s[field]["observed_difference"], expected, abs_tol=1e-12)
        assert s[field]["matched_rows"] == sum(len(a) + len(b) for a, b in shared.values())
        assert s[field]["excluded_no_arm_overlap"] + s[field]["matched_rows"] == len(eligible)
        if denominator:
            assert all(
                math.isclose(x, y, abs_tol=1e-12)
                for x, y in zip(
                    s[field]["difference_bounds"],
                    [lower / denominator, upper / denominator],
                    strict=True,
                )
            )
    strata = defaultdict(list)
    for r in eligible:
        strata[
            (r["team_id"], r["match_id"], r["period"], r["score_state"], r["landmark_cell"][1])
        ].append(r)
    support = {k: v for k, v in strata.items() if len(v) >= 5}
    keys = {(tuple(p["left"]), tuple(p["right"])) for p in s["repeat_support"]["pairs"]}
    assert keys == {
        (a, b) for a, b in combinations(sorted(support), 2) if a[1] != b[1] and a[2:] == b[2:]
    }
    for p in s["repeat_support"]["pairs"]:
        a, b = support[tuple(p["left"])], support[tuple(p["right"])]
        x, y = sum(r["feature"] for r in a) / len(a), sum(r["feature"] for r in b) / len(b)
        assert p["left_n"] == len(a) and p["right_n"] == len(b)
        assert p["absolute_difference"] == abs(x - y)
    assert s["cooccurrence"] == sum(r["cooccurrence"] for r in eligible)
    assert s["cooccurrence_not_ordered"] == sum(
        r["cooccurrence"] and not r["feature"] for r in eligible
    )
    per = s["team_matches"]
    assert {(p["team_id"], p["match_id"]) for p in per} == {
        (r["team_id"], r["match_id"]) for r in eligible
    }
    effects = []
    s_global = s["team_match_context"]
    for p in per:
        subset = [
            r for r in eligible if (r["team_id"], r["match_id"]) == (p["team_id"], p["match_id"])
        ]
        assert p["n"] == len(subset) and p["motif"] == sum(r["feature"] for r in subset)
        expected_shared = [
            s
            for s in s_global["shared_strata"]
            if s["stratum"][4:6] == [p["team_id"], p["match_id"]]
        ]
        assert p["context"]["shared_strata"] == expected_shared
        valid = [(x["weight"], x["effect"]) for x in expected_shared if x["effect"] is not None]
        estimate = sum(w * e for w, e in valid) / sum(w for w, _ in valid) if valid else None
        assert p["context"]["observed_difference"] == estimate
        if p["context"]["observed_difference"] is not None:
            effects.append(p["context"]["observed_difference"])
    assert s["equal_supported_team_match_difference"] == (
        statistics.mean(effects) if effects else None
    )


def verify(root):
    m = json.loads((root / "manifest.json").read_bytes())
    assert (
        m["parent_manifest_sha256"]
        == "c02124906e317733e08bafc9fe52b8898bcf607659760054033461a88ce4cb99"
    )
    assert (
        m["protocol_sha256"]
        == sha("docs/research/REENTRY_PROTOCOL.md")
        == "873fec08c970d4bb2181018fe3a666a6638e0a5e51c11b9ce770567436980da1"
    )
    assert all(sha(root / f) == h for f, h in m["files"].items())
    assert all(sha(p) == h for p, h in m["protected_inputs"].items())
    parent = Path(m["parent_bundle"])
    assert sha(parent / "manifest.json") == m["parent_manifest_sha256"]
    parent_proof = verify_parent(parent)
    data = json.loads((root / "evidence.json").read_bytes())
    summary = json.loads((root / "summary.json").read_bytes())
    sources = json.loads((root / "source-inputs.json").read_bytes())
    variants = {
        "primary": (80, 5, False),
        "boundary75": (75, 5, False),
        "boundary85": (85, 5, False),
        "drop10": (80, 10, False),
        "pass_only": (80, 5, True),
    }
    for source in sources:
        raw = json.loads(Path(source["events"]).read_bytes())
        for variant, args in variants.items():
            expected = reference(raw, source, *args)
            actual = {
                r["possession_id"]: r for r in data[variant] if r["match_id"] == source["match_id"]
            }
            assert set(actual) == set(expected)
            for pid, r in expected.items():
                got = actual[pid]
                assert set(got["exclusion_reasons"]) == r.pop("reasons")
                assert all(got.get(k) == v for k, v in r.items()), (
                    source["match_id"],
                    pid,
                    variant,
                )
                assert got["source_manifest_sha256"] == source["source_manifest_sha256"]

    for variant in variants:
        verify_summary(data[variant], summary["variants"][variant])
        original = {(r["match_id"], r["possession_id"]): r for r in data["primary"]}
        paired = [
            (original[r["match_id"], r["possession_id"]], r)
            for r in data[variant]
            if r["feature"] is not None
            and original[r["match_id"], r["possession_id"]]["feature"] is not None
        ]
        assert summary["sensitivity"][variant] == dict(
            common_eligible=len(paired),
            feature_disagreements=sum(a["feature"] != b["feature"] for a, b in paired),
            landmark_disagreements=sum(
                a["landmark_event_id"] != b["landmark_event_id"] for a, b in paired
            ),
        )
    return dict(
        status="PASS",
        source_matches=len(sources),
        parent=parent_proof,
        variants_checked=len(variants),
        memberships_per_variant=len(data["primary"]),
        verifier_sha256=sha(__file__),
        manifest_sha256=sha(root / "manifest.json"),
        independent_human_judgments=0,
        independent_football_replication=False,
    )


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1])), indent=2, sort_keys=True))
