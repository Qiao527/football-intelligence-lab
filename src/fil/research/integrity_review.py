"""Immutable local forensic review; never changes clock v1, pilot gates or frozen forecasts."""

import argparse
import json
import math
import re
import tempfile
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from fil.research.acquisition import REVISION, digest, verify
from fil.research.baseline_audit import DEVELOPMENT, audit, shrinkage_development
from fil.research.pilot import encode
from fil.time.uncertainty import envelopes, exposure_sensitivity

VERSION = "fil-temporal-research-review-1"
DOCUMENTS = {
    "doc/StatsBomb Open Data Specification v1.1.pdf": (
        "spec.pdf",
        "d5a8267939c5db35a9501b1a272cc9861a2bb3bef2f53c723d4a43ec1f5ef477",
    ),
    "doc/Open Data Events v4.0.0.pdf": (
        "events.pdf",
        "05de42cc76b0c9cd26213d8e5c72610cac7d4d92c9c2ac878073a565dbb6c44a",
    ),
}


def verify_artifact(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_bytes())
    if root.is_symlink() or {p.name for p in root.iterdir()} != set(manifest["files"]) | {
        "manifest.json"
    }:
        raise ValueError("Unexpected parent artifact members")
    for name, sha in manifest["files"].items():
        if (
            Path(name).name != name
            or (root / name).is_symlink()
            or digest((root / name).read_bytes()) != sha
        ):
            raise ValueError("Parent artifact changed")
    return manifest


def forensic(raw: list[dict], metadata: dict, roster: list[dict]) -> dict:
    teams = {metadata[k][k + "_id"] for k in ("home_team", "away_team")}
    model = envelopes(raw, teams)
    if any(e["type"]["name"] in ("Own Goal For", "Own Goal Against") for e in raw):
        raise ValueError("This case-specific source score check requires separate own-goal audit")
    order = [metadata[k][k + "_id"] for k in ("home_team", "away_team")]
    score = dict.fromkeys(order, 0)
    states = {}
    goals = []
    for e in raw:
        states[e["id"]] = [score[t] for t in order]
        if (
            e["type"]["name"] == "Shot"
            and e["shot"]["outcome"]["name"] == "Goal"
            and e["period"] != 5
        ):
            score[e["team"]["id"]] += 1
            goals.append(e)
    if [score[t] for t in order] != [metadata["home_score"], metadata["away_score"]]:
        raise ValueError("Raw goals fail official reconciliation")
    for p in model["periods"]:
        evidence = []
        ids = {e["id"] for e in p["end_evidence"]}
        for i, e in enumerate(raw):
            if e["id"] in ids:
                evidence.append(
                    dict(
                        marker=e, score_before=states[e["id"]], neighbors=raw[max(0, i - 3) : i + 4]
                    )
                )
        p["end_neighborhoods"] = evidence
        p["next_period_start_records"] = [
            e for e in raw if e["period"] == p["period"] + 1 and e["type"]["name"] == "Half Start"
        ]
    return dict(
        match_id=metadata["match_id"],
        metadata_versions=metadata.get("metadata"),
        model=model,
        exposure=exposure_sensitivity(raw, roster, model),
        goal_records=goals,
        transition_records=[
            e for e in raw if e["type"]["name"] in ("Substitution", "Player Off", "Player On")
        ],
        invariant_source_score=[score[t] for t in order],
        original_event_count=len(raw),
        source_match_play_shots=sum(e["type"]["name"] == "Shot" and e["period"] != 5 for e in raw),
        source_match_play_known_xg_sum=math.fsum(
            e["shot"]["statsbomb_xg"]
            for e in raw
            if e["type"]["name"] == "Shot"
            and e["period"] != 5
            and e["shot"].get("statsbomb_xg") is not None
        ),
        source_missing_shot_xg_ids=[
            e["id"]
            for e in raw
            if e["type"]["name"] == "Shot" and e["shot"].get("statsbomb_xg") is None
        ],
        diagnosis=(
            "Reciprocal multi-team representations observed; unequal timestamps are not "
            "explained by ordinary 1ms rounding. Provider cause and physical whistle unresolved."
        ),
        gate_recommendation=(
            "Retain BLOCKED expansion. Conditional metric-specific contract only; "
            "not accepted or activated."
        ),
    )


def markdown(f: dict, a: dict, s: dict) -> str:
    lines = [
        "# 8656 forensic and frozen predictive audit",
        "",
        f"Source metadata data_version: {f['metadata_versions']}",
        "",
        f["diagnosis"],
        "",
        "## Exact source boundary evidence",
        "",
        "|Period|Original event ID|Index|Team|Timestamp|Reciprocal related ID|",
        "|---|---|---:|---|---|---|",
    ]
    for p in f["model"]["periods"]:
        for e in p["end_evidence"]:
            lines.append(
                f"|{p['period']}|{e['id']}|{e['index']}|{e['team']['name']}|"
                f"{e['timestamp']}|{', '.join(e.get('related_events', []))}|"
            )
    lines += [
        "",
        "All Half Start records, complete neighboring records, source goals and all "
        "substitution/Off/On records are in forensic.json. No timestamp was replaced.",
        "",
        f"Conditional duration ms: {f['model']['conditional_recorded_match_duration_ms']}. "
        "This is not certified physical time.",
        "",
        "## Prevalence of original eligible labels",
        "",
        "|Match|Partition|Eligible windows|Positive windows|Prevalence|Distinct linked shots|",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in a["match_prevalence"]:
        lines.append(
            f"|{r['match_id']}|{r['partition']}|{r['n']}|{r['positive']}|{r['prevalence']:.8f}|{r['distinct_label_shots']}|"
        )
    lines += [
        "",
        "## All zero-probability errors",
        "",
        "|Family|Partition|Match|Bin|Cutoff source ID|Index|Shot source IDs|",
        "|---|---|---|---|---|---:|---|",
    ]
    for r in a["zero_probability_errors"]:
        lines.append(
            f"|{r['feature']}|{r['partition']}|{r['match_id']}|{r['bin']}|"
            f"{r['event_id']}|{r['provider_index']}|{', '.join(r['shot_event_ids'])}|"
        )
    lines += [
        "",
        "## Exact bin support",
        "",
        "|Family|Bin|Train n|Train positive|Train matches|Probability|"
        "Val n / positive|Test n / positive|",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for r in a["bin_support"]:
        lines.append(
            f"|{r['feature']}|{r['bin']}|{r['train_n']}|{r['train_positive']}|"
            f"{r['train_match_count']}|{r['predicted_probability']:.8f}|"
            f"{r['validation_n']} / {r['validation_positive']}|"
            f"{r['test_n']} / {r['test_positive']}|"
        )
    lines += [
        "",
        "## Censoring and cohort selection",
        "",
        "|Match|Eligibility|n|Observed short-chain shots|Median owner records|Missing endpoints|",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in a["censoring_selection"]:
        lines.append(
            f"|{r['match_id']}|{r['eligibility']}|{r['n']}|{r['observed_short_chain_shots']}|{r['median_owner_records']}|{r['missing_endpoints']}|"
        )
    lines += [
        "",
        "Short-chain observed shots are not relabelled as negatives. Complete-window selection "
        "removes some known terminal shot-producing chains. Calibration/roster overlap are in "
        "baseline_audit.json; no iid-window confidence interval is justified.",
        "",
        "## Separate development-only shrinkage freeze",
        "",
        encode(s),
        "No new model is evaluated on 8655. New confirmation requires genuinely independent "
        "matches; acquisition remains blocked.",
        "",
        f["gate_recommendation"],
        "",
    ]
    return "\n".join(lines)


def build(delivery: Path, output: Path, implementation: str) -> Path:
    if not re.fullmatch("[0-9a-f]{40}", implementation):
        raise ValueError("Full implementation SHA required")
    parent = json.loads(delivery.read_bytes())
    bundle = Path(parent["bundle"])
    verify_artifact(bundle)
    gate = Path(parent["independent_verification"]).with_name("pilot-gate.json")
    if json.loads(gate.read_bytes())["status"] != "BLOCKED":
        raise ValueError("Expected unchanged blocked pilot")
    rawroot = Path("data/raw/statsbomb-corpus") / REVISION / "8656"
    verify(rawroot, Path("docs/research/statsbomb_corpus_proposal.json"))
    run = gate.parent
    old_reports = [Path(p) for p in json.loads((run / "reports.json").read_bytes())]
    for old in old_reports:
        verify_artifact(old)
    protected = [
        delivery,
        *bundle.iterdir(),
        *run.iterdir(),
        *[p for p in rawroot.parent.rglob("*") if p.is_file()],
        *[p for root in old_reports for p in root.iterdir()],
    ]
    snapshots = {str(p.resolve()): digest(p.read_bytes()) for p in protected}
    if any(
        output.resolve().is_relative_to(p.resolve())
        for p in (bundle, gate.parent, rawroot.parent, *old_reports)
    ):
        raise ValueError("Review output must be outside immutable inputs")
    raw = json.loads((rawroot / "8656.json.events").read_bytes())
    quality = json.loads((bundle / "pilot_quality.json").read_bytes())
    q = next(r for r in quality if r["match_id"] == 8656)
    f = forensic(raw, q["original_match_metadata"], q["roster"])
    docs = []
    for name, (local, expected) in DOCUMENTS.items():
        p = Path("data/interim/spatial-docs") / local
        if digest(p.read_bytes()) != expected:
            raise ValueError("Primary documentation changed")
        docs.append(
            dict(
                path=name,
                sha256=expected,
                url=f"https://github.com/hudl/open-data/blob/{REVISION}/"
                + name.replace(" ", "%20"),
            )
        )
    f["primary_documentation"] = docs
    canonical = pq.ParquetFile(bundle / "canonical_all_matches.parquet").read().to_pylist()
    pairs = defaultdict(list)
    for r in canonical:
        if r["event_type"] == "Half End" and r["period"] in (1, 2, 3, 4):
            pairs[r["match_id"], r["period"]].append(json.loads(r["source_record_json"]))
    f["pilot_marker_representation"] = dict(
        playing_periods=len(pairs),
        two_team_pairs=sum(
            len(v) == 2 and len({e["team"]["id"] for e in v}) == 2 for v in pairs.values()
        ),
        reciprocal_pairs=sum(
            len(v) == 2
            and v[1]["id"] in v[0].get("related_events", [])
            and v[0]["id"] in v[1].get("related_events", [])
            for v in pairs.values()
        ),
        equal_timestamp_pairs=sum(len({e["timestamp"] for e in v}) == 1 for v in pairs.values()),
    )
    rows = json.loads((bundle / "forecast_rows.json").read_bytes())
    a = audit(
        rows,
        json.loads((bundle / "baseline_predictions.json").read_bytes()),
        json.loads((bundle / "process_audits.json").read_bytes()),
        canonical,
        json.loads((bundle / "baseline_results.json").read_bytes()),
    )
    s = shrinkage_development([r for r in rows if r["match_id"] in DEVELOPMENT])
    s["development_rows_sha256"] = digest(
        encode([r for r in rows if r["match_id"] in DEVELOPMENT]).encode()
    )
    target = output / digest(encode(snapshots).encode()) / VERSION / implementation
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        for name, value in [("forensic", f), ("baseline_audit", a), ("development_shrinkage", s)]:
            (stage / f"{name}.json").write_text(encode(value))
        (stage / "REVIEW.md").write_text(markdown(f, a, s))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=implementation,
                    parent_bundle=str(bundle.resolve()),
                    parent_delivery=str(delivery.resolve()),
                    protected_inputs=snapshots,
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                    gate_changed=False,
                    acquisition_performed=False,
                )
            )
        )
        if any(digest(Path(p).read_bytes()) != h for p, h in snapshots.items()):
            raise ValueError("Protected inputs changed during review")
        if target.exists():
            if (
                target.is_symlink()
                or {p.name for p in target.iterdir()} != {p.name for p in stage.iterdir()}
                or any((target / p.name).read_bytes() != p.read_bytes() for p in stage.iterdir())
            ):
                raise ValueError("Immutable review changed")
        else:
            stage.rename(target)
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--delivery", type=Path, required=True)
    p.add_argument("--pipeline-revision", required=True)
    p.add_argument("--output", type=Path, default=Path("data/interim/temporal-review"))
    a = p.parse_args()
    folder = build(a.delivery, a.output, a.pipeline_revision)
    print(
        encode(
            dict(bundle=str(folder.resolve()), gate="BLOCKED", semantics="PROPOSED_NOT_ACCEPTED")
        )
    )


if __name__ == "__main__":
    main()
