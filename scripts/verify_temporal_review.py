"""Independent interval-scenario and frozen-audit verification. REVIEW CONFIG."""

import hashlib
import itertools
import json
import subprocess
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path


def h(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ms(e):
    hours, minutes, seconds = e["timestamp"].split(":")
    secs, millis = seconds.split(".")
    return int(hours) * 3600000 + int(minutes) * 60000 + int(secs) * 1000 + int(millis)


def census(raw, ends):
    active = {}
    totals = defaultdict(int)
    for e in raw:
        if e["type"]["name"] == "Starting XI":
            active[e["team"]["id"]] = {p["player"]["id"] for p in e["tactics"]["lineup"]}
    for period in (1, 2, 3, 4):
        opened = {(t, p): 0 for t, players in active.items() for p in players}

        def close(t, p, time, opened=opened):
            totals[t, p] += time - opened.pop((t, p))

        for e in [e for e in raw if e["period"] == period]:
            t = e["team"]["id"]
            p = e.get("player", {}).get("id")
            kind = e["type"]["name"]
            if kind in ("Substitution", "Player Off"):
                close(t, p, ms(e))
                active[t].remove(p)
                if kind == "Substitution":
                    new = e["substitution"]["replacement"]["id"]
                    active[t].add(new)
                    opened[t, new] = ms(e)
            if kind == "Player On":
                active[t].add(p)
                opened[t, p] = ms(e)
            card = (
                (e.get("foul_committed") or e.get("bad_behaviour") or {})
                .get("card", {})
                .get("name")
            )
            if card in ("Red Card", "Second Yellow") and p in active[t]:
                close(t, p, ms(e))
                active[t].remove(p)
        for t, p in list(opened):
            close(t, p, ends[period - 1])
    return totals


def verify_cv(rows, freeze):
    ids = {8649, 8650, 8651, 8652}
    by = {i: [r for r in rows if r["match_id"] == i] for i in ids}
    assert freeze["development_match_ids"] == sorted(ids) and not freeze["test_scored"]
    assert (
        freeze["development_rows_sha256"]
        == hashlib.sha256(
            (
                json.dumps(
                    [r for r in rows if r["match_id"] in ids],
                    sort_keys=True,
                    indent=2,
                    allow_nan=False,
                )
                + "\n"
            ).encode()
        ).hexdigest()
    )
    for feature, result in freeze["families"].items():
        scores = {}
        for alpha in (Fraction(1, 4), Fraction(1, 2), Fraction(1), Fraction(2), Fraction(4)):
            folds = []
            for held in ids:
                prior = (
                    sum(
                        Fraction(sum(r["outcome"] for r in by[m]), len(by[m])) for m in ids - {held}
                    )
                    / 3
                )
                bins = defaultdict(lambda: [Fraction(0), Fraction(0)])
                for m in ids - {held}:
                    for name in {r["features"][feature] for r in by[m]} - {None}:
                        values = [r for r in by[m] if r["features"][feature] == name]
                        bins[name][0] += Fraction(sum(r["outcome"] for r in values), len(by[m]))
                        bins[name][1] += Fraction(len(values), len(by[m]))
                loss = Fraction(0)
                for name in {r["features"][feature] for r in by[held]}:
                    values = [r for r in by[held] if r["features"][feature] == name]
                    s, n = bins.get(name, [Fraction(0), Fraction(0)])
                    p = (s + alpha * prior) / (n + alpha)
                    positive = sum(r["outcome"] for r in values)
                    loss += (1 - p) ** 2 * positive + p * p * (len(values) - positive)
                folds.append(loss / len(by[held]))
            scores[alpha] = sum(folds) / 4
        selected = min(scores, key=lambda a: (scores[a], -a))
        assert float(selected) == result["alpha_match_equivalent_mass"]
        for a, v in scores.items():
            assert abs(float(v) - result["grid_brier"][str(float(a))]) < 1e-12


def main():
    root = Path(sys.argv[1])
    config = sys.argv[2]
    manifest = json.loads((root / "manifest.json").read_bytes())
    for name, sha in manifest["files"].items():
        assert h(root / name) == sha
    for p, sha in manifest["protected_inputs"].items():
        assert h(Path(p)) == sha
    f = json.loads((root / "forensic.json").read_bytes())
    a = json.loads((root / "baseline_audit.json").read_bytes())
    parent = Path(manifest["parent_bundle"])
    quality = json.loads((parent / "pilot_quality.json").read_bytes())
    q = next(r for r in quality if r["match_id"] == 8656)
    assert f["metadata_versions"] == q["original_match_metadata"]["metadata"]
    raw = json.loads(
        Path(
            "data/raw/statsbomb-corpus/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/8656/8656.json.events"
        ).read_bytes()
    )
    bounds = []
    prefix = [0, 0]
    for row in f["model"]["periods"]:
        p = row["period"]
        group = [e for e in raw if e["period"] == p]
        starts = [e for e in group if e["type"]["name"] == "Half Start"]
        ends = [e for e in group if e["type"]["name"] == "Half End"]
        assert row["start_evidence"] == starts and row["end_evidence"] == ends
        assert len(starts) == len(ends) == 2 and all(ms(e) == 0 for e in starts)
        low, high = min(map(ms, ends)), max(map(ms, ends))
        bounds.append((low, high))
        assert (
            row["observed_end_envelope_ms"] == [low, high]
            and row["event_phase_offset_scenario_ms"] == prefix
        )
        assert all(
            ms(e) < low for e in group if e["type"]["name"] not in ("Half Start", "Half End")
        )
        assert row["exact_physical_end_ms"] is None and not row["physical_end_certified"]
        prefix = [prefix[0] + low, prefix[1] + high]
    assert f["model"]["conditional_recorded_match_duration_ms"] == prefix
    scenarios = [census(raw, ends) for ends in itertools.product(*bounds)]
    for player in f["exposure"]["players"]:
        key = player["team_id"], player["player_id"]
        expected = (
            [min(s[key] for s in scenarios), max(s[key] for s in scenarios)]
            if key in scenarios[0]
            else None
        )
        assert (
            player["conditional_recorded_exposure_ms"] == expected
            and player["official_minutes"] is None
            and not player["per90_eligible"]
        )
    assert not f["exposure"]["issues"] and not f["model"]["expansion_authorized"]
    rows = json.loads((parent / "forecast_rows.json").read_bytes())
    pred = json.loads((parent / "baseline_predictions.json").read_bytes())
    for r in a["match_prevalence"]:
        values = [v for v in rows if v["match_id"] == r["match_id"]]
        assert r["n"] == len(values) and r["positive"] == sum(v["outcome"] for v in values)
    expected = {
        (p["baseline_feature"], p["partition"], p["match_id"], p["event_id"])
        for p in pred
        if p["baseline_feature"] in ("context", "location")
        and p["outcome"] == 1
        and p["candidate"] == 0
    }
    assert expected == {
        (r["feature"], r["partition"], r["match_id"], r["event_id"])
        for r in a["zero_probability_errors"]
    }
    for b in a["bin_support"]:
        matched = [r for r in rows if r["features"][b["feature"]] == b["bin"]]
        train = [r for r in matched if r["match_id"] in (8649, 8650)]
        assert b["train_n"] == len(train) and b["train_positive"] == sum(
            r["outcome"] for r in train
        )
        masses = []
        positive = []
        for mid in (8649, 8650):
            n = sum(r["match_id"] == mid for r in rows)
            v = [r for r in train if r["match_id"] == mid]
            masses.append(Fraction(len(v), n))
            positive.append(Fraction(sum(r["outcome"] for r in v), n))
        if sum(masses) and b["bin"] is not None:
            assert abs(b["predicted_probability"] - float(sum(positive) / sum(masses))) < 1e-12
    original_process = json.loads((parent / "process_audits.json").read_bytes())
    expected_counts = Counter(
        (w["match_id"], w["eligibility"]) for p in original_process for w in p["forecast_windows"]
    )
    assert expected_counts == {
        (r["match_id"], r["eligibility"]): r["n"] for r in a["censoring_selection"]
    }
    verify_cv(rows, json.loads((root / "development_shrinkage.json").read_bytes()))
    # Full PR15 independent source reconciliation is repeated against the unchanged parent.
    delivery = json.loads(Path(manifest["parent_delivery"]).read_bytes())
    reports = Path(delivery["independent_verification"]).with_name("reports.json")
    original = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("verify_worldcup_source.py")),
            config,
            str(reports),
            str(parent),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(original.stdout)["status"] == "PASS"
    assert json.loads(reports.with_name("pilot-gate.json").read_bytes())["status"] == "BLOCKED"
    print(
        json.dumps(
            dict(
                status="PASS",
                conditional_endpoint_scenarios=len(scenarios),
                source_events=len(raw),
                conditional_total_ms=prefix,
                zero_probability_errors=len(expected),
                original_source_reconciliation="PASS",
                expansion_gate="BLOCKED",
                gate_changed=False,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
