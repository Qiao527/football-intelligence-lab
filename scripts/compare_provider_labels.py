"""Compare sampled tracking screens to same-provider model labels, not ground truth."""

import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


def overlapping_labels(events: list[dict], player: int, period: int, start: int, end: int) -> dict:
    """Return IDs for matching player/period and inclusive source-frame overlap."""
    found = {"off_ball_run": [], "passing_option": []}
    for row in events:
        kind = row["event_type"]
        if (
            kind in found
            and row["player_id"] == str(player)
            and row["period"] == str(period)
            and int(row["frame_start"]) <= end
            and int(row["frame_end"]) >= start
        ):
            found[kind].append(row["event_id"])
    return found


def compare(survey: dict, raw_root: Path, interim_root: Path) -> dict:
    """Join sampled pairs to provider source IDs after rechecking source hashes."""
    rows = []
    for match in survey["matches"]:
        mid = match["match_id"]
        manifest = json.loads((interim_root / mid / "source-manifest.json").read_text())
        qc = json.loads((interim_root / mid / "source-quality.json").read_text())
        hashes = {record["name"]: record["sha256"] for record in manifest["files"]}
        if (
            qc["status"] != "WARN"
            or str(qc["match_id"]) != mid
            or hashes != match["source_file_sha256"]
            or manifest["source_revision"] != match["source_revision"]
        ):
            raise ValueError(f"Unverified source identity for match {mid}")
        for name, expected in hashes.items():
            with (raw_root / mid / name).open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                    raise ValueError(f"Source hash mismatch for match {mid}")
        with (raw_root / mid / f"{mid}_dynamic_events.csv").open(encoding="utf-8", newline="") as f:
            events = [
                row
                for row in csv.DictReader(f)
                if row["event_type"] in {"off_ball_run", "passing_option"}
            ]
        if any(row["match_id"] != mid for row in events):
            raise ValueError(f"Event match identity mismatch for {mid}")
        for item in match["outcomes"]:
            center = item["frame"]
            labels = overlapping_labels(
                events, item["player_id"], item["period"], center - 20, center
            )
            rows.append(
                {
                    "match_id": mid,
                    "period": item["period"],
                    "frame": center,
                    "timestamp": item["movement"]["timestamps"][-1]
                    if item["movement"]["timestamps"]
                    else None,
                    "player_id": item["player_id"],
                    "screen_status": item["movement"]["status"],
                    "provider_event_ids": labels,
                }
            )
    return {
        "status": "EXPLORATORY_NOT_VALIDATED",
        "rows": rows,
        "limits": "Same-provider, model-derived labels are not independent ground truth. "
        "Inclusive interval overlap is an assumption; absence is not a verified negative. "
        "Fixed-time sampled pairs are dependent and selected by detection and possession.",
    }


def review_sample(comparison: dict, per_stratum: int = 4) -> list[dict]:
    """Select reproducible hit/miss strata while withholding model outputs from reviewers."""
    groups = defaultdict(list)
    for row in comparison["rows"]:
        if row["screen_status"] not in ("candidate", "not_candidate"):
            continue
        ref = bool(
            row["provider_event_ids"]["off_ball_run"] or row["provider_event_ids"]["passing_option"]
        )
        groups[(row["screen_status"], ref)].append(row)
    rng = random.Random(2401)
    selected = []
    for key in sorted(groups):
        candidates = list(groups[key])
        rng.shuffle(candidates)
        count = 0
        for row in candidates:
            if any(
                row["match_id"] == x["match_id"] and abs(row["frame"] - x["frame"]) < 600
                for x in selected
            ):
                continue
            selected.append(row)
            count += 1
            if count == per_stratum:
                break
    rng.shuffle(selected)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("survey", type=Path)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("interim_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    survey = json.loads(args.survey.read_text())
    result = compare(survey, args.raw_root, args.interim_root)
    selected = review_sample(result)
    result["review_selection"] = selected
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    per_match = defaultdict(list)
    for row in selected:
        per_match[row["match_id"]].append(
            {
                "period": row["period"],
                "frame_id": row["frame"],
                "match_timestamp": row["timestamp"],
                "candidate_player_ids": [row["player_id"]],
                "visibility": "NOT_REVIEWED",
                "support_option_visible": None,
                "counter_evidence": None,
                "review_notes": None,
            }
        )
    for mid, items in per_match.items():
        manifest = json.loads((args.interim_root / mid / "source-manifest.json").read_text())
        packet = {
            "status": "NOT_REVIEWED",
            "match_id": mid,
            "source_revision": manifest["source_revision"],
            "source_file_sha256": {r["name"]: r["sha256"] for r in manifest["files"]},
            "items": items,
            "limits": "Review tracking replay only; not independent video.",
        }
        (args.interim_root / mid / "blind-review-queue.json").write_text(
            json.dumps(packet, indent=2) + "\n"
        )
    counts = Counter(
        (
            r["screen_status"],
            bool(r["provider_event_ids"]["off_ball_run"]),
            bool(r["provider_event_ids"]["passing_option"]),
        )
        for r in result["rows"]
    )
    print(
        json.dumps(
            {
                "rows": len(result["rows"]),
                "selected": len(selected),
                "counts": [
                    {"screen": k[0], "off_ball_run": k[1], "passing_option": k[2], "count": v}
                    for k, v in sorted(counts.items())
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
