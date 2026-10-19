"""Immutable clock artifact bundles bound to verified canonical and raw source inputs."""

import hashlib
import json
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from fil.ingestion.normalize import verify_dataset
from fil.time.clock import CLOCK_VERSION, ClockError, clock_report, derive_clock

_MEMBERS = {"clock_events.parquet", "quality.json", "manifest.json"}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def _input(raw: Path, canonical: Path, revision: str) -> tuple[pa.Table, dict, str]:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ClockError("Expected full clock implementation commit SHA")
    manifest = verify_dataset(raw, canonical)
    manifest_bytes = (canonical / "manifest.json").read_bytes()
    if json.loads(manifest_bytes) != manifest:
        raise ClockError("Canonical manifest changed after verification")
    data = canonical / "events.parquet"
    body = data.read_bytes()
    entry = manifest["files"]["events.parquet"]
    if len(body) != entry["size_bytes"] or hashlib.sha256(body).hexdigest() != entry["sha256"]:
        raise ClockError("Canonical data changed after verification")
    table = pq.ParquetFile(pa.BufferReader(body)).read()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    clocked, periods = derive_clock(table, revision, manifest_hash)
    return clocked, clock_report(clocked, periods), manifest_hash


def _manifest(
    folder: Path, table: pa.Table, revision: str, generated: str, canonical_hash: str
) -> dict:
    return {
        "artifact_version": 1,
        "clock_version": CLOCK_VERSION,
        "clock_pipeline_git_sha": revision,
        "canonical_manifest_sha256": canonical_hash,
        "source_manifest_sha256": table["source_manifest_sha256"][0].as_py(),
        "source_revision": table["source_revision"][0].as_py(),
        "match_id": table["match_id"][0].as_py(),
        "generated_at_utc": generated,
        "row_count": table.num_rows,
        "pyarrow_version": pa.__version__,
        "writer": {
            "version": "2.6",
            "compression": "zstd",
            "use_dictionary": False,
            "write_statistics": True,
            "row_group_size": 65536,
        },
        "files": {
            name: {"sha256": _hash(folder / name), "size_bytes": (folder / name).stat().st_size}
            for name in ("clock_events.parquet", "quality.json")
        },
        "rights_scope": "unchanged: local noncommercial research only; no redistribution",
    }


def verify_clock_artifact(raw: Path, canonical: Path, folder: Path) -> dict:
    """Reverify full upstream lineage, all clock/canonical cells, period QA and artifact hashes."""
    if folder.is_symlink() or not folder.is_dir():
        raise ClockError("Expected clock artifact directory")
    members = list(folder.iterdir())
    if {p.name for p in members} != _MEMBERS or any(
        p.is_symlink() or not p.is_file() for p in members
    ):
        raise ClockError("Missing, unexpected or symlink clock artifacts")
    manifest = json.loads((folder / "manifest.json").read_bytes())
    table, report, digest = _input(raw, canonical, manifest["clock_pipeline_git_sha"])
    actual = pq.ParquetFile(folder / "clock_events.parquet").read()
    if not table.equals(actual, check_metadata=True):
        raise ClockError("Clock table differs from recomputed upstream data")
    if (folder / "quality.json").read_bytes() != _json_bytes(report):
        raise ClockError("Clock QA differs from recomputed evidence")
    generated = manifest["generated_at_utc"]
    if datetime.fromisoformat(generated).utcoffset() != UTC.utcoffset(None):
        raise ClockError("Clock generation time must be UTC aware")
    if manifest != _manifest(folder, table, manifest["clock_pipeline_git_sha"], generated, digest):
        raise ClockError("Clock artifact manifest/hash mismatch")
    return manifest


def build_clock_artifact(raw: Path, canonical: Path, output: Path, revision: str) -> Path:
    """Build into a separate directory or verify/reuse without writing existing inputs/outputs."""
    if any(output.resolve().is_relative_to(p.resolve()) for p in (raw, canonical)):
        raise ClockError("Clock output cannot be inside immutable input bundles")
    table, report, digest = _input(raw, canonical, revision)
    folder = output / f"match_id={table['match_id'][0].as_py()}" / digest / CLOCK_VERSION / revision
    if folder.exists() or folder.is_symlink():
        verify_clock_artifact(raw, canonical, folder)
        return folder
    # A nonempty target is never replaced; rename failure leaves original artifacts intact.
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fil-clock-", dir=folder.parent) as staging:
        candidate = Path(staging) / "bundle"
        candidate.mkdir()
        pq.write_table(
            table,
            candidate / "clock_events.parquet",
            compression="zstd",
            version="2.6",
            use_dictionary=False,
            write_statistics=True,
            row_group_size=65536,
        )
        (candidate / "quality.json").write_bytes(_json_bytes(report))
        (candidate / "manifest.json").write_bytes(
            _json_bytes(
                _manifest(
                    candidate,
                    table,
                    revision,
                    datetime.now(UTC).isoformat(),
                    digest,
                )
            )
        )
        verify_clock_artifact(raw, canonical, candidate)
        candidate.rename(folder)
    return folder
