"""Frozen record-order baseline execution; development selection before test acquisition."""

import argparse
import json
import math
import tempfile
from collections import defaultdict
from pathlib import Path

from fil.research.accepted_corpus import PROPOSAL, policy, write_bundle
from fil.research.acquisition import REVISION, digest, verify
from fil.research.corpus_expansion import frozen_plan
from fil.research.evaluation import dependence_audit
from fil.research.integrity_review import verify_artifact
from fil.research.pilot import encode
from fil.research.possession_target import label_support
from fil.research.prospective import (
    EXPOSED,
    fit_weighted_baseline,
    paired_uncertainty,
    predict_weighted,
)

VERSION = "fil-accepted-corpus-baselines-1"
FEATURES = ("context", "location", "forwardness", "gain_5", "gain_10", "gain_15")
ALPHAS = (0.25, 0.5, 1, 2, 4)


def rows_for_report(folder: Path, partition: str) -> tuple[list[dict], dict]:
    """Source-record features at cutoff, labels separate, no future xG/terminal features."""
    verify_artifact(folder)
    q = json.loads((folder / "quality.json").read_bytes())
    mid = q["match_id"]
    if mid in EXPOSED:
        raise ValueError("All seven exposed matches are excluded from confirmation")
    metadata = dict(
        source="statsbomb_open_data",
        match_id=mid,
        team_ids=[q["original_match_metadata"][k][k + "_id"] for k in ("home_team", "away_team")],
        player_ids=sorted({r["player_id"] for r in q["roster"]}),
    )
    if q["status"] != "PASS":
        return [], metadata
    raw = json.loads((Path(q["raw_manifest_path"]).parent / f"{mid}.json.events").read_bytes())
    by = {e["id"]: e for e in raw}
    decisions = {d["provider_index"]: d for d in q["metric_eligibility"]["score"]["decisions"]}
    teams = metadata["team_ids"]
    score = dict.fromkeys(teams, 0)
    states, prior, past = {}, {}, []
    for e in raw:
        states[e["id"]], prior[e["id"]] = score.copy(), past.copy()
        d = decisions.get(e["index"])
        if d and d["scored"] and d["domain"] == "match_play":
            score[d["beneficiary_team_id"]] += 1
            past.extend(d["source_event_ids"])
    rows = []
    for label in json.loads((folder / "labels.json").read_bytes()):
        e = by[label["cutoff_event_id"]]
        team = e["team"]["id"]
        opponent = next(t for t in teams if t != team)
        difference = states[e["id"]][team] - states[e["id"]][opponent]
        state = "leading" if difference > 0 else "trailing" if difference < 0 else "level"
        start = e.get("location")
        end = e[e["type"]["name"].lower()].get("end_location")
        dx = end[0] - start[0] if start is not None and end is not None else None
        features = dict(
            context=f"period={e['period']}:state={state}",
            location=f"{min(int(end[0] // 20), 5)}:{min(int(end[1] // 20), 3)}" if end else None,
            forwardness="nonpositive"
            if dx is not None and dx <= 0
            else "0_to_5"
            if dx is not None and dx <= 5
            else "5_to_10"
            if dx is not None and dx <= 10
            else "over_10"
            if dx is not None
            else None,
            **{
                f"gain_{threshold}": str(dx >= threshold) if dx is not None else None
                for threshold in (5, 10, 15)
            },
        )
        lineage = [e["id"], *prior[e["id"]]]
        rows.append(
            dict(
                label,
                partition=partition,
                features=features,
                feature_indices=[by[i]["index"] for i in lineage],
                context_feature_event_ids=lineage,
                pre_event_owner_score_difference=difference,
            )
        )
    return rows, metadata


def load_phase(index: Path, plan: dict) -> tuple[list[dict], list[dict], dict]:
    data = json.loads(index.read_bytes())
    if data["policy"] != policy() or data["plan_sha256"] != digest(encode(plan).encode()):
        raise ValueError("Frozen phase policy/partition binding changed")
    partitions = {
        m["match_id"]: name for name, members in plan["partitions"].items() for m in members
    }
    for batch in data["batches"]:
        p = Path(batch["proof"])
        if digest(p.read_bytes()) != batch["proof_sha256"]:
            raise ValueError("Independent batch proof changed")
        proof = json.loads(p.read_bytes())
        if proof["status"] != "PASS" or proof["policy"] != policy():
            raise ValueError("Missing accepted independent quality verification")
        for folder in batch["reports"]:
            f = Path(folder)
            q = json.loads((f / "quality.json").read_bytes())
            if proof["reports"].get(str(q["match_id"])) != digest(
                (f / "manifest.json").read_bytes()
            ):
                raise ValueError("Research report not independently bound")
    rows, metadata, excluded = [], [], {}
    for p in data["reports"]:
        folder = Path(p)
        q = json.loads((folder / "quality.json").read_bytes())
        rawmanifest = Path(q["raw_manifest_path"])
        verify(rawmanifest.parent, PROPOSAL)
        if digest(rawmanifest.read_bytes()) != q["source_manifest_sha256"]:
            raise ValueError("Source changed after independent quality verification")
        if q["match_id"] not in partitions:
            raise ValueError("Match outside frozen partition plan")
        r, meta = rows_for_report(folder, partitions[q["match_id"]])
        rows.extend(r)
        metadata.append(meta)
        if q["status"] != "PASS" or not any(v["outcome"] is not None for v in r):
            excluded[q["match_id"]] = q["material_failures"] or ["no_confirmed_labels"]
    expected = {
        m["match_id"]
        for name, members in plan["partitions"].items()
        if (name == "test") == (data["phase"] == "test")
        for m in members
    }
    if len(metadata) != len(expected) or {m["match_id"] for m in metadata} != expected:
        raise ValueError("Phase must preserve exact frozen match coverage")
    return rows, metadata, excluded


def scores(rows: list[dict], predictions: list[float]) -> dict:
    """Equal-match possession-weighted proper scores, no clipping or missing-as-zero."""
    if len(rows) != len(predictions) or not rows:
        raise ValueError("Nonempty aligned labelled evaluation rows required")
    by_match = defaultdict(list)
    for r, p in zip(rows, predictions, strict=True):
        if r["outcome"] not in (0, 1) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("Confirmed label and finite probability required")
        by_match[r["match_id"]].append((r, p))
    brier, logs, calibration = {}, {}, []
    infinite = 0
    for mid, values in by_match.items():
        if not math.isclose(sum(r["within_match_possession_weight"] for r, p in values), 1):
            raise ValueError("Expected unit match weights")
        brier[mid] = math.fsum(
            r["within_match_possession_weight"] * (p - r["outcome"]) ** 2 for r, p in values
        )
        terms = []
        for r, p in values:
            correct = p if r["outcome"] else 1 - p
            if correct == 0:
                infinite += 1
            else:
                terms.append(-r["within_match_possession_weight"] * math.log(correct))
        logs[mid] = math.fsum(terms) if len(terms) == len(values) else None
    for i in range(10):
        group = [(r, p) for r, p in zip(rows, predictions, strict=True) if min(int(p * 10), 9) == i]
        mass = math.fsum(r["within_match_possession_weight"] / len(by_match) for r, p in group)
        calibration.append(
            dict(
                bin=i,
                n=len(group),
                primary_weight=mass,
                prediction=math.fsum(
                    r["within_match_possession_weight"] / len(by_match) * p for r, p in group
                )
                / mass
                if mass
                else None,
                observed=math.fsum(
                    r["within_match_possession_weight"] / len(by_match) * r["outcome"]
                    for r, p in group
                )
                / mass
                if mass
                else None,
            )
        )
    per_match_cutoff = [
        sum((p - r["outcome"]) ** 2 for r, p in v) / len(v) for v in by_match.values()
    ]
    retrieval = []
    for mid, values in by_match.items():
        ranked = sorted(values, key=lambda v: (-v[1], v[0]["cutoff_provider_index"]))[:10]
        positive = sum(r["outcome"] for r, p in values)
        all_shots = {s for r, p in values if r["outcome"] for s in r["later_shot_event_ids"]}
        retrieved = {s for r, p in ranked if r["outcome"] for s in r["later_shot_event_ids"]}
        retrieval.append(
            dict(
                match_id=mid,
                precision_at_10=sum(r["outcome"] for r, p in ranked) / len(ranked),
                recall_at_10=sum(r["outcome"] for r, p in ranked) / positive if positive else None,
                unique_shot_coverage=len(retrieved) / len(all_shots) if all_shots else None,
            )
        )
    return dict(
        equal_match_possession_brier=math.fsum(brier.values()) / len(brier),
        equal_match_cutoff_brier=sum(per_match_cutoff) / len(per_match_cutoff),
        pooled_cutoff_brier=sum(
            (p - r["outcome"]) ** 2 for r, p in zip(rows, predictions, strict=True)
        )
        / len(rows),
        log_loss=None if infinite else sum(logs.values()) / len(logs),
        infinite_log_predictions=infinite,
        per_match_brier=brier,
        calibration=calibration,
        retrieval_at_10=retrieval,
    )


def freeze(
    development: Path, review: Path, rawroot: Path, output: Path, implementation: str
) -> Path:
    plan, plan_hash = frozen_plan(review)
    test_ids = sorted(m["match_id"] for m in plan["partitions"]["test"])
    if any((rawroot / REVISION / str(mid)).exists() for mid in test_ids):
        raise ValueError("Test payloads already opened: cannot create a prospective model freeze")
    rows, metadata, excluded = load_phase(development, plan)
    train = [r for r in rows if r["partition"] == "train" and r["outcome"] is not None]
    validation = [r for r in rows if r["partition"] == "validation" and r["outcome"] is not None]
    if not train or not validation or any(r["partition"] == "test" for r in rows):
        raise ValueError("Development-only nonempty frozen partitions required")
    models, choices = {}, {}
    models["constant"] = fit_weighted_baseline(train, "constant", 1)
    for feature in FEATURES:
        trials = []
        for alpha in ALPHAS:
            m = fit_weighted_baseline(train, feature, alpha)
            loss = scores(validation, predict_weighted(m, validation))[
                "equal_match_possession_brier"
            ]
            trials.append(dict(alpha=alpha, validation_brier=loss))
        best = min(trials, key=lambda r: (r["validation_brier"], -r["alpha"]))
        models[feature] = fit_weighted_baseline(train, feature, best["alpha"])
        choices[feature] = dict(selected_alpha=best["alpha"], trials=trials)
    info = dict(
        version=VERSION,
        policy=policy(),
        plan_sha256=plan_hash,
        test_match_ids=test_ids,
        frozen_before_test_acquisition=True,
        choices=choices,
        exclusions=excluded,
        training_match_ids=sorted({r["match_id"] for r in train}),
        validation_match_ids=sorted({r["match_id"] for r in validation}),
        development_index=str(development.resolve()),
        development_index_sha256=digest(development.read_bytes()),
        study_status="exploratory_no_scientific_or_analyst_validation",
    )
    target = output / "model-freeze" / implementation
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        for name, value in [
            ("freeze", info),
            ("models", models),
            ("development_rows", rows),
            ("metadata", metadata),
        ]:
            (stage / f"{name}.json").write_text(encode(value))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=implementation,
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                )
            )
        )
        write_bundle(stage, target)
    return target


def evaluate(
    test_index: Path, frozen: Path, review: Path, output: Path, implementation: str
) -> Path:
    verify_artifact(frozen)
    plan, plan_hash = frozen_plan(review)
    info = json.loads((frozen / "freeze.json").read_bytes())
    if info["plan_sha256"] != plan_hash or not info["frozen_before_test_acquisition"]:
        raise ValueError("Study freeze mismatch")
    index = json.loads(test_index.read_bytes())
    if index["model_freeze_manifest_sha256"] != digest((frozen / "manifest.json").read_bytes()):
        raise ValueError("Models changed since test acquisition")
    rows, metadata, excluded = load_phase(test_index, plan)
    if {r["match_id"] for r in metadata} != set(info["test_match_ids"]):
        raise ValueError("Exact test identity coverage required")
    labelled = [r for r in rows if r["outcome"] is not None]
    models = json.loads((frozen / "models.json").read_bytes())
    predictions = {name: predict_weighted(model, labelled) for name, model in models.items()}
    result = {name: scores(labelled, values) for name, values in predictions.items()}
    constant = result["constant"]["equal_match_possession_brier"]
    eligible_metadata = [m for m in metadata if m["match_id"] in {r["match_id"] for r in labelled}]
    for _name, s in result.items():
        s["brier_improvement_from_constant"] = constant - s["equal_match_possession_brier"]
        s["relative_brier_skill"] = (
            s["brier_improvement_from_constant"] / constant if constant else None
        )
        effects = [
            dict(
                source="statsbomb_open_data",
                match_id=m["match_id"],
                effect=result["constant"]["per_match_brier"][m["match_id"]]
                - s["per_match_brier"][m["match_id"]],
            )
            for m in eligible_metadata
        ]
        s["conditional_uncertainty"] = paired_uncertainty(effects, eligible_metadata)
        s["leave_one_test_team_out"] = {
            t: sum(
                e["effect"]
                for e in effects
                if t not in next(m["team_ids"] for m in metadata if m["match_id"] == e["match_id"])
            )
            / sum(
                t not in next(m["team_ids"] for m in metadata if m["match_id"] == e["match_id"])
                for e in effects
            )
            if any(t not in m["team_ids"] for m in eligible_metadata)
            else None
            for t in sorted({t for m in eligible_metadata for t in m["team_ids"]})
        }
    development_metadata = json.loads((frozen / "metadata.json").read_bytes())
    partitions = {
        name: {("statsbomb_open_data", m["match_id"]) for m in plan["partitions"][name]}
        for name in plan["partitions"]
    }
    report = dict(
        version=VERSION,
        policy=policy(),
        frozen_models_manifest_sha256=digest((frozen / "manifest.json").read_bytes()),
        plan_sha256=plan_hash,
        results=result,
        test_exclusions=excluded,
        label_support=label_support(rows),
        test_match_support={
            m["match_id"]: label_support([r for r in rows if r["match_id"] == m["match_id"]])
            for m in metadata
        },
        dependence=dependence_audit(partitions, development_metadata + metadata),
        scientifically_validated=False,
        analyst_utility="not_evaluated",
        conclusion="INCONCLUSIVE",
        limits=(
            "Five held matches, repeated teams/players, variable horizons, label selection; "
            "conditional intervals do not certify independence"
        ),
    )
    target = output / "evaluation" / implementation
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        for name, value in [
            ("results", report),
            ("test_rows", rows),
            ("predictions", predictions),
            ("metadata", metadata),
        ]:
            (stage / f"{name}.json").write_text(encode(value))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=implementation,
                    model_freeze=str(frozen.resolve()),
                    test_index=str(test_index.resolve()),
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                )
            )
        )
        write_bundle(stage, target)
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("freeze", "evaluate"))
    p.add_argument("--index", required=True, type=Path)
    p.add_argument("--frozen-review", required=True, type=Path)
    p.add_argument("--model-freeze", type=Path)
    p.add_argument("--pipeline-revision", required=True)
    p.add_argument("--raw-root", type=Path, default=Path("data/raw/statsbomb-corpus"))
    p.add_argument("--output", type=Path, default=Path("data/interim/accepted-corpus"))
    a = p.parse_args()
    folder = (
        freeze(a.index, a.frozen_review, a.raw_root, a.output, a.pipeline_revision)
        if a.stage == "freeze"
        else evaluate(a.index, a.model_freeze, a.frozen_review, a.output, a.pipeline_revision)
    )
    print(encode(dict(bundle=str(folder.resolve()))))


if __name__ == "__main__":
    main()
