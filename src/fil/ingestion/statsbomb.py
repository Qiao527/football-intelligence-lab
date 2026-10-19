"""Acquire and independently verify one reviewed, pinned StatsBomb research fixture."""

import argparse
import hashlib
import json
import re
import tempfile
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
from uuid import UUID

ADAPTER_VERSION = "fil-source-1"
PIN = json.loads(files(__package__).joinpath("statsbomb_source.json").read_text())
Fetch = Callable[[str, int], bytes]


class AcquisitionError(ValueError):
    """Unavailable, changed, malformed or locally corrupted source bundle."""


def source_url(path: str, pin: dict[str, Any] = PIN) -> str:
    """Return the immutable official raw URL; no caller-supplied host is accepted."""
    return f"https://raw.githubusercontent.com/hudl/open-data/{pin['revision']}/{path}"


def download(url: str, max_bytes: int) -> bytes:
    """Bounded HTTPS fetch with default TLS verification and no redirected content."""
    try:
        with urlopen(url, timeout=30) as response:
            if response.status != 200 or response.geturl() != url:
                raise AcquisitionError(f"Unexpected HTTP status or redirect: {url}")
            body = response.read(max_bytes + 1)
    except (URLError, OSError) as exc:
        raise AcquisitionError(f"Source unavailable: {url}: {exc}") from exc
    if len(body) > max_bytes:
        raise AcquisitionError(f"Source exceeds size limit: {url}")
    return body


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise AcquisitionError(message)


def _json_records(body: bytes, name: str) -> list[dict[str, Any]]:
    try:
        value = json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise AcquisitionError(f"Invalid JSON: {name}") from exc
    _check(isinstance(value, list) and bool(value), f"Expected nonempty JSON array: {name}")
    _check(all(isinstance(row, dict) for row in value), f"Expected object rows: {name}")
    return value


def _unique_record(rows: list[dict[str, Any]], **keys: Any) -> dict[str, Any]:
    matches = [r for r in rows if all(r.get(k) == v for k, v in keys.items())]
    _check(len(matches) == 1, f"Expected exactly one metadata record matching {keys}")
    return matches[0]


def _inspect_sources(raw: dict[str, bytes], pin: dict[str, Any]) -> dict[str, Any]:
    for entry in pin["files"]:
        path = entry["path"]
        _check(path in raw, f"Missing source: {path}")
        body = raw[path]
        _check(len(body) == entry["size_bytes"], f"Size mismatch: {path}")
        _check(hashlib.sha256(body).hexdigest() == entry["sha256"], f"SHA-256 mismatch: {path}")
    _check(raw["LICENSE.pdf"].startswith(b"%PDF-"), "Invalid license PDF header")
    _check(bool(raw["README.md"].decode("utf-8").strip()), "Empty source README")
    expected = pin["match"]
    match_id = expected["match_id"]
    comp_id, season_id = expected["competition_id"], expected["season_id"]
    competition = _unique_record(
        _json_records(raw["data/competitions.json"], "competitions"),
        competition_id=comp_id,
        season_id=season_id,
    )
    match = _unique_record(
        _json_records(raw[f"data/matches/{comp_id}/{season_id}.json"], "matches"),
        match_id=match_id,
    )
    try:
        identity = {
            "match_id": match["match_id"],
            "competition_id": match["competition"]["competition_id"],
            "competition_name": match["competition"]["competition_name"],
            "season_id": match["season"]["season_id"],
            "season_name": match["season"]["season_name"],
            "match_date": match["match_date"],
            "home_team_id": match["home_team"]["home_team_id"],
            "home_team_name": match["home_team"]["home_team_name"],
            "away_team_id": match["away_team"]["away_team_id"],
            "away_team_name": match["away_team"]["away_team_name"],
            "competition_stage": match["competition_stage"]["name"],
        }
    except (KeyError, TypeError) as exc:
        raise AcquisitionError("Missing or invalid match metadata") from exc
    _check(identity == expected, "Match metadata does not match reviewed identity")
    for key in ("competition_name", "season_name"):
        _check(competition.get(key) == identity[key], f"Competition/metadata mismatch: {key}")
    events = _json_records(raw[f"data/events/{match_id}.json"], "events")
    ids: set[UUID] = set()
    types: Counter[str] = Counter()
    periods: Counter[int] = Counter()
    for event in events:
        event_id = event.get("id")
        try:
            _check(isinstance(event_id, str) and bool(event_id), "Missing event ID")
            parsed_id = UUID(event_id)
        except (ValueError, AttributeError) as exc:
            raise AcquisitionError("Missing or invalid event UUID") from exc
        _check(parsed_id not in ids, f"Duplicate event ID: {event_id}")
        ids.add(parsed_id)
        _check(type(event.get("index")) is int and event["index"] > 0, "Invalid event index")
        _check(type(event.get("period")) is int and 1 <= event["period"] <= 5, "Invalid period")
        _check(isinstance(event.get("timestamp"), str), "Missing event timestamp")
        _check(isinstance(event.get("type"), dict), "Missing event type")
        name = event["type"].get("name")
        _check(isinstance(name, str) and bool(name), "Missing event type name")
        types[name] += 1
        periods[event["period"]] += 1
    lineups = _json_records(raw[f"data/lineups/{match_id}.json"], "lineups")
    teams = {
        identity["home_team_id"]: identity["home_team_name"],
        identity["away_team_id"]: identity["away_team_name"],
    }
    _check(len(lineups) == 2, "Expected two lineup teams")
    _check({t.get("team_id") for t in lineups} == set(teams), "Lineup team IDs mismatch")
    for team in lineups:
        _check(team.get("team_name") == teams[team["team_id"]], "Lineup team name mismatch")
        _check(isinstance(team.get("lineup"), list) and bool(team["lineup"]), "Empty lineup")
    return {
        "identity": identity,
        "event_count_raw": len(events),
        "output_record_count": len(events),
        "unique_event_ids": len(ids),
        "duplicate_event_ids": 0,
        "event_type_counts": dict(sorted(types.items())),
        "top_level_key_counts": dict(sorted(Counter(k for e in events for k in e).items())),
        "period_counts": {str(k): v for k, v in sorted(periods.items())},
        "unknown_type_count": None,
        "nullable_counts": {
            key: sum(e.get(key) is None for e in events)
            for key in ("player", "location", "possession_team")
        },
        "sample_event_ids": [
            events[i]["id"] for i in sorted({0, len(events) // 2, len(events) - 1})
        ],
        "warnings": [
            "No normalization or full provider schema/type-enum audit performed.",
            "360/tracking not acquired or assumed available.",
            "Registration and research-use rights need owner confirmation; no redistribution.",
        ],
    }


def inspect_sources(raw: dict[str, bytes], pin: dict[str, Any] = PIN) -> dict[str, Any]:
    """Validate original bytes/identity and return QC facts without changing records."""
    try:
        return _inspect_sources(raw, pin)
    except (KeyError, TypeError, AttributeError, UnicodeError) as exc:
        raise AcquisitionError(f"Invalid provider structure: {exc}") from exc


def build_manifest(
    raw: dict[str, bytes],
    pipeline_revision: str,
    acquired_at: str,
    pin: dict[str, Any] = PIN,
) -> dict[str, Any]:
    """Create a deterministic manifest for fixed bytes, time and implementation revision."""
    _check(bool(re.fullmatch(r"[0-9a-f]{40}", pipeline_revision)), "Invalid pipeline commit SHA")
    try:
        timestamp = datetime.fromisoformat(acquired_at)
        _check(timestamp.utcoffset() == UTC.utcoffset(timestamp), "Timestamp must be UTC-aware")
    except (ValueError, TypeError) as exc:
        raise AcquisitionError("Invalid UTC acquisition timestamp") from exc
    qc = inspect_sources(raw, pin)
    return {
        "manifest_version": 1,
        "source": "statsbomb_open_data",
        "repository": pin["repository"],
        "upstream_revision": pin["revision"],
        "pipeline_git_sha": pipeline_revision,
        "acquisition_adapter_version": ADAPTER_VERSION,
        "normalizer_version": None,
        "metric_spec_version": None,
        "acquired_at_utc": acquired_at,
        "files": [
            {
                **entry,
                "source_url": source_url(entry["path"], pin),
                "final_url": source_url(entry["path"], pin),
            }
            for entry in pin["files"]
        ],
        "usage": {
            "provider": "StatsBomb",
            "scope": "noncommercial research only",
            "license_url": source_url("LICENSE.pdf", pin),
            "readme_url": source_url("README.md", pin),
            "attribution": "StatsBomb acknowledgement and brand logo for published analysis",
            "redistribution_approved": False,
            "registration": "owner confirmation required; LICENSE.pdf section 2.2",
            "assessment": "docs/SOURCE_POLICY.md",
        },
        "quality": qc,
        "source_integrity_status": "PASS",
        "rights_gate_status": "PENDING_OWNER_CONFIRMATION",
    }


def verify_bundle(bundle: Path, pin: dict[str, Any] = PIN) -> dict[str, Any]:
    """Offline verification against committed pins and a recomputed manifest."""
    try:
        expected_files = {e["path"] for e in pin["files"]} | {"manifest.json"}
        members = list(bundle.rglob("*"))
        _check(
            not bundle.is_symlink() and all(not p.is_symlink() for p in members),
            "Symlinks are not allowed in raw bundles",
        )
        _check(
            {str(p.relative_to(bundle)) for p in members if p.is_file()} == expected_files,
            "Missing or unexpected files in raw bundle",
        )
        manifest = json.loads((bundle / "manifest.json").read_bytes())
        raw = {e["path"]: (bundle / e["path"]).read_bytes() for e in pin["files"]}
        expected = build_manifest(
            raw, manifest["pipeline_git_sha"], manifest["acquired_at_utc"], pin
        )
        _check(manifest == expected, "Manifest does not match recomputed source facts")
        return expected
    except (OSError, KeyError, TypeError, UnicodeError) as exc:
        raise AcquisitionError(f"Invalid local bundle: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AcquisitionError("Invalid manifest JSON") from exc


def acquire(
    root: Path,
    pipeline_revision: str,
    *,
    fetch: Fetch = download,
    acquired_at: str | None = None,
    pin: dict[str, Any] = PIN,
) -> Path:
    """Atomically publish validated raw bytes, or verify and reuse an existing bundle."""
    bundle = root / str(pin["match"]["match_id"]) / pin["revision"]
    if bundle.exists() or bundle.is_symlink():
        verify_bundle(bundle, pin)
        return bundle
    try:
        raw = {
            entry["path"]: fetch(source_url(entry["path"], pin), entry["size_bytes"])
            for entry in pin["files"]
        }
    except OSError as exc:
        raise AcquisitionError(f"Source unavailable: {exc}") from exc
    manifest = build_manifest(
        raw,
        pipeline_revision,
        acquired_at or datetime.now(UTC).isoformat(),
        pin,
    )
    try:
        bundle.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".fil-acquire-", dir=bundle.parent) as staging:
            candidate = Path(staging) / "bundle"
            candidate.mkdir()
            for name, body in raw.items():
                destination = candidate / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(body)
            (candidate / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            verify_bundle(candidate, pin)
            candidate.rename(bundle)
    except OSError as exc:
        raise AcquisitionError(f"Cannot publish raw bundle (nothing overwritten): {exc}") from exc
    return bundle


def main(argv: list[str] | None = None) -> int:
    """CLI exit 0 on verified success, 1 on acquisition/integrity failure, 2 on usage error."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch_parser = sub.add_parser("acquire", help="Acquire pinned match 8658 for local research")
    fetch_parser.add_argument("--root", type=Path, default=Path("data/raw/statsbomb"))
    fetch_parser.add_argument("--pipeline-revision", required=True)
    check_parser = sub.add_parser("verify", help="Offline hash, metadata and manifest verification")
    check_parser.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)
    try:
        bundle = (
            acquire(args.root, args.pipeline_revision) if args.command == "acquire" else args.bundle
        )
        manifest = verify_bundle(bundle)
    except AcquisitionError as exc:
        parser.exit(1, f"Acquisition failed: {exc}\n")
    print(
        json.dumps(
            {
                "bundle": str(bundle),
                "manifest": str(bundle / "manifest.json"),
                "event_count_raw": manifest["quality"]["event_count_raw"],
                "source_integrity_status": manifest["source_integrity_status"],
                "rights_gate_status": manifest["rights_gate_status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
