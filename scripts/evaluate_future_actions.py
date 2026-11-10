"""Relate pre-action geometry to later same-provider carrier events; exploratory only."""

import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from fil.research.future_action import (
    corroborate_reception,
    later_carrier_action,
    reception_followup,
    valid_action_clock,
)
from fil.research.pass_lane import (
    passing_line_observation,
    position_screen,
    summarize_lane_timeline,
)
from fil.research.tracking_replay import movement_candidate


def cluster_interval(clusters: dict, seed: int, draws: int) -> list[float] | None:
    """Percentile interval resampling matches, withheld for fewer than five matches."""
    names = sorted(clusters)
    if len(names) < 5:
        return None
    rng = random.Random(seed)
    estimates = []
    for _ in range(draws):
        sampled = [rng.choice(names) for _ in names]
        values = [v for mid in sampled for v in clusters[mid]]
        estimates.append(sum(values) / len(values))
    estimates.sort()
    return [estimates[int(draws * 0.025)], estimates[min(draws - 1, int(draws * 0.975))]]


def features_match(
    prior: list[dict],
    pair: dict,
    team: int,
    group: str,
    teams: dict,
    phases: list[dict],
    home: int,
    away: int,
    frame_id: int,
    period: int,
    minimum_samples: int,
) -> bool:
    """Recompute every included row using immutable source frames."""
    movement = movement_candidate(
        prior, pair["player_id"], team, group, teams, phases, frame_id, period
    )
    timeline = [passing_line_observation(f, teams, home, away, pair["player_id"]) for f in prior]
    temporal = summarize_lane_timeline(timeline, phases)
    return (
        movement["status"] == pair["movement_status"]
        and movement["displacement_m"] == pair["movement_displacement_m"]
        and temporal == pair["temporal"]
        and position_screen(temporal, minimum_samples) == pair["position_screen"]
    )


def summarize(snapshots: list[dict], seed: int = 4201, draws: int = 2000) -> dict:
    """Average within-snapshot per-player targeting differences; resample match clusters."""
    result = {}
    for split in ("development", "comparison"):
        chosen = [s for s in snapshots if s["split"] == split]
        counts = Counter(s["status"] for s in chosen)
        matched = [s for s in chosen if s["status"] == "matched_pass"]
        clusters = defaultdict(list)
        for s in matched:
            targeted_position = s["target_position_candidate"]
            delta = (
                1 / s["position_candidates"] if targeted_position else -1 / s["position_controls"]
            )
            clusters[s["match_id"]].append(delta)
        values = [v for group in clusters.values() for v in group]
        shared = [
            s for s in matched if s.get("movement_candidates", 0) and s.get("movement_controls", 0)
        ]

        def delta(s: dict, prefix: str) -> float:
            return (
                1 / s[f"{prefix}_candidates"]
                if s[f"target_{prefix}_candidate"]
                else -1 / s[f"{prefix}_controls"]
            )

        position_shared = [delta(s, "position") for s in shared]
        movement_shared = [delta(s, "movement") for s in shared]
        differences = [a - b for a, b in zip(position_shared, movement_shared, strict=True)]
        shared_clusters = defaultdict(list)
        for s, difference in zip(shared, differences, strict=True):
            shared_clusters[s["match_id"]].append(difference)
        result[split] = {
            "snapshot_status": dict(counts),
            "insufficient_data_reasons": dict(
                Counter(
                    s.get("action", {}).get("reason") or s.get("reason", "unknown")
                    for s in chosen
                    if s["status"] == "insufficient_data"
                )
            ),
            "matched_snapshots": len(matched),
            "matched_matches": len(clusters),
            "targets_in_position_group": sum(s["target_position_candidate"] for s in matched),
            "position_exposures": sum(s["position_candidates"] for s in matched),
            "control_exposures": sum(s["position_controls"] for s in matched),
            "pass_outcomes": dict(Counter(s["action"]["pass_outcome"] for s in matched)),
            "provider_reception_corroborated": sum(
                s.get("reception", {}).get("status") == "provider_reception_corroborated"
                for s in matched
            ),
            "receiver_followup_by_target_group": {
                str(flag).lower(): dict(
                    Counter(
                        s.get("receiver_followup", {}).get("status", "unconfirmed")
                        for s in matched
                        if s["target_position_candidate"] is flag
                    )
                )
                for flag in (True, False)
            },
            "same_snapshot_rule_comparison": {
                "snapshots": len(shared),
                "position_delta": sum(position_shared) / len(shared) if shared else None,
                "movement_delta": sum(movement_shared) / len(shared) if shared else None,
                "paired_delta_difference": sum(differences) / len(shared) if shared else None,
                "cluster_bootstrap_95_interval": cluster_interval(shared_clusters, seed + 1, draws),
            },
            "within_snapshot_rate_difference": sum(values) / len(values) if values else None,
            "cluster_bootstrap_95_interval": cluster_interval(clusters, seed, draws),
        }
    return result


def evaluate(
    report: dict,
    raw_root: Path,
    interim_root: Path,
    minimum_samples: int = 3,
    restrict_distance: bool = False,
) -> dict:
    """Recheck source hashes and examine later action only after selecting spatial cohorts."""
    grouped = defaultdict(list)
    for row in report["rows"]:
        if row["eligibility"] != "comparable":
            continue
        if restrict_distance and not 8 <= row["temporal"]["samples"][-1]["ball_distance_m"] <= 25:
            continue
        position = position_screen(row["temporal"], minimum_samples)
        if position["status"] in ("candidate", "not_candidate"):
            grouped[(row["match_id"], row["period"], row["frame"])].append(
                {**row, "position_screen": position}
            )
    snapshots = []
    for info in report["matches"]:
        mid = info["match_id"]
        manifest = json.loads((interim_root / mid / "source-manifest.json").read_text())
        qc = json.loads((interim_root / mid / "source-quality.json").read_text())
        hashes = {r["name"]: r["sha256"] for r in manifest["files"]}
        if (
            qc["status"] != "WARN"
            or str(qc["match_id"]) != mid
            or qc["source_revision"] != manifest["source_revision"]
            or manifest["source_revision"] != raw_root.name
            or hashes != info["source_file_sha256"]
        ):
            raise ValueError(f"Source manifest mismatch: {mid}")
        raw = raw_root / mid
        for name, expected in hashes.items():
            with (raw / name).open("rb") as file:
                if hashlib.file_digest(file, "sha256").hexdigest() != expected:
                    raise ValueError(f"Source hash mismatch: {mid}/{name}")
        meta = json.loads((raw / f"{mid}_match.json").read_text())
        if str(meta["id"]) != mid:
            raise ValueError(f"Match identity mismatch: {mid}")
        teams = {p["id"]: p["team_id"] for p in meta["players"]}
        groups = {"home team": meta["home_team"]["id"], "away team": meta["away_team"]["id"]}
        home, away = meta["home_team"]["id"], meta["away_team"]["id"]
        with (raw / f"{mid}_phases_of_play.csv").open(encoding="utf-8", newline="") as file:
            phases = list(csv.DictReader(file))
        wanted = {
            n
            for key in grouped
            if key[0] == mid
            for n in (*range(key[2] - 20, key[2] + 1, 5), *range(key[2] + 1, key[2] + 131))
        }
        frames = {}
        with (raw / f"{mid}_tracking_extrapolated.jsonl").open(encoding="utf-8") as file:
            for line in file:
                frame = json.loads(line)
                if frame["frame"] in wanted:
                    frames[frame["frame"]] = frame
        with (raw / f"{mid}_dynamic_events.csv").open(encoding="utf-8", newline="") as file:
            events = [e for e in csv.DictReader(file) if e["event_type"] == "player_possession"]
        if any(e["match_id"] != mid for e in events):
            raise ValueError(f"Event match identity mismatch: {mid}")
        for key, pairs in grouped.items():
            if key[0] != mid:
                continue
            _, period, frame_id = key
            frame = frames.get(frame_id)
            row = {
                "match_id": mid,
                "split": info["split"],
                "period": period,
                "frame_id": frame_id,
                "source_file_sha256": hashes,
                "status": "insufficient_data",
            }
            if (
                frame is None
                or frame.get("period") != period
                or any(p["center_timestamp"] != frame.get("timestamp") for p in pairs)
            ):
                row["reason"] = "Source frame or timestamp mismatch."
                snapshots.append(row)
                continue
            possession = frame.get("possession") or {}
            carrier, team = possession.get("player_id"), groups.get(possession.get("group"))
            if team is None or teams.get(carrier) != team:
                row["reason"] = "Source carrier team unavailable."
                snapshots.append(row)
                continue
            prior = [frames.get(i) for i in range(frame_id - 20, frame_id + 1, 5)]
            if any(f is None for f in prior):
                row["reason"] = "Source tracking samples are missing."
                snapshots.append(row)
                continue
            if not all(
                features_match(
                    prior,
                    pair,
                    team,
                    possession.get("group"),
                    teams,
                    phases,
                    home,
                    away,
                    frame_id,
                    period,
                    minimum_samples,
                )
                for pair in pairs
            ):
                row["reason"] = "Source tracking and computed features differ."
                snapshots.append(row)
                continue
            options = {p["player_id"]: p["position_screen"]["status"] == "candidate" for p in pairs}
            movement_options = {p["player_id"]: p["movement_status"] == "candidate" for p in pairs}
            if len(options) != len(pairs) or any(teams.get(pid) != team for pid in options):
                row["reason"] = "Duplicate or wrong-team player snapshot."
                snapshots.append(row)
                continue
            pos, controls = sum(options.values()), sum(not x for x in options.values())
            row.update(
                carrier_id=carrier,
                center_timestamp=frame.get("timestamp"),
                position_candidates=pos,
                position_controls=controls,
                position_player_ids=sorted(pid for pid, flag in options.items() if flag),
                control_player_ids=sorted(pid for pid, flag in options.items() if not flag),
                movement_candidates=sum(movement_options.values()),
                movement_controls=sum(not flag for flag in movement_options.values()),
                movement_player_ids=sorted(pid for pid, flag in movement_options.items() if flag),
                movement_control_player_ids=sorted(
                    pid for pid, flag in movement_options.items() if not flag
                ),
            )
            if not pos or not controls:
                row["status"] = "unmatched_groups"
                snapshots.append(row)
                continue
            action = later_carrier_action(events, period, frame_id, carrier, team)
            if action["status"] in ("pass", "non_pass_action"):
                end_frame = frames.get(action["end_frame"])
                if not valid_action_clock(frame, end_frame, period):
                    action = {
                        **action,
                        "status": "insufficient_data",
                        "target_id": None,
                        "pass_outcome": None,
                        "reason": "Future source frame or clock is missing or inconsistent.",
                    }
                else:
                    action["end_timestamp"] = end_frame["timestamp"]
            row["action"] = action
            if action["status"] == "pass":
                reception = corroborate_reception(events, period, action, team)
                if reception["status"] == "provider_reception_corroborated":
                    arrival = frames.get(reception["frame_start"])
                    if not valid_action_clock(frame, arrival, period, max_frames=80):
                        reception = {"status": "unconfirmed", "event_id": None, "frame_start": None}
                    else:
                        reception["timestamp"] = arrival["timestamp"]
                row["reception"] = reception
                followup = reception_followup(events, reception)
                if followup["status"] != "unconfirmed":
                    ending = frames.get(followup["end_frame"])
                    if not valid_action_clock(frame, ending, period, max_frames=130):
                        followup = {
                            "status": "unconfirmed",
                            "event_id": reception["event_id"],
                            "end_frame": None,
                        }
                    else:
                        followup["end_timestamp"] = ending["timestamp"]
                row["receiver_followup"] = followup
            if action["status"] != "pass":
                row["status"] = action["status"]
            elif action["target_id"] not in options:
                row["status"] = "target_outside_comparable_cohort"
            else:
                row["status"] = "matched_pass"
                row["target_position_candidate"] = options[action["target_id"]]
                row["target_movement_candidate"] = movement_options[action["target_id"]]
            snapshots.append(row)
        print(f"{mid}: checked", flush=True)
    return {
        "status": "EXPLORATORY_NOT_VALIDATED",
        "snapshots": snapshots,
        "summary": summarize(snapshots),
        "source_revision": raw_root.name,
        "minimum_qualifying_samples": minimum_samples,
        "center_distance_restricted": restrict_distance,
        "limits": "Provider-detected events and labels share the tracking source. "
        "Conditional on a recorded pass with known target within three seconds and both "
        "groups measurable; no causal attribution, verified tactical value or independent truth.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("interim_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-samples", type=int, choices=(2, 3, 4, 5), default=3)
    parser.add_argument("--restrict-distance", action="store_true")
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if report["status"] != "EXPLORATORY_NOT_VALIDATED":
        raise ValueError("Unexpected source report status")
    output = evaluate(
        report, args.raw_root, args.interim_root, args.minimum_samples, args.restrict_distance
    )
    with args.report.open("rb") as source:
        output["input_report_sha256"] = hashlib.file_digest(source, "sha256").hexdigest()
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output["summary"], indent=2))


if __name__ == "__main__":
    main()
