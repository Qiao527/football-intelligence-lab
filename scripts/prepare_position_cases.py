"""Prepare local, traceable low-movement geometry cases for the existing replay."""

import argparse
import json
from pathlib import Path


def select_cases(report: dict) -> dict[str, list[dict]]:
    """Select first and first weak-label-overlap cases per match, without value labels."""
    chosen = {}
    overlap_selected = set()
    for row in report["rows"]:
        mid = row["match_id"]
        if (
            row["eligibility"] != "comparable"
            or row["movement_status"] != "not_candidate"
            or row.get("position_screen", {}).get("status") != "candidate"
        ):
            continue
        overlap = bool(row.get("provider_event_ids", {}).get("passing_option"))
        if mid in chosen and (not overlap or mid in overlap_selected):
            continue
        chosen.setdefault(mid, []).append(
            {
                "period": row["period"],
                "frame_id": row["frame"],
                "match_timestamp": row["center_timestamp"],
                "candidate_player_ids": [row["player_id"]],
            }
        )
        if overlap:
            overlap_selected.add(mid)
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("interim_root", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if report["status"] != "EXPLORATORY_NOT_VALIDATED":
        raise ValueError("Expected exploratory baseline report")
    source_matches = {m["match_id"]: m for m in report["matches"]}
    selected = select_cases(report)
    for mid, items in selected.items():
        if not mid.isdecimal() or mid not in source_matches:
            raise ValueError("Invalid match ID in report")
        manifest = json.loads((args.interim_root / mid / "source-manifest.json").read_text())
        hashes = {r["name"]: r["sha256"] for r in manifest["files"]}
        if hashes != source_matches[mid]["source_file_sha256"]:
            raise ValueError(f"Report/manifest mismatch: {mid}")
        packet = {
            "status": "NOT_REVIEWED",
            "match_id": mid,
            "source_revision": manifest["source_revision"],
            "source_file_sha256": hashes,
            "items": items,
            "limits": "Observed geometry only; no tactical judgment.",
        }
        (args.interim_root / mid / "position-candidates.json").write_text(
            json.dumps(packet, indent=2) + "\n"
        )
    print(f"Prepared {sum(map(len, selected.values()))} cases from {len(selected)} matches")


if __name__ == "__main__":
    main()
