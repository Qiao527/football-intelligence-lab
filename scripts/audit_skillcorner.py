"""Read-only audit of one pinned SkillCorner source bundle; no normalization or modeling."""

import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def audit(raw_dir: Path, manifest_path: Path) -> dict[str, Any]:
    """Verify source bytes and report provider IDs, frame coverage and unresolved provenance."""
    manifest = json.loads(manifest_path.read_text())
    match = manifest["match_id"]
    if not isinstance(match, str) or not match.isdecimal():
        raise ValueError("Invalid source match ID")
    names = {
        f"{match}_{suffix}"
        for suffix in (
            "match.json",
            "tracking_extrapolated.jsonl",
            "dynamic_events.csv",
            "phases_of_play.csv",
        )
    }
    records = manifest["files"]
    if len(records) != 4 or {r["name"] for r in records} != names:
        raise ValueError("Unexpected source manifest files")
    for record in records:
        digest = hashlib.sha256()
        with (raw_dir / record["name"]).open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != record["sha256"]:
            raise ValueError(f"Source SHA-256 mismatch: {record['name']}")
    meta = json.loads((raw_dir / f"{match}_match.json").read_text())
    if str(meta["id"]) != match:
        raise ValueError("Manifest and source match IDs differ")
    players = meta["players"]
    player_ids = [p["id"] for p in players]
    if len(player_ids) != len(set(player_ids)):
        raise ValueError("Duplicate source player ID")
    team_ids = [meta["home_team"]["id"], meta["away_team"]["id"]]
    if len(set(team_ids)) != 2 or any(p["team_id"] not in team_ids for p in players):
        raise ValueError("Inconsistent source team IDs")
    # Source docs have not established whether player goal counts include own goals.
    # Do not infer own-goal attribution from ambiguous aggregate fields.
    own_goals = sum(p["own_goal"] for p in players)
    score_by_meta = (
        None
        if own_goals
        else [sum(p["goal"] for p in players if p["team_id"] == team) for team in team_ids]
    )
    official_score = [meta["home_team_score"], meta["away_team_score"]]

    frames: dict[int, int | None] = {}
    frame_keys: collections.Counter[str] = collections.Counter()
    frame_types: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    detection: collections.Counter[str] = collections.Counter()
    ball_detection: collections.Counter[str] = collections.Counter()
    unknown_players: collections.Counter[int] = collections.Counter()
    periods: collections.Counter[str] = collections.Counter()
    previous = -1
    with (raw_dir / f"{match}_tracking_extrapolated.jsonl").open() as f:
        for line in f:
            frame = json.loads(line)
            if not isinstance(frame, dict):
                raise ValueError("Invalid frame object")
            for key, value in frame.items():
                frame_keys[key] += 1
                frame_types[key][type(value).__name__] += 1
            if not {"frame", "period", "timestamp", "ball_data", "player_data"} <= set(frame):
                raise ValueError("Missing required tracking fields")
            idx = frame["frame"]
            if type(idx) is not int or idx <= previous:
                raise ValueError("Frame IDs are duplicated or not increasing")
            previous = idx
            period = frame["period"]
            if period not in (None, 1, 2):
                raise ValueError("Unexpected period")
            frames[idx] = period
            periods[str(period)] += 1
            if not isinstance(frame["ball_data"], dict) or not isinstance(
                frame["player_data"], list
            ):
                raise ValueError("Invalid frame contents")
            ball_detection[str(frame["ball_data"].get("is_detected"))] += 1
            seen = set()
            for player in frame["player_data"]:
                pid = player["player_id"]
                if type(pid) is not int or pid in seen:
                    raise ValueError("Missing or duplicate tracked player ID")
                seen.add(pid)
                if pid not in player_ids:
                    unknown_players[pid] += 1
                detection[str(player.get("is_detected"))] += 1
    if not frames:
        raise ValueError("Empty tracking file")

    events: dict[str, dict[str, str]] = {}
    kinds: collections.Counter[str] = collections.Counter()
    event_periods: collections.Counter[str] = collections.Counter()
    missing: collections.Counter[str] = collections.Counter()
    boundary_errors = 0
    with (raw_dir / f"{match}_dynamic_events.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        if not columns or not {
            "event_id",
            "match_id",
            "frame_start",
            "frame_end",
            "period",
            "event_type",
            "event_subtype",
            "player_id",
        } <= set(columns):
            raise ValueError("Missing required dynamic-event columns")
        for row in reader:
            event_id = row["event_id"]
            if not event_id or event_id in events or row["match_id"] != match:
                raise ValueError("Missing/duplicate event ID or match mismatch")
            events[event_id] = row
            for key, value in row.items():
                if value == "":
                    missing[key] += 1
            kinds[f"{row['event_type']}:{row['event_subtype']}"] += 1
            event_periods[row["period"]] += 1
            try:
                start, end, period = (
                    int(row["frame_start"]),
                    int(row["frame_end"]),
                    int(row["period"]),
                )
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid event frame or period") from exc
            if (
                start > end
                or start not in frames
                or end not in frames
                or (frames[start] != period or frames[end] != period)
            ):
                boundary_errors += 1
    if not events:
        raise ValueError("Empty dynamic-event file")
    missing_players = sum(
        bool(r["player_id"]) and int(r["player_id"]) not in player_ids for r in events.values()
    )
    links = [
        r["associated_player_possession_event_id"]
        for r in events.values()
        if r.get("associated_player_possession_event_id")
    ]
    missing_links = sum(link not in events for link in links)
    example = next((r for r in events.values() if r["event_type"] == "off_ball_run"), None)
    phase_ids = set()
    with (raw_dir / f"{match}_phases_of_play.csv").open(newline="", encoding="utf-8") as f:
        phases = csv.DictReader(f)
        if not phases.fieldnames or not {"index", "match_id", "period"} <= set(phases.fieldnames):
            raise ValueError("Missing required phase columns")
        for row in phases:
            if not row["index"] or row["index"] in phase_ids or row["match_id"] != match:
                raise ValueError("Missing/duplicate phase index or match mismatch")
            phase_ids.add(row["index"])
    warnings = [
        "Provider scores and scorer metadata are not independent event-level reconciliation.",
        "Provider dynamic events are derived labels; definition and validation are pending.",
        "Extrapolated or missing tracking positions are not treated as observed.",
        "This audit is not source normalization, research validation or causal evidence.",
    ]
    failures = []
    if score_by_meta is None:
        warnings.append(
            "Own-goal attribution requires provider documentation; score not reconciled."
        )
    elif score_by_meta != official_score:
        failures.append("Scorer metadata does not reconcile with source score")
    if unknown_players or missing_players:
        failures.append("Source references unknown player IDs")
    if boundary_errors:
        failures.append("Event boundary frames or periods do not match tracking")
    if missing_links:
        warnings.append("Some possession links do not resolve to a source dynamic event.")
    return {
        "status": "FAIL" if failures else "WARN",
        "failures": failures,
        "warnings": warnings,
        "source_revision": manifest["source_revision"],
        "match_id": meta["id"],
        "match_date": meta["date_time"],
        "home": meta["home_team"]["name"],
        "away": meta["away_team"]["name"],
        "source_score": official_score,
        "scorer_metadata_score": score_by_meta,
        "players": len(players),
        "tracking": {
            "raw_count": len(frames),
            "periods": dict(periods),
            "key_frequencies": dict(frame_keys),
            "key_types": {k: dict(v) for k, v in frame_types.items()},
            "player_detection_flags": dict(detection),
            "ball_detection_flags": dict(ball_detection),
            "unknown_player_occurrences": sum(unknown_players.values()),
        },
        "dynamic_events": {
            "raw_count": len(events),
            "columns": columns,
            "event_types": dict(kinds),
            "periods": dict(event_periods),
            "missing_by_column": dict(missing),
            "unknown_player_rows": missing_players,
            "invalid_frame_boundaries": boundary_errors,
            "possession_links": len(links),
            "unresolved_possession_links": missing_links,
        },
        "phases": {"raw_count": len(phase_ids)},
        "reverse_lookup_example": (
            {
                "event_id": example["event_id"],
                "period": example["period"],
                "player_id": example["player_id"],
                "frame_start": example["frame_start"],
                "frame_end": example["frame_end"],
            }
            if example
            else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_dir", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.raw_dir, args.manifest)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {k: result[k] for k in ("status", "failures", "warnings", "match_id")},
            ensure_ascii=False,
        )
    )
    if result["status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
