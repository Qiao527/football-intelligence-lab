"""Local approved pilot corpus: all canonical records, eligible analysis separately."""

import argparse
import json
import re
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from fil.explorer.data import load_match
from fil.ingestion.player_roster import load_roster
from fil.research.acquisition import PROPOSAL_SHA256, REVISION, digest, scope, verify
from fil.research.baselines import examples, run
from fil.research.corpus import AUTHORISED, MatchEvidence, assemble
from fil.research.pilot import encode
from fil.schema import EVENT_SCHEMA

VERSION = "fil-worldcup-audited-corpus-1"


def build(
    reports: list[Path],
    raw_root: Path,
    proposal: Path,
    original_config: dict,
    output: Path,
    implementation: str,
) -> Path:
    if not re.fullmatch("[0-9a-f]{40}", implementation):
        raise ValueError("Full implementation SHA required")
    # Output must not be an input descendant; immutable source trees stay unchanged.
    inputs = [
        raw_root,
        *reports,
        *[Path(original_config[k]) for k in ("raw", "canonical", "clock", "score")],
    ]
    if any(output.resolve().is_relative_to(p.resolve()) for p in inputs):
        raise ValueError("Output must be outside immutable inputs")
    old, old_meta = load_match(original_config)
    roster = load_roster(Path(original_config["raw"]), 8658, old_meta["source_manifest_sha256"])
    valid = [MatchEvidence(old, old_meta, roster)]
    canonical = [pa.Table.from_arrays([old[n] for n in EVENT_SCHEMA.names], schema=EVENT_SCHEMA)]
    authorisations = set(AUTHORISED)
    process_audits = []
    report_rows = []
    rows = []
    metadata = []
    fingerprints = []
    for folder in reports:
        if folder.is_symlink():
            raise ValueError("Symlink pilot artifact")
        manifest = json.loads((folder / "manifest.json").read_bytes())
        if set(manifest["files"]) | {"manifest.json"} != {p.name for p in folder.iterdir()}:
            raise ValueError("Unexpected pilot members")
        for name, sha in manifest["files"].items():
            p = folder / name
            if p.is_symlink() or digest(p.read_bytes()) != sha:
                raise ValueError("Pilot artifact changed")
        q = json.loads((folder / "quality.json").read_bytes())
        mid = q["match_id"]
        raw_folder = raw_root / REVISION / str(mid)
        verify(raw_folder, proposal)
        if digest((raw_folder / "manifest.json").read_bytes()) != q["source_manifest_sha256"]:
            raise ValueError("Pilot source differs")
        if q["reference"]["manifest_sha256"] != old_meta["source_manifest_sha256"]:
            raise ValueError("Reference source differs")
        fingerprints.append(digest((folder / "manifest.json").read_bytes()))
        canonical.append(pq.ParquetFile(folder / "canonical.parquet").read())
        report_rows.append(q)
        if q["material_failures"]:
            continue
        e = pq.ParquetFile(folder / "events.parquet").read()
        match_meta = dict(
            source="statsbomb_open_data",
            match_id=mid,
            match_date=q["match_date"],
            source_manifest_sha256=q["source_manifest_sha256"],
            team_ids=sorted({r["team_id"] for r in q["roster"]}),
            player_ids=sorted({r["player_id"] for r in q["roster"]}),
        )
        valid.append(MatchEvidence(e, match_meta, q["roster"]))
        metadata.append(match_meta)
        authorisations.add(("statsbomb_open_data", mid, q["source_manifest_sha256"]))
        process_audits.append(json.loads((folder / "process.json").read_bytes()))
        rows.extend(
            examples(
                e,
                json.loads((folder / "process.json").read_bytes()),
                q["original_match_metadata"]["home_team"]["home_team_id"],
            )
        )
    if len(report_rows) != 6 or {r["match_id"] for r in report_rows} != set(
        scope(proposal)["pilot_new_match_ids"]
    ):
        raise ValueError("Expected six distinct pilot reports")
    canonical_all = pa.concat_tables(canonical)
    validated, quality = assemble(valid, authorisations=authorisations)
    if quality["identity_conflicts"]:
        raise ValueError("Cross-match identity conflict")
    baseline, predictions = run(rows, metadata)
    protocol = Path("docs/research/WORLDCUP_PILOT_PROTOCOL.md")
    content = digest(
        encode(
            sorted(fingerprints)
            + [old_meta["source_manifest_sha256"], digest(protocol.read_bytes())]
        ).encode()
    )
    target = output / content / VERSION / implementation
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        pq.write_table(canonical_all, stage / "canonical_all_matches.parquet", compression="zstd")
        pq.write_table(validated, stage / "validated_score_events.parquet", compression="zstd")
        for name, value in [
            ("corpus", quality),
            ("pilot_quality", report_rows),
            ("forecast_rows", rows),
            ("process_audits", process_audits),
            ("baseline_results", baseline),
            ("baseline_predictions", predictions),
        ]:
            (stage / f"{name}.json").write_text(encode(value))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=implementation,
                    proposal_sha256=PROPOSAL_SHA256,
                    protocol_sha256=digest(protocol.read_bytes()),
                    source_revision=REVISION,
                    rights_review=report_rows[0]["reference"]["rights_review"],
                    input_pilot_manifests=fingerprints,
                    original_source_manifest_sha256=old_meta["source_manifest_sha256"],
                    canonical_match_count=7,
                    canonical_events=canonical_all.num_rows,
                    validated_match_count=quality["match_count"],
                    validated_events=validated.num_rows,
                    blocked_match_ids=[
                        r["match_id"] for r in report_rows if r["material_failures"]
                    ],
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                    rights=(
                        "unchanged local approved noncommercial scope; no redistribution or xT/VAEP"
                    ),
                )
            )
        )
        if target.exists():
            if (
                target.is_symlink()
                or {p.name for p in target.iterdir()} != {p.name for p in stage.iterdir()}
                or any(
                    (target / p.name).is_symlink()
                    or (target / p.name).read_bytes() != p.read_bytes()
                    for p in stage.iterdir()
                )
            ):
                raise ValueError("Immutable research corpus changed")
        else:
            stage.rename(target)
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--reports",
        type=Path,
        required=True,
        help="Local JSON list of six audited pilot directories",
    )
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--raw-root", type=Path, default=Path("data/raw/statsbomb-corpus"))
    p.add_argument("--output", type=Path, default=Path("data/interim/worldcup-corpus"))
    p.add_argument(
        "--proposal", type=Path, default=Path("docs/research/statsbomb_corpus_proposal.json")
    )
    p.add_argument("--pipeline-revision", required=True)
    a = p.parse_args()
    folder = build(
        [Path(r) for r in json.loads(a.reports.read_bytes())],
        a.raw_root,
        a.proposal,
        json.loads(a.config.read_bytes()),
        a.output,
        a.pipeline_revision,
    )
    print(encode(dict(bundle=str(folder.resolve()), status="audited_pilot_corpus_built")))


if __name__ == "__main__":
    main()
