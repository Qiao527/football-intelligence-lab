"""Run a local, nonrepresentative geometry feasibility check; not a value evaluation."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from probe_skillcorner_geometry import AUDIT, normalize_frame

from fil.research.support_change import support_change
from fil.research.tracking_replay import movement_candidate, tracking_window


def evaluate(raw: Path, manifest_path: Path, queue_path: Path) -> dict:
    """Preserve every local outcome and the source hashes for reproducibility."""
    qc = AUDIT(raw, manifest_path)
    if qc["status"] == "FAIL":
        raise ValueError("Source audit failed")
    manifest = json.loads(manifest_path.read_text())
    queue = json.loads(queue_path.read_text())
    match = str(manifest["match_id"])
    if (
        str(queue["match_id"]) != match
        or queue["source_revision"] != manifest["source_revision"]
        or queue["source_file_sha256"] != {r["name"]: r["sha256"] for r in manifest["files"]}
    ):
        raise ValueError("Review queue does not match source manifest")
    meta = json.loads((raw / f"{match}_match.json").read_text())
    with (raw / f"{match}_phases_of_play.csv").open(encoding="utf-8", newline="") as source:
        phases = list(csv.DictReader(source))
    teams = {p["id"]: p["team_id"] for p in meta["players"]}
    outcomes = []
    for item in queue["items"]:
        frames = tracking_window(
            raw / f"{match}_tracking_extrapolated.jsonl", item["frame_id"], item["period"]
        )
        for player in item["candidate_player_ids"]:
            team = teams[player]
            group = "home team" if team == meta["home_team"]["id"] else "away team"
            movement = movement_candidate(
                frames, player, team, group, teams, phases, item["frame_id"], item["period"]
            )
            row = {
                "period": item["period"],
                "center_frame": item["frame_id"],
                "player_id": player,
                "movement": movement,
                "geometry": None,
            }
            if movement["status"] == "candidate":
                endpoints = [
                    f
                    for f in frames
                    if f["frame"] in (movement["frame_ids"][0], movement["frame_ids"][-1])
                ]
                before, opponents_before, reason_before = normalize_frame(
                    endpoints[0], meta, phases
                )
                after, opponents_after, reason_after = normalize_frame(endpoints[1], meta, phases)
                if reason_before or reason_after or opponents_before != opponents_after:
                    row["geometry"] = {
                        "status": "insufficient_data",
                        "reason": reason_before or reason_after or "Opponents changed.",
                    }
                else:
                    row["geometry"] = support_change(before, after, opponents_before, movement)
            outcomes.append(row)
    counts = Counter((row["geometry"] or {"status": "not_evaluated"})["status"] for row in outcomes)
    return {
        "status": "EXPLORATORY_NOT_VALIDATED",
        "source_revision": manifest["source_revision"],
        "match_id": match,
        "file_sha256": queue["source_file_sha256"],
        "counts": dict(counts),
        "outcomes": outcomes,
        "limits": "Preselected examples; provider labels and detection have uncertainty. "
        "Geometry change is not an observed pass, tactical value, causality or model accuracy.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("queue", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.raw, args.manifest, args.queue)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "counts": result["counts"]}))


if __name__ == "__main__":
    main()
