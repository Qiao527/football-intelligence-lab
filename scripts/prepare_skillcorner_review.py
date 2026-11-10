"""Prepare an unlabelled review queue from the exploratory geometry output."""

import argparse
import json
from pathlib import Path
from typing import Any


def review_queue(probe: dict[str, Any]) -> dict[str, Any]:
    """Choose up to ten chronological positive frames, at least 60 seconds apart."""
    if probe.get("status") != "EXPLORATORY_NOT_VALIDATED":
        raise ValueError("Expected exploratory probe output")
    chosen: list[dict[str, Any]] = []
    for row in sorted(probe["observations"], key=lambda x: (x["period"], x["frame_id"])):
        if not row["options"]:
            continue
        if chosen and row["period"] == chosen[-1]["period"]:
            if row["frame_id"] - chosen[-1]["frame_id"] < 600:
                continue
        chosen.append(
            {
                "period": row["period"],
                "frame_id": row["frame_id"],
                "match_timestamp": row["timestamp"],
                "candidate_player_ids": [x["player_id"] for x in row["options"]],
                "video_timestamp": None,
                "visibility": "NOT_REVIEWED",
                "geometric_screen_correct": None,
                "off_ball_support_visible": None,
                "review_notes": None,
            }
        )
        if len(chosen) == 10:
            break
    return {
        "status": "NOT_REVIEWED",
        "match_id": probe["match_id"],
        "source_revision": probe["source_revision"],
        "source_file_sha256": probe["file_sha256"],
        "sampling": "First ten positive sampled frames at least 600 source frames apart "
        "within a period; selected for review, not representative.",
        "limitations": "Only positive frames: this queue cannot estimate recall or population "
        "precision. Provider timestamps require manual synchronization to video.",
        "items": chosen,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("probe", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = review_queue(json.loads(args.probe.read_text()))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Prepared {len(result['items'])} unreviewed frames")


if __name__ == "__main__":
    main()
