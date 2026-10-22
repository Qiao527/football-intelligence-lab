"""Assemble a local, source-preserving 64-match corpus and metric quality inventory."""

import argparse
import json
import math
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from fil.ingestion.normalize import verify_dataset
from fil.research.accepted_corpus import PROPOSAL, policy, verify_gate, write_bundle
from fil.research.acquisition import REVISION, digest, scope, verify
from fil.research.integrity_review import verify_artifact
from fil.research.pilot import encode


def assemble(
    pilot: Path,
    development: Path,
    test: Path,
    config: Path,
    review: Path,
    gate: Path,
    output: Path,
    implementation: str,
) -> Path:
    c = json.loads(config.read_bytes())
    rawroot = Path("data/raw/statsbomb-corpus")
    verify_gate(gate, rawroot)
    original = Path(c["raw"])
    canonical = Path(c["canonical"])
    verify_dataset(original, canonical)
    original_review = Path(json.loads(review.read_bytes())["bundle"])
    verify_artifact(original_review)
    protected = {
        str(p.resolve()): digest(p.read_bytes()) for p in (pilot, development, test, config, gate)
    }
    reports = [Path(p) for p in json.loads(pilot.read_bytes())]
    for index in (development, test):
        data = json.loads(index.read_bytes())
        reports.extend(Path(p) for p in data["reports"])
        for batch in data["batches"]:
            p = Path(batch["proof"])
            if digest(p.read_bytes()) != batch["proof_sha256"]:
                raise ValueError("Independent batch proof changed")
            protected[str(p.resolve())] = digest(p.read_bytes())
    rows = []
    seen = set()
    players = defaultdict(set)
    for folder in reports:
        verify_artifact(folder)
        q = json.loads((folder / "quality.json").read_bytes())
        mid = q["match_id"]
        if mid in seen:
            raise ValueError("Duplicate corpus match")
        seen.add(mid)
        verify(rawroot / REVISION / str(mid), PROPOSAL)
        raw = rawroot / REVISION / str(mid)
        for p in [*folder.iterdir(), *raw.iterdir()]:
            protected[str(p.resolve())] = digest(p.read_bytes())
        source = json.loads((raw / f"{mid}.json.events").read_bytes())
        shot = [e for e in source if e["type"]["name"] == "Shot" and e["period"] < 5]
        missing = [e["id"] for e in shot if e["shot"].get("statsbomb_xg") is None]
        invalid = [
            e["id"]
            for e in shot
            if e["shot"].get("statsbomb_xg") is not None and not 0 <= e["shot"]["statsbomb_xg"] <= 1
        ]
        for p in q["roster"]:
            players[p["player_id"]].add(p["team_id"])
        rows.append(
            dict(
                match_id=mid,
                status=q["status"],
                material_failures=q["material_failures"],
                raw_event_count=q["raw_count"],
                source_manifest_sha256=q["source_manifest_sha256"],
                quality_path=str(folder.resolve()),
                quality_manifest_sha256=digest((folder / "manifest.json").read_bytes()),
                canonical_null_counts=q["canonical_null_counts"],
                unknown_types=q["unknown_types"],
                supplemental_semantics_review=q["supplemental_semantics_review"],
                metric_outcomes={
                    name: dict(support=value["support"], reasons=value["reasons"])
                    for name, value in q["metric_eligibility"].items()
                },
                label_support=q["label_support"],
                label_exclusions=q["label_exclusion_counts"],
                census_issues=(
                    q["metric_eligibility"]["recorded_census_envelope"].get("census") or {}
                ).get("issues"),
                source_xg=dict(
                    match_play_shots=len(shot),
                    known_sum=math.fsum(
                        e["shot"]["statsbomb_xg"] for e in shot if e["id"] not in missing
                    ),
                    missing_event_ids=missing,
                    invalid_event_ids=invalid,
                ),
            )
        )
    approved = scope(PROPOSAL)
    if seen != set(approved["pilot_new_match_ids"] + approved["expansion_new_match_ids"]):
        raise ValueError("Corpus must contain exactly the approved 63 new matches")
    conflicts = {str(p): sorted(t) for p, t in players.items() if len(t) > 1}
    if conflicts:
        raise ValueError("Cross-match provider player/team identity conflict")
    for p in [*canonical.iterdir(), *[p for p in original.rglob("*") if p.is_file()]]:
        protected[str(p.resolve())] = digest(p.read_bytes())
    old = next(
        r
        for r in json.loads((original_review / "eligibility.json").read_bytes())
        if r["match_id"] == 8658
    )
    inventory = dict(
        version="fil-accepted-worldcup-corpus-1",
        policy=policy(),
        source_revision=REVISION,
        match_count=64,
        new_match_count=63,
        original_event_count=sum(r["raw_event_count"] for r in rows) + 2978,
        source_record_quality_statuses=dict(Counter(r["status"] for r in rows)),
        matches=sorted(rows, key=lambda r: r["match_id"]),
        reference_match=dict(
            match_id=8658,
            events=2978,
            classification="development_exposed_only",
            eligibility=old["eligibility"],
            raw=str(original.resolve()),
        ),
        cross_match_player_team_conflicts=conflicts,
        official_minutes=None,
        per90_eligible=False,
        coverage="One men's World Cup (2018), 32 recurrent teams; not general-football validation",
        data_rights=(
            "local noncommercial; no redistribution, external AI, deployment or weights release"
        ),
    )
    target = output / "corpus" / implementation
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        with pq.ParquetWriter(
            stage / "canonical.parquet",
            pq.read_schema(canonical / "events.parquet"),
            compression="zstd",
        ) as writer:
            writer.write_table(pq.ParquetFile(canonical / "events.parquet").read())
            for folder in sorted(reports):
                writer.write_table(pq.read_table(folder / "canonical.parquet"))
        (stage / "quality.json").write_text(encode(inventory))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=inventory["version"],
                    implementation_sha=implementation,
                    policy=policy(),
                    protected_inputs=protected,
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                )
            )
        )
        if any(digest(Path(p).read_bytes()) != h for p, h in protected.items()):
            raise ValueError("Protected input changed")
        write_bundle(stage, target)
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("pilot", "development", "test", "config", "frozen-review", "gate"):
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--pipeline-revision", required=True)
    p.add_argument("--output", type=Path, default=Path("data/interim/accepted-corpus"))
    a = p.parse_args()
    result = assemble(
        a.pilot,
        a.development,
        a.test,
        a.config,
        a.frozen_review,
        a.gate,
        a.output,
        a.pipeline_revision,
    )
    print(encode(dict(bundle=str(result.resolve()))))


if __name__ == "__main__":
    main()
