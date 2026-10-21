"""Independently reconcile local fact tables directly against original StatsBomb records.

Usage: uv run --frozen python scripts/verify_explorer_source.py LOCAL_CONFIG
No shot/window/cumulative implementation is imported or used to establish expected values.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

import pyarrow.parquet as pq

from fil.ingestion.statsbomb import verify_bundle


def elapsed(stamp: str) -> int:
    hours, minutes, seconds = stamp.split(":")
    whole, fraction = seconds.split(".")
    return (int(hours) * 3600 + int(minutes) * 60 + int(whole)) * 1000 + int(fraction)


def main() -> None:
    config = json.loads(Path(sys.argv[1]).read_bytes())
    raw = Path(config["raw"])
    facts = Path(config["metrics"])
    source = verify_bundle(raw)
    match_id = source["quality"]["identity"]["match_id"]
    events = json.loads((raw / f"data/events/{match_id}.json").read_bytes())
    by_id = {e["id"]: e for e in events}
    original = [e for e in events if e["type"]["name"] == "Shot" and e["period"] in (1, 2, 3, 4)]
    actual = pq.ParquetFile(facts / "shots.parquet").read().to_pylist()
    assert [r["event_id"] for r in actual] == [e["id"] for e in original]
    for r, e in zip(actual, original, strict=True):
        assert r["shot_xg"] == e["shot"]["statsbomb_xg"]
        assert json.loads(r["source_record_json"]) == e
        assert r["coordinate_system"] == "raw_statsbomb_120x80"
        for names, values in (
            (("x", "y"), e.get("location") or []),
            (("end_x", "end_y"), e["shot"].get("end_location") or []),
        ):
            for index, name in enumerate(names):
                assert r[name] == (values[index] if len(values) > index else None)
    spatial = json.loads((facts / "quality.json").read_bytes())["match"]["spatial"]
    assert spatial["coordinate_system"] == "raw_statsbomb_120x80"
    assert spatial["origin"] == "upper_left" and spatial["y_increases"] == "down"
    assert spatial["event_count"] == len(events)
    assert spatial["coordinate_nulls"]["x"] == sum(e.get("location") is None for e in events)
    expected_groups = {(e["team"]["id"], e["period"]) for e in events if e["period"] < 5}
    assert {(g["team_id"], g["period"]) for g in spatial["team_period_evidence"]} == expected_groups
    for group in spatial["team_period_evidence"]:
        goals = [
            e
            for e in original
            if e["team"]["id"] == group["team_id"]
            and e["period"] == group["period"]
            and e["shot"]["outcome"]["name"] == "Goal"
        ]
        assert group["goal_event_ids"] == [e["id"] for e in goals]
        assert group["goal_end_x"] == [e["shot"]["end_location"][0] for e in goals]
        assert group["physical_attacking_direction"] is None
    identity = source["quality"]["identity"]
    teams = (identity["home_team_id"], identity["away_team_id"])
    points = pq.ParquetFile(facts / "xg_cumulative.parquet").read().to_pylist()
    assert [r["event_id"] for r in points] == [e["id"] for e in original]
    totals = []
    for t in teams:
        rows = [e for e in original if e["team"]["id"] == t]
        values = []
        for e in rows:
            values.append(e["shot"]["statsbomb_xg"])
            point = next(p for p in points if p["event_id"] == e["id"])
            assert point["cumulative_xg"] == math.fsum(values)
        totals.append(
            {
                "team_id": t,
                "shots": len(rows),
                "xg": math.fsum(values),
                "npxg": math.fsum(
                    e["shot"]["statsbomb_xg"]
                    for e in rows
                    if e["shot"]["type"]["name"] != "Penalty"
                ),
            }
        )
    windows = pq.ParquetFile(facts / "window_threat.parquet").read().to_pylist()
    for width in (300000, 600000, 900000):
        bins = [w for w in windows if w["width_ms"] == width]
        seen = []
        for b in bins:
            expected = [
                e
                for e in original
                if e["team"]["id"] == b["team_id"]
                and e["period"] == b["period"]
                and (
                    b["start_ms"] <= elapsed(e["timestamp"]) < b["end_ms"]
                    or b["include_terminal"]
                    and elapsed(e["timestamp"]) == b["end_ms"]
                )
            ]
            ids = [e["id"] for e in expected]
            assert b["event_ids"] == ids and b["shot_count"] == len(ids)
            assert b["xg"] == math.fsum(e["shot"]["statsbomb_xg"] for e in expected)
            seen.extend(ids)
        assert sorted(seen) == sorted(e["id"] for e in original) and len(seen) == len(set(seen))
    result = {
        "verified_source_events": len(by_id),
        "verified_shots": len(original),
        "team_totals": totals,
        "verified_cumulative_points": len(points),
        "verified_windows": len(windows),
        "window_widths_minutes": [5, 10, 15],
        "spatial_native_coordinates": "PASS; original shot start/end coordinates unchanged",
        "physical_attacking_directions": "UNCERTIFIED; explicitly null",
        "files": {
            p.name: {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "size_bytes": p.stat().st_size,
            }
            for p in facts.iterdir()
            if p.is_file()
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
