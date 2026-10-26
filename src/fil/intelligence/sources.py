"""Offline adapters for self-authored demos and owner-authorized local sources.

No download, upload, arbitrary match acquisition or runtime network code. Library
paths are operator configuration, never accepted from a browser text field.
"""

import hashlib
import json
from pathlib import Path

from fil.ingestion.statsbomb import PIN, verify_bundle
from fil.intelligence.demo import MATCHES, load_demo
from fil.research.accepted_corpus import PROPOSAL, policy
from fil.research.acquisition import REVISION, verify
from fil.research.integrity_review import verify_artifact

LIBRARY_VERSION = "fil-local-match-library-1"
METADATA = "data/matches/43/3.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inventory(library: dict) -> tuple[dict, list[dict]]:
    if library.get("version") != LIBRARY_VERSION or library.get("source_revision") != REVISION:
        raise ValueError("Unsupported local library or source revision")
    for name, expected in library["bindings"].items():
        if Path(name).is_symlink() or sha(Path(name)) != expected:
            raise ValueError("Local library binding changed; no stale report reuse")
    corpus = Path(library["corpus"])
    manifest = json.loads((corpus / "manifest.json").read_bytes())
    quality = json.loads((corpus / "quality.json").read_bytes())
    if (
        sha(corpus / "quality.json") != manifest["files"]["quality.json"]
        or quality["policy"] != policy()
        or quality["source_revision"] != REVISION
        or quality["match_count"] != 64
    ):
        raise ValueError("Corpus identity or accepted policy mismatch")
    path = Path(library["reference"]) / METADATA
    expected = next(f["sha256"] for f in PIN["files"] if f["path"] == METADATA)
    if sha(path) != expected:
        raise ValueError("Original pinned match metadata changed")
    return quality, json.loads(path.read_bytes())


def prepare_library(corpus: Path, reference: Path, destination: Path) -> Path:
    """Bind an existing verified corpus; never acquire source data."""
    verify_artifact(corpus)
    verify_bundle(reference)
    obj = dict(
        version=LIBRARY_VERSION,
        corpus=str(corpus.resolve()),
        reference=str(reference.resolve()),
        source_revision=REVISION,
        bindings={
            str(p.resolve()): sha(p)
            for p in (
                corpus / "manifest.json",
                corpus / "quality.json",
                reference / "manifest.json",
            )
        },
    )
    _inventory(obj)
    body = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    if destination.exists():
        if destination.read_text() != body:
            raise ValueError("Refusing to overwrite a different local library")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x") as handle:
        handle.write(body)
    return destination


def catalog(library: dict | None = None) -> list[dict]:
    result = [
        dict(id=mid, title=f"{names[0]} vs {names[1]}", mode="synthetic", date="Fictional fixture")
        for mid, names in MATCHES.items()
    ]
    if library is None:
        return result
    quality, metadata = _inventory(library)
    allowed = {e["match_id"] for e in quality["matches"]} | {8658}
    for row in sorted(metadata, key=lambda r: (r["match_date"], r["match_id"])):
        if row["match_id"] in allowed:
            result.append(
                dict(
                    id=str(row["match_id"]),
                    mode="local",
                    title=f"{row['home_team']['home_team_name']} vs "
                    f"{row['away_team']['away_team_name']}",
                    date=row["match_date"],
                )
            )
    return result


def _paths(library: dict, match_id: int) -> tuple[Path | None, Path, dict]:
    quality, _ = _inventory(library)
    if match_id == 8658:
        return None, Path(library["reference"]), quality
    entry = next((r for r in quality["matches"] if r["match_id"] == match_id), None)
    if entry is None:
        raise ValueError("Match outside existing authorized corpus")
    for domain in ("source_identity", "event_order", "score"):
        if entry["metric_outcomes"][domain]["support"] != "fully_supported":
            raise ValueError("Required metric integrity gate not fully supported")
    folder = Path(entry["quality_path"])
    if sha(folder / "manifest.json") != entry["quality_manifest_sha256"]:
        raise ValueError("Quality bundle identity changed")
    detail = json.loads((folder / "quality.json").read_bytes())
    return folder, Path(detail["raw_manifest_path"]).parent, quality


def fingerprint(library: dict, match_id: int) -> str:
    """Hash actual bytes on every rerun, including cache hits; no mtime shortcuts.

    Cache reuse never skips content-change detection. Only selected-match outputs
    are used by analysis; the combined multi-match Parquet is not a runtime input.
    """
    folder, raw, _ = _paths(library, match_id)
    reference = Path(library["reference"])
    members = list(reference.rglob("*"))
    expected = {f["path"] for f in PIN["files"]} | {"manifest.json"}
    if (
        reference.is_symlink()
        or any(p.is_symlink() for p in members)
        or {str(p.relative_to(reference)) for p in members if p.is_file()} != expected
    ):
        raise ValueError("Reference source bundle membership changed")
    paths = {reference / f["path"] for f in PIN["files"]} | {reference / "manifest.json"}
    if folder is not None:
        for root in (folder, raw):
            members = list(root.iterdir())
            if root.is_symlink() or any(p.is_symlink() or not p.is_file() for p in members):
                raise ValueError("Selected source or quality bundle membership changed")
            paths.update(members)
    h = hashlib.sha256(json.dumps(library, sort_keys=True).encode())
    for path in sorted(paths):
        if path.is_symlink():
            raise ValueError("Symlink source or quality payload")
        h.update(str(path).encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def load_local(library: dict, match_id: int) -> tuple[list[dict], dict, dict]:
    """Reverify immutable hashes, selected canonical preservation, native order/score."""
    folder, raw, quality = _paths(library, match_id)
    reference = Path(library["reference"])
    verify_bundle(reference)
    _, metadata = _inventory(library)
    meta = next(m for m in metadata if m["match_id"] == match_id)
    if folder is None:
        path = raw / "data/events/8658.json"
        gates = {
            "source_identity": "fully_supported",
            "event_order": "fully_supported",
            "score": "fully_supported",
        }
    else:
        import pyarrow.parquet as pq

        verify_artifact(folder)
        verify(raw, PROPOSAL)
        path = raw / f"{match_id}.json.events"
        rows = (
            pq.ParquetFile(folder / "canonical.parquet")
            .read(columns=["source_record_json"])
            .to_pylist()
        )
        if [json.loads(r["source_record_json"]) for r in rows] != json.loads(path.read_bytes()):
            raise ValueError("Canonical original-record preservation failed")
        entry = next(r for r in quality["matches"] if r["match_id"] == match_id)
        if sha(raw / "manifest.json") != entry["source_manifest_sha256"]:
            raise ValueError("Raw manifest differs from accepted quality inventory")
        gates = {k: v["support"] for k, v in entry["metric_outcomes"].items()}
    events = json.loads(path.read_bytes())
    # Validate even when called outside the UI. Includes all records and own goals.
    from fil.intelligence.engine import validate

    validate(events, meta)
    return (
        events,
        meta,
        dict(
            mode="local",
            source="Hudl / StatsBomb Open Data",
            source_revision=REVISION,
            raw_sha256=sha(path),
            raw_path=str(path.resolve()),
            raw_manifest_sha256=sha(raw / "manifest.json"),
            quality_manifest_sha256=sha(folder / "manifest.json") if folder else None,
            metric_gates=gates,
            physical_time_certified=False,
            rights="Local noncommercial research only. No redistribution, public service, "
            "external AI upload or new model training. Provider terms still apply.",
        ),
    )


def load(match_id: str, library: dict | None = None) -> tuple[list[dict], dict, dict]:
    if match_id in MATCHES:
        return load_demo(match_id)
    if library is None:
        raise ValueError("Real matches require an explicitly configured local library")
    return load_local(library, int(match_id))
