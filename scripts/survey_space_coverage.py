"""Systematic local source-coverage survey; not an accuracy or tactical-value study."""

import argparse
import csv
import hashlib
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any

from probe_skillcorner_geometry import normalize_frame

from fil.research.support_change import support_change
from fil.research.tracking_replay import movement_candidate


def sampled_windows(frames: Any, interval: int = 600) -> Any:
    """Yield fixed-interval source frames and their preceding 2 Hz samples."""
    if interval <= 0 or interval % 5:
        raise ValueError("Sampling interval must be a positive multiple of five source frames")
    window: deque[dict] = deque(maxlen=5)
    for frame in frames:
        index = frame["frame"]
        if index % 5:
            continue
        window.append(frame)
        if index % interval == 0:
            yield frame, list(window)


def survey_match(raw: Path, interim: Path) -> dict:
    """Recheck immutable source hashes and survey only previously audited WARN matches."""
    manifest = json.loads((interim / "source-manifest.json").read_text())
    qc = json.loads((interim / "source-quality.json").read_text())
    match = str(manifest["match_id"])
    if (
        qc["status"] != "WARN"
        or str(qc["match_id"]) != match
        or qc["source_revision"] != manifest["source_revision"]
    ):
        raise ValueError("Match did not have matching WARN source audit")
    for record in manifest["files"]:
        with (raw / record["name"]).open("rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() != record["sha256"]:
                raise ValueError(f"Source hash mismatch: {record['name']}")
    meta = json.loads((raw / f"{match}_match.json").read_text())
    with (raw / f"{match}_phases_of_play.csv").open(encoding="utf-8", newline="") as file:
        phases = list(csv.DictReader(file))
    teams = {p["id"]: p["team_id"] for p in meta["players"]}
    groups = {"home team": meta["home_team"]["id"], "away team": meta["away_team"]["id"]}
    windows: Counter[str] = Counter()
    outcomes = []
    with (raw / f"{match}_tracking_extrapolated.jsonl").open(encoding="utf-8") as file:
        source = (json.loads(line) for line in file)
        for frame, prior in sampled_windows(source):
            windows["sampled"] += 1
            possession = frame.get("possession") or {}
            group = possession.get("group")
            team = groups.get(group)
            carrier = possession.get("player_id")
            if team is None or teams.get(carrier) != team or frame.get("period") not in (1, 2):
                windows["possession_or_period_unavailable"] += 1
                continue
            targets = [
                p["player_id"]
                for p in frame.get("player_data", [])
                if p.get("is_detected") is True
                and p.get("player_id") != carrier
                and teams.get(p.get("player_id")) == team
            ]
            if len(set(targets)) != len(targets):
                windows["duplicate_target_identity"] += 1
                continue
            windows["with_eligible_target_list"] += 1
            for player in targets:
                movement = movement_candidate(
                    prior, player, team, group, teams, phases, frame["frame"], frame["period"]
                )
                row = {
                    "frame": frame["frame"],
                    "period": frame["period"],
                    "player_id": player,
                    "movement": movement,
                    "geometry": None,
                }
                if movement["status"] == "candidate":
                    a, oa, ra = normalize_frame(prior[0], meta, phases)
                    b, ob, rb = normalize_frame(prior[-1], meta, phases)
                    if ra or rb or oa != ob:
                        row["geometry"] = {
                            "status": "insufficient_data",
                            "reason": ra or rb or "Opponents changed.",
                        }
                    else:
                        row["geometry"] = support_change(a, b, oa, movement)
                outcomes.append(row)
    return {
        "match_id": match,
        "source_revision": manifest["source_revision"],
        "source_file_sha256": {r["name"]: r["sha256"] for r in manifest["files"]},
        "windows": dict(windows),
        "outcomes": outcomes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("interim_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    matches, excluded = [], []
    for path in sorted(args.interim_root.glob("*/source-manifest.json")):
        match = path.parent.name
        if not match.isdecimal():
            continue
        try:
            matches.append(survey_match(args.raw_root / match, path.parent))
            print(f"{match}: surveyed", flush=True)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            excluded.append({"match_id": match, "reason": str(exc)})
            print(f"{match}: excluded: {exc}", flush=True)
    result = {
        "status": "EXPLORATORY_NOT_VALIDATED",
        "method": "Source frame divisible by 600 (10 Hz); focus candidates are detected teammates "
        "of a known provider carrier at the center, excluding the carrier.",
        "limits": "Nonrandom time sample conditioned on provider possession and center "
        "detection. Not accuracy, representativeness, causal value or a population rate.",
        "matches": matches,
        "excluded": excluded,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Completed {len(matches)} matches, excluded {len(excluded)}", flush=True)


if __name__ == "__main__":
    main()
