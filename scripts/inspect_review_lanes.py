"""Locally inspect review frames using detected positions and source hashes."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from fil.research.pass_lane import passing_line_observation, summarize_lane_timeline
from fil.time.clock import ClockError, parse_period_timestamp


def inspect(raw_root: Path, interim_root: Path) -> dict:
    """Measure review cases without consulting hidden rule or provider labels."""
    rows = []
    for queue_path in sorted(interim_root.glob("*/blind-review-queue.json")):
        queue = json.loads(queue_path.read_text())
        mid = queue_path.parent.name
        qc = json.loads((queue_path.parent / "source-quality.json").read_text())
        manifest = json.loads((queue_path.parent / "source-manifest.json").read_text())
        hashes = {r["name"]: r["sha256"] for r in manifest["files"]}
        if (
            queue["status"] != "NOT_REVIEWED"
            or qc["status"] != "WARN"
            or str(queue["match_id"]) != mid
            or str(qc["match_id"]) != mid
            or str(manifest["match_id"]) != mid
            or queue["source_file_sha256"] != hashes
            or queue["source_revision"] != manifest["source_revision"]
            or qc["source_revision"] != manifest["source_revision"]
        ):
            raise ValueError(f"Unverified source identity: {mid}")
        for name, digest in hashes.items():
            with (raw_root / mid / name).open("rb") as f:
                if hashlib.file_digest(f, "sha256").hexdigest() != digest:
                    raise ValueError(f"Source hash mismatch: {mid}/{name}")
        meta = json.loads((raw_root / mid / f"{mid}_match.json").read_text())
        if str(meta["id"]) != mid:
            raise ValueError(f"Metadata mismatch: {mid}")
        teams = {p["id"]: p["team_id"] for p in meta["players"]}
        with (raw_root / mid / f"{mid}_phases_of_play.csv").open(newline="", encoding="utf-8") as f:
            phases = list(csv.DictReader(f))
        wanted = {
            n
            for item in queue["items"]
            for n in range(item["frame_id"] - 20, item["frame_id"] + 1, 5)
        }
        found = {}
        with (raw_root / mid / f"{mid}_tracking_extrapolated.jsonl").open() as f:
            for line in f:
                frame = json.loads(line)
                if frame["frame"] in wanted:
                    found[frame["frame"]] = frame
        for item in queue["items"]:
            for target in item["candidate_player_ids"]:
                timeline = []
                for index in range(item["frame_id"] - 20, item["frame_id"] + 1, 5):
                    frame = found.get(index)
                    try:
                        valid_clock = (
                            frame is not None
                            and frame.get("period") == item["period"]
                            and parse_period_timestamp(frame.get("timestamp"))
                            == parse_period_timestamp(item["match_timestamp"])
                            - (item["frame_id"] - index) * 100
                        )
                    except ClockError:
                        valid_clock = False
                    if not valid_clock:
                        observation = {
                            "status": "insufficient_data",
                            "frame_id": index,
                            "reason": "Source frame identity or timestamp mismatch.",
                        }
                    else:
                        observation = passing_line_observation(
                            frame, teams, meta["home_team"]["id"], meta["away_team"]["id"], target
                        )
                    timeline.append(observation)
                rows.append(
                    {
                        "match_id": mid,
                        "frame": item["frame_id"],
                        "target_id": target,
                        "source_file_sha256": hashes,
                        "observation": timeline[-1],
                        "timeline": timeline,
                        "temporal_summary": summarize_lane_timeline(timeline, phases),
                    }
                )
    return {
        "status": "EXPLORATORY_NOT_VALIDATED",
        "rows": rows,
        "limits": "Five half-second samples ending at each selected frame; "
        "observed opponent proximity only. "
        "Player orientation is unavailable; missing defenders, speed, height and "
        "opponent reach prevent pass-feasibility or tactical-value conclusions. "
        "Cue-relative displacement is an observed timing, not cognitive reaction time.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("interim_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.raw_root, args.interim_root)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    counts = Counter()
    for row in result["rows"]:
        o = row["observation"]
        key = o["status"]
        if key == "observed_geometry":
            key += (
                ":near_detected_opponent"
                if o["near_segment_opponent_ids"]
                else ":none_detected_near"
            )
        counts[key] += 1
    print(json.dumps({"cases": len(result["rows"]), "counts": dict(counts)}))


if __name__ == "__main__":
    main()
