"""Independent source-feature and rational-arithmetic baseline verification. FREEZE [EVALUATION]."""

import hashlib
import json
import math
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bundle(folder):
    m = json.loads((folder / "manifest.json").read_bytes())
    for name, h in m["files"].items():
        assert sha(folder / name) == h
    return m


def feature_check(rows):
    grouped = defaultdict(list)
    for r in rows:
        grouped[r["match_id"]].append(r)
    for mid, values in grouped.items():
        assert mid not in {8649, 8650, 8651, 8652, 8655, 8656, 8658}
        paths = list(Path("data/raw/statsbomb-corpus").glob(f"*/{mid}/{mid}.json.events"))
        assert len(paths) == 1
        raw = json.loads(paths[0].read_bytes())
        by = {e["id"]: e for e in raw}
        teams = sorted({e["team"]["id"] for e in raw})
        awards = []
        for e in raw:
            if e["period"] == 5:
                continue
            kind = e["type"]["name"]
            if kind == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
                awards.append((e["index"], e["team"]["id"]))
            elif kind == "Own Goal Against":
                linked = [
                    other
                    for other in raw
                    if other["type"]["name"] == "Own Goal For"
                    and (
                        other["id"] in e.get("related_events", [])
                        or e["id"] in other.get("related_events", [])
                    )
                ]
                awards.append(
                    (
                        min([e["index"]] + [o["index"] for o in linked]),
                        next(t for t in teams if t != e["team"]["id"]),
                    )
                )
            elif kind == "Own Goal For" and not any(
                o["type"]["name"] == "Own Goal Against"
                and (
                    o["id"] in e.get("related_events", []) or e["id"] in o.get("related_events", [])
                )
                for o in raw
            ):
                awards.append((e["index"], e["team"]["id"]))
        for r in values:
            e = by[r["cutoff_event_id"]]
            team = e["team"]["id"]
            diff = sum((1 if t == team else -1) for idx, t in awards if idx < e["index"])
            state = "leading" if diff > 0 else "trailing" if diff < 0 else "level"
            start = e.get("location")
            end = e[e["type"]["name"].lower()].get("end_location")
            dx = end[0] - start[0] if end is not None and start is not None else None
            f = r["features"]
            assert f["context"] == f"period={e['period']}:state={state}"
            assert r["pre_event_owner_score_difference"] == diff
            assert f["location"] == (
                f"{min(int(end[0] / 20), 5)}:{min(int(end[1] / 20), 3)}" if end else None
            )
            bins = (
                "nonpositive"
                if dx is not None and dx <= 0
                else "0_to_5"
                if dx is not None and dx <= 5
                else "5_to_10"
                if dx is not None and dx <= 10
                else "over_10"
                if dx is not None
                else None
            )
            assert f["forwardness"] == bins
            for limit in (5, 10, 15):
                assert f[f"gain_{limit}"] == (str(dx >= limit) if dx is not None else None)
            assert max(r["feature_indices"]) <= e["index"]
            assert all(by[i]["index"] <= e["index"] for i in r["context_feature_event_ids"])


def exact_weights(rows):
    groups = defaultdict(lambda: defaultdict(list))
    for r in rows:
        groups[r["match_id"]][r["possession_id"]].append(r)
    return {
        (mid, r["cutoff_event_id"]): Fraction(1, len(groups[mid]) * len(v))
        for mid, pos in groups.items()
        for v in pos.values()
        for r in v
    }


def sufficient(rows, weights, feature):
    bins = defaultdict(lambda: [Fraction(0), Fraction(0)])
    for r in rows:
        w = weights[r["match_id"], r["cutoff_event_id"]]
        key = r["features"].get(feature)
        bins[key][0] += r["outcome"] * w
        bins[key][1] += w
    return bins


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-12), (float(a), float(b))


def verify(frozen, evaluation=None):
    bundle(frozen)
    info = json.loads((frozen / "freeze.json").read_bytes())
    rows = json.loads((frozen / "development_rows.json").read_bytes())
    feature_check(rows)
    assert not any(r["partition"] == "test" for r in rows)
    train = [r for r in rows if r["partition"] == "train" and r["outcome"] is not None]
    val = [r for r in rows if r["partition"] == "validation" and r["outcome"] is not None]
    tw, vw = exact_weights(train), exact_weights(val)
    ntrain = len({r["match_id"] for r in train})
    nval = len({r["match_id"] for r in val})
    pi = (
        sum(r["outcome"] * tw[r["match_id"], r["cutoff_event_id"]] for r in train) + Fraction(1, 2)
    ) / (ntrain + 1)
    models = json.loads((frozen / "models.json").read_bytes())
    for name, model in models.items():
        assert model["training_matches"] == [
            ["statsbomb_open_data", i] for i in sorted({r["match_id"] for r in train})
        ]
        close(pi, model["prior"])
        bins = sufficient(train, tw, name)
        for key, (s, n) in bins.items():
            if key is not None:
                alpha = Fraction(str(model["alpha"]))
                close((s + alpha * pi) / (n + alpha), model["bins"][key])
        if name == "constant":
            assert not model["bins"]
            continue
        validation = sufficient(val, vw, name)
        losses = {}
        for a in (Fraction(1, 4), Fraction(1, 2), Fraction(1), Fraction(2), Fraction(4)):
            loss = Fraction(0)
            for key, (sy, ny) in validation.items():
                s, n = bins.get(key, (Fraction(0), Fraction(0)))
                p = (s + a * pi) / (n + a) if key is not None and n else pi
                loss += ny * p * p - 2 * sy * p + sy
            losses[a] = loss / nval
        selected = min(losses, key=lambda a: (losses[a], -a))
        assert float(selected) == info["choices"][name]["selected_alpha"] == model["alpha"]
        for trial in info["choices"][name]["trials"]:
            close(losses[Fraction(str(trial["alpha"]))], trial["validation_brier"])
    result = dict(
        status="PASS",
        model_manifest_sha256=sha(frozen / "manifest.json"),
        development_feature_rows=len(rows),
        model_count=len(models),
        verifier_sha256=sha(Path(__file__)),
        test_evaluated=False,
    )
    if evaluation is not None:
        bundle(evaluation)
        test = json.loads((evaluation / "test_rows.json").read_bytes())
        feature_check(test)
        assert {r["match_id"] for r in test} == set(info["test_match_ids"])
        labelled = [r for r in test if r["outcome"] is not None]
        weights = exact_weights(labelled)
        predictions = json.loads((evaluation / "predictions.json").read_bytes())
        report = json.loads((evaluation / "results.json").read_bytes())
        for name, model in models.items():
            p = predictions[name]
            assert len(p) == len(labelled)
            losses = defaultdict(Fraction)
            for r, pred in zip(labelled, p, strict=True):
                close(pred, model["bins"].get(r["features"].get(name), model["prior"]))
                losses[r["match_id"]] += (
                    weights[r["match_id"], r["cutoff_event_id"]]
                    * (Fraction(str(pred)) - r["outcome"]) ** 2
                )
            scores = report["results"][name]
            close(sum(losses.values()) / len(losses), scores["equal_match_possession_brier"])
            for mid, loss in losses.items():
                close(loss, scores["per_match_brier"][str(mid)])
            for c in scores["calibration"]:
                group = [
                    (r, v)
                    for r, v in zip(labelled, p, strict=True)
                    if min(int(v * 10), 9) == c["bin"]
                ]
                assert c["n"] == len(group)
                mass = sum(weights[r["match_id"], r["cutoff_event_id"]] for r, v in group)
                close(mass / len(losses), c["primary_weight"])
                if mass:
                    close(
                        sum(
                            weights[r["match_id"], r["cutoff_event_id"]] * r["outcome"]
                            for r, v in group
                        )
                        / mass,
                        c["observed"],
                    )
        result.update(
            test_evaluated=True, test_rows=len(test), test_matches=len(info["test_match_ids"])
        )
    return result


if __name__ == "__main__":
    print(json.dumps(verify(*map(Path, sys.argv[1:])), sort_keys=True, indent=2))
