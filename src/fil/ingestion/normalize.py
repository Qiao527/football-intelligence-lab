"""Offline, atomic canonical dataset rebuild, verification and exact source lookup."""

import argparse
import hashlib
import json
import re
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from fil.ingestion.statsbomb import AcquisitionError
from fil.ingestion.statsbomb import verify_bundle as verify_source_bundle
from fil.ingestion.statsbomb_adapter import NORMALIZER_VERSION, to_canonical
from fil.schema import SCHEMA_VERSION, SchemaError, SourceContext, validate_table

_FILES = {"events.parquet", "quality.json", "manifest.json"}


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _json(body: bytes) -> Any:
    def reject(value: str) -> None:
        raise SchemaError(f"Invalid JSON constant: {value}")

    def unique(pairs: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise SchemaError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(body, parse_constant=reject, object_pairs_hook=unique)


def _encode(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode()


def load_source(bundle: Path, pipeline_revision: str) -> tuple[pa.Table, SourceContext]:
    """Verify FIL-002 source bundle before projecting any event record."""
    if not re.fullmatch(r"[0-9a-f]{40}", pipeline_revision):
        raise SchemaError("Expected full FIL implementation commit SHA")
    manifest = verify_source_bundle(bundle)
    manifest_bytes = (bundle / "manifest.json").read_bytes()
    # Bind the verified manifest returned by FIL-002 to exactly the bytes referenced by rows.
    if _json(manifest_bytes) != manifest:
        raise SchemaError("Source manifest changed during verification")
    identity = manifest["quality"]["identity"]
    path = f"data/events/{identity['match_id']}.json"
    entry = next(e for e in manifest["files"] if e["path"] == path)
    raw = (bundle / path).read_bytes()
    if len(raw) != entry["size_bytes"] or _digest(raw) != entry["sha256"]:
        raise SchemaError("Source bytes changed after verification")
    context = SourceContext(
        source=manifest["source"],
        source_revision=entry["sha256"],
        upstream_revision=manifest["upstream_revision"],
        source_manifest_sha256=_digest(manifest_bytes),
        pipeline_git_sha=pipeline_revision,
        match_id=identity["match_id"],
        competition_id=identity["competition_id"],
        season_id=identity["season_id"],
        raw_event_path=path,
    )
    table = to_canonical(_json(raw), context)
    if table.num_rows != manifest["quality"]["event_count_raw"]:
        raise SchemaError("Raw/manifest/canonical count mismatch")
    return table, context


def quality_report(table: pa.Table, context: SourceContext) -> dict[str, Any]:
    """Report every column's null count and source/type reconciliation, without metrics."""
    return {
        "schema_version": SCHEMA_VERSION,
        "normalizer_version": NORMALIZER_VERSION,
        "source_manifest_sha256": context.source_manifest_sha256,
        "raw_count": table.num_rows,
        "processed_count": table.num_rows,
        "excluded_count": 0,
        "exclusions": [],
        "unique_event_ids": len(set(table["event_id"].to_pylist())),
        "null_counts": {name: table[name].null_count for name in table.column_names},
        "event_type_counts": dict(sorted(Counter(table["event_type"].to_pylist()).items())),
        "unrecognized_type_count": sum(bool(v) for v in table["quality_flags"].to_pylist()),
        "transformations": [
            "Project source-native fields to typed columns; widen numeric coordinates to float64.",
            "Keep provider order, IDs and timestamps; no row exclusions or coordinate flips.",
            "Encode complete source records as deterministic JSON; raw bytes remain immutable.",
            "Copy provider shot xG only; no xG/xT/clock/score calculations.",
        ],
        "warnings": [
            "Unrecognized event types are retained and flagged, never dropped.",
            "No chronological or period-elapsed clock reconstruction.",
            "No spatial-direction, score or metric gate is claimed.",
            "Derived provider records remain local; redistribution/commercial use unapproved.",
            "Historical source rights pending value; SOURCE_POLICY.md records owner attestation.",
        ],
        "source_traceability": "PASS",
        "count_reconciliation": "PASS",
    }


def _manifest(
    folder: Path,
    context: SourceContext,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "manifest_version": 1,
        "schema_version": SCHEMA_VERSION,
        "normalizer_version": NORMALIZER_VERSION,
        "pipeline_git_sha": context.pipeline_git_sha,
        "source": context.source,
        "match_id": context.match_id,
        "source_revision": context.source_revision,
        "upstream_revision": context.upstream_revision,
        "source_manifest_sha256": context.source_manifest_sha256,
        "source_manifest_path": "manifest.json (relative to supplied verified raw bundle)",
        "raw_event_path": context.raw_event_path,
        "generated_at_utc": generated_at,
        "pyarrow_version": pa.__version__,
        "writer": {
            "version": "2.6",
            "compression": "zstd",
            "use_dictionary": False,
            "row_group_size": 65536,
            "write_statistics": True,
        },
        "files": {
            name: {
                "sha256": _digest((folder / name).read_bytes()),
                "size_bytes": (folder / name).stat().st_size,
            }
            for name in ("events.parquet", "quality.json")
        },
        "rights_scope": "local noncommercial research only; no redistribution approval",
    }


def verify_dataset(raw_bundle: Path, dataset: Path) -> dict[str, Any]:
    """Recompute all rows from verified raw input and compare schema, values, report and hashes."""
    if dataset.is_symlink() or not dataset.is_dir():
        raise SchemaError("Expected real dataset directory")
    members = list(dataset.iterdir())
    if {p.name for p in members} != _FILES or any(
        p.is_symlink() or not p.is_file() for p in members
    ):
        raise SchemaError("Dataset has missing, unexpected or symlink files")
    manifest = _json((dataset / "manifest.json").read_bytes())
    expected, context = load_source(raw_bundle, manifest["pipeline_git_sha"])
    actual = pq.ParquetFile(dataset / "events.parquet").read()
    validate_table(actual)
    if not actual.equals(expected, check_metadata=True):
        raise SchemaError("Parquet rows differ from source-derived canonical records")
    if (dataset / "quality.json").read_bytes() != _encode(quality_report(expected, context)):
        raise SchemaError("Quality report differs from recomputed source facts")
    stamp = manifest["generated_at_utc"]
    if datetime.fromisoformat(stamp).utcoffset() != UTC.utcoffset(None):
        raise SchemaError("Expected aware UTC generation timestamp")
    if manifest != _manifest(dataset, context, stamp):
        raise SchemaError("Processed manifest/hash mismatch")
    return manifest


def build_dataset(raw_bundle: Path, output_root: Path, pipeline_revision: str) -> Path:
    """Atomically build a versioned bundle, or verify/reuse it without rewriting outputs."""
    if output_root.resolve().is_relative_to(raw_bundle.resolve()):
        raise SchemaError("Processed output must not be written inside the immutable raw bundle")
    table, context = load_source(raw_bundle, pipeline_revision)
    dataset = (
        output_root
        / f"match_id={context.match_id}"
        / context.source_manifest_sha256
        / NORMALIZER_VERSION
        / pipeline_revision
    )
    if dataset.exists() or dataset.is_symlink():
        verify_dataset(raw_bundle, dataset)
        return dataset
    dataset.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fil-normalize-", dir=dataset.parent) as staging:
        candidate = Path(staging) / "dataset"
        candidate.mkdir()
        pq.write_table(
            table,
            candidate / "events.parquet",
            compression="zstd",
            version="2.6",
            use_dictionary=False,
            write_statistics=True,
            row_group_size=65536,
        )
        (candidate / "quality.json").write_bytes(_encode(quality_report(table, context)))
        (candidate / "manifest.json").write_bytes(
            _encode(_manifest(candidate, context, datetime.now(UTC).isoformat()))
        )
        verify_dataset(raw_bundle, candidate)
        candidate.rename(dataset)
    return dataset


def lookup_event(raw_bundle: Path, dataset: Path, event_id: str) -> dict[str, Any]:
    """Resolve a verified canonical ID to the exact original record, without guessing."""
    manifest = verify_dataset(raw_bundle, dataset)
    table = pq.ParquetFile(dataset / "events.parquet").read()
    ids = table["event_id"].to_pylist()
    if event_id not in ids:
        raise SchemaError(f"Event ID not found: {event_id}")
    position = ids.index(event_id)
    raw = _json((raw_bundle / manifest["raw_event_path"]).read_bytes())
    record = raw[table["raw_event_row"][position].as_py()]
    if record["id"] != event_id or record != _json(table["source_record_json"][position].as_py()):
        raise SchemaError("Reverse lookup lineage mismatch")
    return record


def main(argv: list[str] | None = None) -> int:
    """Build/verify locally or print an original record; no network access."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--raw-bundle", type=Path, required=True)
    build.add_argument("--output-root", type=Path, default=Path("data/interim/events"))
    build.add_argument("--pipeline-revision", required=True)
    for name in ("verify", "lookup"):
        command = commands.add_parser(name)
        command.add_argument("--raw-bundle", type=Path, required=True)
        command.add_argument("--dataset", type=Path, required=True)
        if name == "lookup":
            command.add_argument("--event-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "lookup":
            print(
                json.dumps(
                    lookup_event(args.raw_bundle, args.dataset, args.event_id),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        dataset = (
            build_dataset(args.raw_bundle, args.output_root, args.pipeline_revision)
            if args.command == "build"
            else args.dataset
        )
        manifest = verify_dataset(args.raw_bundle, dataset)
        print(
            json.dumps(
                {
                    "dataset": str(dataset),
                    "status": "PASS",
                    "source_manifest_sha256": manifest["source_manifest_sha256"],
                    "quality_report": str(dataset / "quality.json"),
                },
                indent=2,
            )
        )
    except (
        SchemaError,
        AcquisitionError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        pa.ArrowException,
        StopIteration,
    ) as exc:
        parser.exit(1, f"Normalization failed (nothing overwritten): {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
