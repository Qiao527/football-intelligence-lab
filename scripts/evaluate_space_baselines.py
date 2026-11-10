"""Compare movement-only and observed-space rules on local provider weak labels."""

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from survey_space_coverage import sampled_windows

from fil.research.pass_lane import (
    passing_line_observation,
    position_screen,
    summarize_lane_timeline,
)
from fil.research.tracking_replay import movement_candidate

THRESHOLDS = (0.5, 1.0, 2.0)


def summarize(rows: list[dict]) -> dict:
    """Count comparable decisions and overlapping weak references, not precision or recall."""
    result: dict = {}
    for split in ("development", "comparison"):
        selected = [r for r in rows if r["split"] == split]
        coverage = Counter(r["eligibility"] for r in selected)
        comparable = [r for r in selected if r["eligibility"] == "comparable"]
        output = {
            "rows": len(selected),
            "coverage": dict(coverage),
            "movement_abstention_reasons": dict(
                Counter(
                    r.get("movement_reason", "unknown")
                    for r in selected
                    if r["eligibility"] == "movement_unavailable"
                )
            ),
            "space_abstention_reasons": dict(
                Counter(
                    r.get("temporal", {}).get("reason", "unknown")
                    for r in selected
                    if r["eligibility"] == "space_unavailable"
                )
            ),
            "rules": {},
            "by_match": {},
            "by_provider_role_group": {},
        }
        independent: Counter = Counter()
        for r in comparable:
            pos_status = r.get("position_screen", {}).get("status")
            if pos_status not in ("candidate", "not_candidate"):
                output.setdefault("independent_position_unavailable", 0)
                output["independent_position_unavailable"] += 1
                continue
            pos = pos_status == "candidate"
            movement = r["movement_status"] == "candidate"
            provider = bool(
                r["provider_event_ids"]["off_ball_run"] or r["provider_event_ids"]["passing_option"]
            )
            independent[(movement, pos, provider)] += 1
        output["independent_position_rule"] = [
            {"movement": key[0], "position": key[1], "provider_overlap": key[2], "count": value}
            for key, value in sorted(independent.items())
        ]
        output["position_persistence_sensitivity"] = {}
        for required in (2, 3, 4, 5):
            count: Counter = Counter()
            for r in comparable:
                if "temporal" not in r:
                    continue
                status = position_screen(r["temporal"], minimum_samples=required)["status"]
                if status == "candidate":
                    count["position_candidates"] += 1
                    count["missed_by_movement"] += r["movement_status"] == "not_candidate"
            output["position_persistence_sensitivity"][str(required)] = dict(count)
        for label, key in (
            ("by_match", "match_id"),
            ("by_provider_role_group", "provider_role_group"),
        ):
            groups: dict[str, Counter] = defaultdict(Counter)
            for r in comparable:
                bucket = groups[str(r.get(key) or "unavailable")]
                bucket["comparable"] += 1
                bucket["movement_candidate"] += r["movement_status"] == "candidate"
                bucket["spatial_candidate_1m"] += (
                    r["movement_status"] == "candidate" and r["clearance_change_m"] >= 1.0
                )
            output[label] = {name: dict(counts) for name, counts in sorted(groups.items())}
        for threshold in THRESHOLDS:
            cells: Counter = Counter()
            per_reference: dict[str, Counter] = defaultdict(Counter)
            for r in comparable:
                movement = r["movement_status"] == "candidate"
                spatial = movement and r["clearance_change_m"] >= threshold
                reference = bool(
                    r["provider_event_ids"]["off_ball_run"]
                    or r["provider_event_ids"]["passing_option"]
                )
                cells[(movement, spatial, reference)] += 1
                for rule, selected_by_rule in (("movement", movement), ("spatial", spatial)):
                    if selected_by_rule:
                        per_reference[rule]["selected"] += 1
                        per_reference[rule]["off_ball_run_overlap"] += bool(
                            r["provider_event_ids"]["off_ball_run"]
                        )
                        per_reference[rule]["passing_option_overlap"] += bool(
                            r["provider_event_ids"]["passing_option"]
                        )
            output["rules"][str(threshold)] = [
                {"movement": key[0], "spatial": key[1], "provider_overlap": key[2], "count": value}
                for key, value in sorted(cells.items())
            ]
            output.setdefault("separate_provider_labels", {})[str(threshold)] = {
                k: dict(v) for k, v in sorted(per_reference.items())
            }
        result[split] = output
    return result


def evaluate_match(raw: Path, interim: Path, split: str) -> tuple[dict, list[dict]]:
    """Stream a hash-verified match, using provider annotations only as weak references."""
    manifest = json.loads((interim / "source-manifest.json").read_text())
    qc = json.loads((interim / "source-quality.json").read_text())
    mid = str(manifest["match_id"])
    if (
        qc["status"] != "WARN"
        or str(qc["match_id"]) != mid
        or raw.name != mid
        or qc["source_revision"] != manifest["source_revision"]
    ):
        raise ValueError(f"Source audit not eligible: {mid}")
    for record in manifest["files"]:
        with (raw / record["name"]).open("rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() != record["sha256"]:
                raise ValueError(f"Source hash mismatch: {mid}/{record['name']}")
    meta = json.loads((raw / f"{mid}_match.json").read_text())
    if str(meta["id"]) != mid:
        raise ValueError(f"Metadata identity mismatch: {mid}")
    with (raw / f"{mid}_phases_of_play.csv").open(encoding="utf-8", newline="") as f:
        phases = list(csv.DictReader(f))
    events: dict[tuple[str, str], list[dict]] = defaultdict(list)
    with (raw / f"{mid}_dynamic_events.csv").open(encoding="utf-8", newline="") as f:
        for event in csv.DictReader(f):
            if event["event_type"] in ("off_ball_run", "passing_option"):
                if event["match_id"] != mid:
                    raise ValueError(f"Event identity mismatch: {mid}")
                events[(event["player_id"], event["period"])].append(event)
    teams = {p["id"]: p["team_id"] for p in meta["players"]}
    roles = {p["id"]: (p.get("player_role") or {}).get("position_group") for p in meta["players"]}
    home, away = meta["home_team"]["id"], meta["away_team"]["id"]
    groups = {"home team": home, "away team": away}
    rows: list[dict] = []
    windows: Counter = Counter()
    with (raw / f"{mid}_tracking_extrapolated.jsonl").open(encoding="utf-8") as f:
        for frame, prior in sampled_windows((json.loads(line) for line in f), interval=100):
            windows["sampled"] += 1
            possession = frame.get("possession") or {}
            group = possession.get("group")
            team = groups.get(group)
            carrier = possession.get("player_id")
            if team is None or teams.get(carrier) != team or frame.get("period") not in (1, 2):
                windows["unavailable_possession_or_period"] += 1
                continue
            targets = [
                p["player_id"]
                for p in frame.get("player_data", [])
                if p.get("is_detected") is True
                and p.get("player_id") != carrier
                and teams.get(p.get("player_id")) == team
            ]
            if len(targets) != len(set(targets)):
                windows["duplicate_identity"] += 1
                continue
            windows["usable_center"] += 1
            for player in targets:
                movement = movement_candidate(
                    prior, player, team, group, teams, phases, frame["frame"], frame["period"]
                )
                labels = {"off_ball_run": [], "passing_option": []}
                for event in events[(str(player), str(frame["period"]))]:
                    if (
                        int(event["frame_start"]) <= frame["frame"]
                        and int(event["frame_end"]) >= frame["frame"] - 20
                    ):
                        labels[event["event_type"]].append(event["event_id"])
                row = {
                    "match_id": mid,
                    "split": split,
                    "frame": frame["frame"],
                    "period": frame["period"],
                    "center_timestamp": frame.get("timestamp"),
                    "source_frame_ids": movement["frame_ids"],
                    "source_timestamps": movement["timestamps"],
                    "player_id": player,
                    "provider_role_group": roles.get(player),
                    "movement_status": movement["status"],
                    "movement_reason": movement["reason"],
                    "movement_displacement_m": movement["displacement_m"],
                    "movement_start_m": movement["start"],
                    "movement_end_m": movement["end"],
                    "clearance_change_m": None,
                    "eligibility": "movement_unavailable",
                    "provider_event_ids": labels,
                }
                if movement["status"] in ("candidate", "not_candidate"):
                    timeline = [
                        passing_line_observation(f, teams, home, away, player) for f in prior
                    ]
                    temporal = summarize_lane_timeline(timeline, phases)
                    row["temporal"] = temporal
                    if temporal["status"] == "observed_geometry":
                        row["eligibility"] = "comparable"
                        row["clearance_change_m"] = temporal["clearance_change_m"]
                        row["position_screen"] = position_screen(temporal)
                    else:
                        row["eligibility"] = "space_unavailable"
                rows.append(row)
    return {
        "match_id": mid,
        "split": split,
        "windows": dict(windows),
        "source_file_sha256": {r["name"]: r["sha256"] for r in manifest["files"]},
    }, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("interim_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifests = [
        p
        for p in sorted(args.interim_root.glob("*/source-manifest.json"))
        if p.parent.name.isdecimal()
    ]
    eligible, excluded = [], []
    for path in manifests:
        qc = json.loads((path.parent / "source-quality.json").read_text())
        (eligible if qc["status"] == "WARN" else excluded).append(path.parent.name)
    comparison = set(eligible[-5:])
    matches, rows = [], []
    for mid in eligible:
        split = "comparison" if mid in comparison else "development"
        info, cases = evaluate_match(args.raw_root / mid, args.interim_root / mid, split)
        matches.append(info)
        rows.extend(cases)
        print(f"{mid}: {split}, {len(cases)} observations", flush=True)
    output = {
        "status": "EXPLORATORY_NOT_VALIDATED",
        "sampling": "Every 100 source frames "
        "(10 seconds at stated 10 Hz), detected teammates at center, 2 Hz lookback.",
        "split": "Last five sorted eligible match IDs used as comparison, assigned before "
        "running; previously inspected dataset, not a blind generalization test.",
        "thresholds_m": list(THRESHOLDS),
        "summary": summarize(rows),
        "matches": matches,
        "excluded": excluded,
        "rows": rows,
        "limits": "Same-provider model outputs are weak references; no human ground truth, "
        "true negatives, tactical value, player ranking, causation, or live-model performance. "
        "Stable detected opponents do not establish full opponent coverage.",
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "summary": output["summary"]}), flush=True)


if __name__ == "__main__":
    main()
