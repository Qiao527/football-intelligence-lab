"""Independent original-JSON audit of the local pilot corpus and real predictions.

CONFIG PILOT_REPORT_LIST CORPUS_DIR. Expected scores, exposure and forecasting
labels/features are recomputed without production clock/score/census/model code.
"""

import hashlib
import json
import math
import sys
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from verify_process_source import OWNER_TYPES, successful_move


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def elapsed(e):
    h, m, s = e["timestamp"].split(":")
    return round((int(h) * 3600 + int(m) * 60 + float(s)) * 1000)


def independent_exposure(raw, roster):
    active = {t: set() for t, p in roster}
    seconds = defaultdict(float)
    for e in raw:
        if e["type"]["name"] == "Starting XI":
            active[e["team"]["id"]] = {p["player"]["id"] for p in e["tactics"]["lineup"]}
    for period in sorted({e["period"] for e in raw} - {5}):
        prior = 0
        for e in [e for e in raw if e["period"] == period]:
            now = elapsed(e)
            for t, players in active.items():
                for p in players:
                    seconds[t, p] += (now - prior) / 1000
            prior = now
            t = e["team"]["id"]
            p = e.get("player", {}).get("id")
            kind = e["type"]["name"]
            if kind == "Substitution":
                active[t].remove(p)
                active[t].add(e["substitution"]["replacement"]["id"])
            if kind == "Player Off":
                active[t].remove(p)
            if kind == "Player On":
                active[t].add(p)
            card = (
                (e.get("foul_committed") or e.get("bad_behaviour") or {})
                .get("card", {})
                .get("name")
            )
            if card in {"Red Card", "Second Yellow"}:
                active[t].discard(p)
    return seconds


def main():
    c = json.loads(Path(sys.argv[1]).read_bytes())
    folders = [Path(p) for p in json.loads(Path(sys.argv[2]).read_bytes())]
    root = Path(sys.argv[3])
    manifest = json.loads((root / "manifest.json").read_bytes())
    for name, h in manifest["files"].items():
        assert sha(root / name) == h
    canonical = pq.ParquetFile(root / "canonical_all_matches.parquet").read().to_pylist()
    validated = pq.ParquetFile(root / "validated_score_events.parquet").read().to_pylist()
    raw_root = Path("data/raw/statsbomb-corpus") / manifest["source_revision"]
    original = Path(c["raw"])
    originals = {8658: json.loads((original / "data/events/8658.json").read_bytes())}
    matches = json.loads((original / "data/matches/43/3.json").read_bytes())
    metadata = {m["match_id"]: m for m in matches}
    reports = {
        json.loads((p / "quality.json").read_bytes())["match_id"]: json.loads(
            (p / "quality.json").read_bytes()
        )
        for p in folders
    }
    for mid in reports:
        originals[mid] = json.loads((raw_root / str(mid) / f"{mid}.json.events").read_bytes())
        src = json.loads((raw_root / str(mid) / "manifest.json").read_bytes())
        for path, item in src["files"].items():
            body = (raw_root / str(mid) / (f"{mid}.json." + path.split("/")[1])).read_bytes()
            assert hashlib.sha256(body).hexdigest() == item["sha256"]
            git = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            assert git == item["upstream_git_blob_sha1"]
    assert len(canonical) == sum(map(len, originals.values())) == 24805
    for mid, raw in originals.items():
        projected = [r for r in canonical if r["match_id"] == mid]
        assert [json.loads(r["source_record_json"]) for r in projected] == raw
        assert [r["event_id"] for r in projected] == [e["id"] for e in raw]
        for r, e in zip(projected, raw, strict=True):
            assert (r["provider_index"], r["period"], r["period_timestamp"]) == (
                e["index"],
                e["period"],
                e["timestamp"],
            )
            assert (r["team_id"], r["player_id"], r["possession_id"], r["possession_team_id"]) == (
                e["team"]["id"],
                e.get("player", {}).get("id"),
                e.get("possession"),
                e.get("possession_team", {}).get("id"),
            )
            point = e.get("location") or [None, None]
            assert [r["x"], r["y"]] == point[:2]
            assert r["z"] == (point[2] if len(point) > 2 else None)
            kind = e["type"]["name"]
            detail = e.get(
                {
                    "Pass": "pass",
                    "Carry": "carry",
                    "Shot": "shot",
                    "Goal Keeper": "goalkeeper",
                    "Dribble": "dribble",
                    "Duel": "duel",
                    "Interception": "interception",
                    "Ball Receipt*": "ball_receipt",
                    "50/50": "50_50",
                }.get(kind, "TEST_NON_ACTION"),
                {},
            )
            end = (detail or {}).get("end_location") or [None, None]
            assert [r["end_x"], r["end_y"]] == end[:2]
            assert r["end_z"] == (end[2] if len(end) > 2 else None)
            assert r["shot_xg"] == (e["shot"].get("statsbomb_xg") if kind == "Shot" else None)
    all_expected = {}
    boundary_failures = {}
    blocked_raw_scores = {}
    checks = []
    for mid, q in reports.items():
        raw = originals[mid]
        meta = metadata[mid]
        teams = [meta[k][k + "_id"] for k in ("home_team", "away_team")]
        lineup = json.loads((raw_root / str(mid) / f"{mid}.json.lineups").read_bytes())
        roster = {(t["team_id"], p["player_id"]) for t in lineup for p in t["lineup"]}
        assert set(teams) == {t["team_id"] for t in lineup}
        assert len(roster) == len(q["roster"])
        assert not [
            e for e in raw if e.get("player") and (e["team"]["id"], e["player"]["id"]) not in roster
        ]
        conflicts = {
            p: sorted(
                {
                    e["timestamp"]
                    for e in raw
                    if e["period"] == p and e["type"]["name"] == "Half End"
                }
            )
            for p in {e["period"] for e in raw} - {5}
        }
        conflicts = {p: v for p, v in conflicts.items() if len(v) != 1}
        if conflicts:
            raw_goals = dict.fromkeys(teams, 0)
            seen = set()
            for e in raw:
                if e["period"] == 5:
                    continue
                kind = e["type"]["name"]
                team = e["team"]["id"]
                if kind == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
                    raw_goals[team] += 1
                if kind in {"Own Goal For", "Own Goal Against"} and e["id"] not in seen:
                    beneficiary = (
                        team if kind == "Own Goal For" else next(t for t in teams if t != team)
                    )
                    raw_goals[beneficiary] += 1
                    seen.add(e["id"])
                    seen.update(e.get("related_events", []))
            assert [raw_goals[t] for t in teams] == [meta["home_score"], meta["away_score"]]
            blocked_raw_scores[mid] = dict(
                raw_goal_count=[raw_goals[t] for t in teams], temporal_score_states="blocked"
            )
            boundary_failures[mid] = conflicts
            assert q["material_failures"] and mid not in {r["match_id"] for r in validated}
            continue
        assert not q["material_failures"]
        scores = {"score": dict.fromkeys(teams, 0), "shootout": dict.fromkeys(teams, 0)}
        awarded = set()
        projected = {r["event_id"]: r for r in validated if r["match_id"] == mid}
        for e in raw:
            r = projected[e["id"]]
            domain = "shootout" if e["period"] == 5 else "score"
            for d in scores:
                assert [r[f"{d}_{t}_before"] for t in ("home", "away")] == [
                    scores[d][i] for i in teams
                ]
            kind = e["type"]["name"]
            t = e["team"]["id"]
            if kind == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
                scores[domain][t] += 1
            if kind in {"Own Goal For", "Own Goal Against"} and e["id"] not in awarded:
                beneficiary = t if kind == "Own Goal For" else next(i for i in teams if i != t)
                scores[domain][beneficiary] += 1
                awarded.add(e["id"])
                awarded.update(e.get("related_events", []))
            for d in scores:
                assert [r[f"{d}_{t}_after"] for t in ("home", "away")] == [
                    scores[d][i] for i in teams
                ]
            assert r["period_elapsed_ms"] == elapsed(e)
        assert [scores["score"][i] for i in teams] == [meta["home_score"], meta["away_score"]]
        expected_exposure = independent_exposure(raw, roster)
        for p in q["exposure"]["players"]:
            expected = expected_exposure.get((p["team_id"], p["player_id"]))
            actual = p["provisional_recorded_seconds"]
            assert (
                expected is actual is None
                or expected is not None
                and actual is not None
                and abs(expected - actual) < 1e-7
            )
            assert p["minutes_played"] is None and not p["per90_eligible"]
        groups = defaultdict(list)
        for e in raw:
            if e.get("possession") is not None:
                groups[e["possession"]].append(e)
        for group in groups.values():
            own = [
                e
                for e in group
                if e["team"]["id"] == e["possession_team"]["id"]
                and e["type"]["name"] in OWNER_TYPES
                and e["period"] in (1, 2, 3, 4)
            ]
            if len({e["period"] for e in group}) != 1:
                continue
            for i, e in enumerate(own):
                future = own[i + 1 : i + 6]
                if successful_move(e) and len(future) == 5:
                    all_expected[mid, e["id"]] = (e, future, teams)
        checks.append(
            dict(
                match_id=mid,
                score=[scores["score"][i] for i in teams],
                shootout=[scores["shootout"][i] for i in teams]
                if 5 in {e["period"] for e in raw}
                else None,
                events=len(raw),
            )
        )
    rows = json.loads((root / "forecast_rows.json").read_bytes())
    assert {(r["match_id"], r["event_id"]) for r in rows} == set(all_expected)
    for r in rows:
        e, future, teams = all_expected[r["match_id"], r["event_id"]]
        assert r["feature_event_ids"] == [e["id"]] and r["outcome_event_ids"] == [
            s["id"] for s in future
        ]
        assert r["outcome"] == int(any(s["type"]["name"] == "Shot" for s in future))
        start = e.get("location") or [None, None]
        end = e[e["type"]["name"].lower()].get("end_location") or [None, None]
        assert r["source_feature_geometry"] == start[:2] + end[:2]
        endpoint_ok = (
            all(v is not None for v in end[:2]) and 0 <= end[0] <= 120 and 0 <= end[1] <= 80
        )
        origin_ok = (
            all(v is not None for v in start[:2]) and 0 <= start[0] <= 120 and 0 <= start[1] <= 80
        )
        expected_location = (
            f"{min(5, int(end[0] / 20))}:{min(3, int(end[1] / 20))}" if endpoint_ok else None
        )
        dx = end[0] - start[0] if origin_ok and endpoint_ok else None
        assert r["features"]["location"] == expected_location
        assert r["features"]["forwardness"] == (
            ["nonpositive", "0to5", "5to10", "above10"][bisect_left([0, 5, 10], dx)]
            if dx is not None
            else None
        )
        for threshold in [5, 10, 15]:
            assert r["features"][f"gain_{threshold}"] == (
                str(dx >= threshold) if dx is not None else None
            )
        diff = (r["score_home_before"] - r["score_away_before"]) * (
            1 if e["team"]["id"] == teams[0] else -1
        )
        state = "leading" if diff > 0 else "trailing" if diff < 0 else "level"
        assert r["features"]["context"] == f"period={e['period']}:state={state}"
    by_match = defaultdict(list)
    for r in rows:
        by_match[r["match_id"]].append(r)
    results = json.loads((root / "baseline_results.json").read_bytes())
    train_ids = {i for source, i in results["partitions"]["train"]}
    assert train_ids == {8649, 8650} and results["partitions"]["test"] == [
        ["statsbomb_open_data", 8655]
    ]
    prior = sum(sum(r["outcome"] for r in by_match[i]) / len(by_match[i]) for i in train_ids) / len(
        train_ids
    )
    predictions = json.loads((root / "baseline_predictions.json").read_bytes())
    for feature, value in results["results"].items():
        assert abs(value["training_prior"] - prior) < 1e-15
        context = defaultdict(lambda: [0.0, 0.0])
        for i in train_ids:
            for r in by_match[i]:
                name = r["features"][feature]
                if name is not None:
                    context[name][0] += r["outcome"] / len(by_match[i])
                    context[name][1] += 1 / len(by_match[i])
        for p in [p for p in predictions if p["baseline_feature"] == feature]:
            expected = (
                context[p["context"]][0] / context[p["context"]][1]
                if p["context"] in context
                else prior
            )
            assert abs(p["baseline"] - prior) < 1e-15 and abs(p["candidate"] - expected) < 1e-12
        test = [
            p for p in predictions if p["baseline_feature"] == feature and p["partition"] == "test"
        ]
        for field in ("baseline", "candidate"):
            expected = sum((p[field] - p["outcome"]) ** 2 for p in test) / len(test)
            assert (
                abs(expected - value["comparisons"]["test"]["scores"][field]["equal_match_brier"])
                < 1e-12
            )
            probabilities = [p[field] if p["outcome"] else 1 - p[field] for p in test]
            impossible = sum(v == 0 for v in probabilities)
            score = value["comparisons"]["test"]["scores"][field]
            assert score["infinite_log_loss_predictions"] == impossible
            if impossible:
                assert score["equal_match_log_loss"] is None
            else:
                assert (
                    abs(
                        score["equal_match_log_loss"]
                        - sum(-math.log(v) for v in probabilities) / len(probabilities)
                    )
                    < 1e-12
                )
            for i, bin_row in enumerate(score["calibration"]):
                selected = [p for p in test if min(int(p[field] * 5), 4) == i]
                assert bin_row["n"] == len(selected)
                if selected:
                    assert (
                        abs(
                            bin_row["mean_probability"]
                            - sum(p[field] for p in selected) / len(selected)
                        )
                        < 1e-12
                    )
                    assert (
                        abs(
                            bin_row["observed_frequency"]
                            - sum(p["outcome"] for p in selected) / len(selected)
                        )
                        < 1e-12
                    )
        assert value["comparisons"]["test"]["match_bootstrap_95_interval"] is None
    print(
        json.dumps(
            dict(
                status="PASS",
                passed_pilot_ids=sorted(
                    i for i, q in reports.items() if not q["material_failures"]
                ),
                pilot_source_manifests={
                    str(i): sha(raw_root / str(i) / "manifest.json") for i in reports
                },
                canonical_matches=len(originals),
                canonical_events=len(canonical),
                validated_matches=len({r["match_id"] for r in validated}),
                validated_events=len(validated),
                independent_scores=checks,
                boundary_failures=boundary_failures,
                blocked_raw_score_checks=blocked_raw_scores,
                source_forecast_rows=len(rows),
                heldout_test_matches=1,
                limitations="pilot only; no statistical sufficiency or general football validation",
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
