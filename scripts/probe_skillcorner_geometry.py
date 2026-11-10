"""Exploratory source-frame geometry probe; no player ranking or tracking interpolation."""

import argparse
import collections
import csv
import json
import runpy
from pathlib import Path
from typing import Any

from fil.research.support_geometry import support_geometry

AUDIT = runpy.run_path(str(Path(__file__).with_name("audit_skillcorner.py")))["audit"]


def normalize_frame(
    source: dict[str, Any], meta: dict[str, Any], phases: list[dict[str, str]]
) -> tuple[dict[str, Any] | None, set[int] | None, str | None]:
    """Conservatively select independently recorded positions and provider lineup intervals."""
    frame, period = source.get("frame"), source.get("period")
    if (
        type(frame) is not int
        or type(period) is not int
        or period not in (1, 2)
        or not source.get("timestamp")
    ):
        return None, None, "frame_identity_unavailable"
    active_phases = [
        p
        for p in phases
        if int(p["period"]) == period and int(p["frame_start"]) < frame < int(p["frame_end"])
    ]
    if len(active_phases) != 1:
        return None, None, "phase_unavailable_or_boundary"
    teams = {"home team": meta["home_team"]["id"], "away team": meta["away_team"]["id"]}
    possession = source.get("possession") or {}
    own = teams.get(possession.get("group"))
    carrier_id = possession.get("player_id")
    if (
        own is None
        or type(carrier_id) is not int
        or int(active_phases[0]["team_in_possession_id"]) != own
    ):
        return None, None, "possession_unavailable_or_conflicting"
    ball = source.get("ball_data") or {}
    if ball.get("is_detected") is not True or ball.get("x") is None or ball.get("y") is None:
        return None, None, "ball_not_detected"
    player_meta = {p["id"]: p for p in meta["players"]}
    if carrier_id not in player_meta or player_meta[carrier_id]["team_id"] != own:
        return None, None, "carrier_identity_unavailable"
    active_opponents = set()
    for p in meta["players"]:
        sequences = (p.get("playing_time") or {}).get("sequences")
        if not isinstance(sequences, list) or any(
            not isinstance(seq, dict)
            or seq.get("period") not in ("period_1", "period_2")
            or type(seq.get("start_frame")) is not int
            or type(seq.get("end_frame")) is not int
            or seq["start_frame"] >= seq["end_frame"]
            for seq in sequences
        ):
            return None, None, "lineup_intervals_unavailable"
        if p["team_id"] != own and any(
            seq.get("period") == f"period_{period}"
            and type(seq.get("start_frame")) is int
            and type(seq.get("end_frame")) is int
            and seq["start_frame"] < frame < seq["end_frame"]
            for seq in sequences
        ):
            active_opponents.add(p["id"])
    if not 7 <= len(active_opponents) <= 11:
        return None, None, "opponent_lineup_unavailable_or_boundary"
    tracked = source.get("player_data")
    if not isinstance(tracked, list):
        return None, None, "tracking_unavailable"
    normalized = []
    for p in tracked:
        pid = p.get("player_id")
        if pid not in player_meta:
            return None, None, "unknown_tracking_identity"
        position = None if p.get("x") is None or p.get("y") is None else [p["x"], p["y"]]
        normalized.append(
            {
                "player_id": pid,
                "team_id": player_meta[pid]["team_id"],
                "position": position,
                "detected": p.get("is_detected") is True,
            }
        )
    return (
        {
            "source_id": str(meta["id"]),
            "frame_id": frame,
            "period": period,
            "timestamp": source["timestamp"],
            "coordinate_units": "metres",
            "ball_in_play": True,
            "ball": [ball["x"], ball["y"]],
            "ball_detected": True,
            "possession_team_id": own,
            "carrier_id": carrier_id,
            "players": normalized,
        },
        active_opponents,
        None,
    )


def probe(raw_dir: Path, manifest_path: Path) -> dict[str, Any]:
    """Screen every tenth provider frame after source audit; retain exact original frame IDs."""
    quality = AUDIT(raw_dir, manifest_path)
    if quality["status"] == "FAIL":
        raise ValueError("Source audit failed; refusing geometry probe")
    manifest = json.loads(manifest_path.read_text())
    match = manifest["match_id"]
    meta = json.loads((raw_dir / f"{match}_match.json").read_text())
    with (raw_dir / f"{match}_phases_of_play.csv").open(newline="", encoding="utf-8") as f:
        phases = list(csv.DictReader(f))
    counts: collections.Counter[str] = collections.Counter()
    observations = []
    with (raw_dir / f"{match}_tracking_extrapolated.jsonl").open() as f:
        for line in f:
            frame = json.loads(line)
            if frame["frame"] % 10:
                continue
            counts["sampled_frames"] += 1
            try:
                normalized, opponents, reason = normalize_frame(frame, meta, phases)
                if reason:
                    counts[reason] += 1
                    continue
                result = support_geometry(normalized, opponents)
            except (ValueError, TypeError, KeyError, OverflowError):
                counts["invalid_source_frame"] += 1
                continue
            if result["abstention"]:
                counts["coverage_abstention"] += 1
                continue
            counts["screened_frames"] += 1
            if result["options"]:
                counts["frames_with_screened_options"] += 1
                observations.append(
                    {
                        "frame_id": result["frame_id"],
                        "period": result["period"],
                        "timestamp": result["timestamp"],
                        "options": result["options"],
                        "unobserved_teammate_ids": result["unobserved_teammate_ids"],
                    }
                )
    return {
        "status": "EXPLORATORY_NOT_VALIDATED",
        "source_revision": manifest["source_revision"],
        "match_id": match,
        "file_sha256": {r["name"]: r["sha256"] for r in manifest["files"]},
        "method": "Every tenth original frame; detected ball, carrier and all active opponents; "
        "strictly inside one provider phase and player intervals.",
        "thresholds": {"ball_to_teammate_m": [8, 25], "opponent_segment_clearance_m": 2},
        "counts": dict(counts),
        "observations": observations,
        "limits": [
            "Static geometry, not an inferred pass, off-ball run or football IQ.",
            "Detection, lineup and phase labels are provider estimates; incomplete coverage "
            "can exclude valid options and missing defenders can create false positives.",
            "Repeated sampled frames are not independent opportunities; no player ranking, "
            "causal effect, benchmark or generalization is established.",
            "Thresholds are illustrative and not calibrated or validated.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_dir", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = probe(args.raw_dir, args.manifest)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "match_id", "counts")}, indent=2))


if __name__ == "__main__":
    main()
