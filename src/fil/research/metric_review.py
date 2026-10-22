"""Local diagnostic eligibility/label audit; no acquisition, model evaluation or gate edits."""

import argparse
import json
import re
import tempfile
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

from fil.ingestion.statsbomb import verify_bundle
from fil.research.acquisition import REVISION, digest, scope, verify
from fil.research.eligibility import assess
from fil.research.integrity_review import verify_artifact
from fil.research.pilot import encode
from fil.research.possession_target import label_segments, possession_weights
from fil.research.prospective import components, partition_plan

VERSION = "fil-metric-specific-review-1"


def build(review: Path, reference_raw: Path, output: Path, implementation: str) -> Path:
    """Verify held inputs; preserve all parent artifacts and emit a separate immutable bundle."""
    if not re.fullmatch("[0-9a-f]{40}", implementation):
        raise ValueError("Full implementation SHA required")
    parent = Path(json.loads(review.read_bytes())["bundle"])
    manifest = verify_artifact(parent)
    protected = manifest["protected_inputs"].copy()
    for name, expected in protected.items():
        if digest(Path(name).read_bytes()) != expected:
            raise ValueError("Historical protected input changed")
    for p in [review, *parent.iterdir(), *reference_raw.rglob("*")]:
        if p.is_file():
            protected[str(p.resolve())] = digest(p.read_bytes())
    protocol = Path("docs/research/PROSPECTIVE_PROTOCOL.md")
    proposal = Path("docs/research/statsbomb_corpus_proposal.json")
    for p in [protocol, proposal]:
        protected[str(p.resolve())] = digest(p.read_bytes())
    if any(output.resolve().is_relative_to(Path(p).resolve()) for p in protected) or any(
        output.resolve().is_relative_to(p.resolve())
        for p in (parent, Path(manifest["parent_bundle"]), reference_raw, Path("data/raw"))
    ):
        raise ValueError("Output cannot overlap immutable source/parent inputs")
    approved = scope(proposal)
    verify_bundle(reference_raw)
    metadata_file = reference_raw / "data/matches/43/3.json"
    if digest(metadata_file.read_bytes()) != approved["metadata_source_sha256"]:
        raise ValueError("Original match metadata changed")
    metadata = json.loads(metadata_file.read_bytes())
    corpus = Path(manifest["parent_bundle"])
    canonical = pq.read_table(corpus / "canonical_all_matches.parquet").to_pylist()
    quality = json.loads((corpus / "pilot_quality.json").read_bytes())
    rawroot = Path("data/raw/statsbomb-corpus") / REVISION
    matrices, labels = [], []
    for mid in [*approved["pilot_new_match_ids"], 8658]:
        meta = next(m for m in metadata if m["match_id"] == mid)
        if mid == 8658:
            body = (reference_raw / "data/events/8658.json").read_bytes()
            lineups = json.loads((reference_raw / "data/lineups/8658.json").read_bytes())
            source_hash = digest((reference_raw / "manifest.json").read_bytes())
            expected = digest(body)  # verify_bundle independently checks the manifest-bound bytes.
        else:
            source = verify(rawroot / str(mid), proposal)
            body = (rawroot / str(mid) / f"{mid}.json.events").read_bytes()
            expected = source["files"][f"data/events/{mid}.json"]["sha256"]
            lineups = json.loads((rawroot / str(mid) / f"{mid}.json.lineups").read_bytes())
            source_hash = digest((rawroot / str(mid) / "manifest.json").read_bytes())
        roster = [
            dict(team_id=t["team_id"], player_id=p["player_id"])
            for t in lineups
            for p in t["lineup"]
        ]
        m = assess(
            body,
            expected,
            [r for r in canonical if r["match_id"] == mid],
            meta,
            roster,
            source_manifest_sha256=source_hash,
        )
        matrices.append(m)
        # This is exposed-source label QA only. Never predict or score this new target here.
        labels.extend(label_segments(json.loads(body), source_hash, mid))
    labels = possession_weights(labels)
    plan = partition_plan(approved, metadata)
    future = [
        dict(source="statsbomb_open_data", player_ids=None, **m)
        for part in plan["partitions"].values()
        for m in part
    ]
    plan["metadata_only_dependence"] = components(future)
    if any((rawroot / str(mid)).exists() for mid in approved["expansion_new_match_ids"]):
        raise ValueError("Review expects the 57 event payloads to remain unacquired")
    summary = dict(
        version=VERSION,
        label_audit_status="development_exposed_source_reconciliation_only",
        predictive_evaluation_performed=False,
        per_match=[
            dict(
                match_id=mid,
                states=dict(
                    Counter(r["observation_state"] for r in labels if r["match_id"] == mid)
                ),
            )
            for mid in sorted({r["match_id"] for r in labels})
        ],
        historical_pilot_status={r["match_id"]: r["status"] for r in quality},
        proposed_support_for_8656=next(m["eligibility"] for m in matrices if m["match_id"] == 8656),
        frozen_future_partition_counts={p: len(m) for p, m in plan["partitions"].items()},
        expansion_gate="BLOCKED",
        expansion_authorized=False,
    )
    folder = output / digest(encode(protected).encode()) / VERSION / implementation
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=folder.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        for name, value in [
            ("eligibility", matrices),
            ("labels", labels),
            ("future_partitions", plan),
            ("summary", summary),
        ]:
            (stage / f"{name}.json").write_text(encode(value))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=implementation,
                    parent_review=str(parent.resolve()),
                    protected_inputs=protected,
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                    expansion_gate="BLOCKED",
                    acquisition_performed=False,
                    gate_changed=False,
                    predictive_evaluation_performed=False,
                )
            )
        )
        if any(digest(Path(p).read_bytes()) != h for p, h in protected.items()):
            raise ValueError("Protected historical artifacts changed during review")
        if folder.exists():
            verify_artifact(folder)
            if {p.name for p in folder.iterdir()} != {p.name for p in stage.iterdir()} or any(
                (folder / p.name).read_bytes() != p.read_bytes() for p in stage.iterdir()
            ):
                raise ValueError("Immutable review output changed")
        else:
            stage.rename(folder)
    return folder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-review", required=True, type=Path)
    parser.add_argument("--reference-raw", required=True, type=Path)
    parser.add_argument("--pipeline-revision", required=True)
    parser.add_argument("--output", type=Path, default=Path("data/interim/metric-review"))
    args = parser.parse_args()
    folder = build(args.parent_review, args.reference_raw, args.output, args.pipeline_revision)
    print(encode(dict(bundle=str(folder.resolve()), gate="BLOCKED", proposal_accepted=False)))


if __name__ == "__main__":
    main()
