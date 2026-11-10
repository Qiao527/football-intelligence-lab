"""Immutable, offline score artifact chained to raw, canonical and clock manifests."""

import hashlib
import json
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from fil.ingestion.statsbomb_score import official_score, scoring_signals
from fil.metrics.score import SCORE_VERSION, ScoreError, reconstruct_score
from fil.time.artifacts import verify_clock_artifact

_MEMBERS = {"score_events.parquet", "decisions.parquet", "quality.json", "manifest.json"}


def _json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _checked(folder: Path, name: str, entry: dict) -> bytes:
    body = (folder / name).read_bytes()
    if len(body) != entry["size_bytes"] or _digest(body) != entry["sha256"]:
        raise ScoreError(f"Input changed after verification: {name}")
    return body


def _input(raw: Path, canonical: Path, clock: Path, revision: str) -> tuple:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ScoreError("Expected full score implementation SHA")
    verified = verify_clock_artifact(raw, canonical, clock)
    manifest_bytes = (clock / "manifest.json").read_bytes()
    if json.loads(manifest_bytes) != verified:
        raise ScoreError("Clock manifest changed after verification")
    body = _checked(clock, "clock_events.parquet", verified["files"]["clock_events.parquet"])
    table = pq.ParquetFile(pa.BufferReader(body)).read()
    source_bytes = (raw / "manifest.json").read_bytes()
    if _digest(source_bytes) != verified["source_manifest_sha256"]:
        raise ScoreError("Source manifest changed after verification")
    source = json.loads(source_bytes)
    entries = {e["path"]: e for e in source["files"]}
    event_paths = set(table["raw_event_path"].to_pylist())
    if len(event_paths) != 1:
        raise ScoreError("Expected one raw event file")
    event_path = event_paths.pop()
    events = json.loads(_checked(raw, event_path, entries[event_path]))
    # Select metadata by the verified source identity, not by inferred team names/paths.
    identity = source["quality"]["identity"]
    metadata_path = f"data/matches/{identity['competition_id']}/{identity['season_id']}.json"
    matches = json.loads(_checked(raw, metadata_path, entries[metadata_path]))
    rows = table.select(["source_record_json"]).to_pylist()
    if len(events) != len(rows) or any(
        json.loads(r["source_record_json"]) != e for r, e in zip(rows, events, strict=True)
    ):
        raise ScoreError("Raw/clock source records differ")
    digest = _digest(manifest_bytes)
    states, decisions, report = reconstruct_score(
        table,
        scoring_signals(events),
        official_score(matches, identity["match_id"]),
        revision,
        digest,
    )
    report["official_metadata"] = {
        "path": metadata_path,
        "sha256": entries[metadata_path]["sha256"],
        "source_url": entries[metadata_path]["source_url"],
        "match_id": identity["match_id"],
    }
    report["source_events_sha256"] = entries[event_path]["sha256"]
    return states, decisions, report, digest


def _manifest(
    folder: Path, states: pa.Table, decisions: pa.Table, revision: str, generated: str, digest: str
) -> dict:
    return {
        "artifact_version": 1,
        "score_version": SCORE_VERSION,
        "score_pipeline_git_sha": revision,
        "clock_manifest_sha256": digest,
        "source_manifest_sha256": states["source_manifest_sha256"][0].as_py(),
        "canonical_manifest_sha256": states["canonical_manifest_sha256"][0].as_py(),
        "match_id": states["match_id"][0].as_py(),
        "generated_at_utc": generated,
        "row_count": states.num_rows,
        "decision_count": decisions.num_rows,
        "pyarrow_version": pa.__version__,
        "writer": {
            "version": "2.6",
            "compression": "zstd",
            "use_dictionary": False,
            "write_statistics": True,
            "row_group_size": 65536,
        },
        "files": {
            name: {
                "sha256": _digest((folder / name).read_bytes()),
                "size_bytes": (folder / name).stat().st_size,
            }
            for name in sorted(_MEMBERS - {"manifest.json"})
        },
        "rights_scope": "unchanged: local noncommercial research only; no redistribution",
    }


def verify_score_artifact(raw: Path, canonical: Path, clock: Path, folder: Path) -> dict:
    """Recompute every score state/decision, metadata reconciliation, QA and hash offline."""
    if folder.is_symlink() or not folder.is_dir():
        raise ScoreError("Expected score artifact directory")
    members = list(folder.iterdir())
    if {p.name for p in members} != _MEMBERS or any(
        p.is_symlink() or not p.is_file() for p in members
    ):
        raise ScoreError("Missing, unexpected or symlink score artifacts")
    manifest = json.loads((folder / "manifest.json").read_bytes())
    states, decisions, report, digest = _input(
        raw, canonical, clock, manifest["score_pipeline_git_sha"]
    )
    for name, expected in (("score_events.parquet", states), ("decisions.parquet", decisions)):
        actual = pq.ParquetFile(folder / name).read()
        if not actual.equals(expected, check_metadata=True):
            raise ScoreError(f"Recomputed score table differs: {name}")
    if (folder / "quality.json").read_bytes() != _json(report):
        raise ScoreError("Recomputed score QA differs")
    generated = manifest["generated_at_utc"]
    if datetime.fromisoformat(generated).utcoffset() != UTC.utcoffset(None):
        raise ScoreError("Score timestamp must be UTC aware")
    if manifest != _manifest(
        folder, states, decisions, manifest["score_pipeline_git_sha"], generated, digest
    ):
        raise ScoreError("Score manifest/hash mismatch")
    return manifest


def build_score_artifact(
    raw: Path, canonical: Path, clock: Path, output: Path, revision: str
) -> Path:
    """Stage, verify and atomically publish only a reconciled local bundle; reuse unchanged."""
    if any(output.resolve().is_relative_to(p.resolve()) for p in (raw, canonical, clock)):
        raise ScoreError("Score output cannot be inside immutable inputs")
    states, decisions, report, digest = _input(raw, canonical, clock, revision)
    folder = output / f"match_id={report['match_id']}" / digest / SCORE_VERSION / revision
    if folder.exists() or folder.is_symlink():
        verify_score_artifact(raw, canonical, clock, folder)
        return folder
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fil-score-", dir=folder.parent) as staging:
        candidate = Path(staging) / "bundle"
        candidate.mkdir()
        for name, table in (("score_events.parquet", states), ("decisions.parquet", decisions)):
            pq.write_table(
                table,
                candidate / name,
                compression="zstd",
                version="2.6",
                use_dictionary=False,
                write_statistics=True,
                row_group_size=65536,
            )
        (candidate / "quality.json").write_bytes(_json(report))
        (candidate / "manifest.json").write_bytes(
            _json(
                _manifest(
                    candidate, states, decisions, revision, datetime.now(UTC).isoformat(), digest
                )
            )
        )
        verify_score_artifact(raw, canonical, clock, candidate)
        candidate.rename(folder)
    return folder
