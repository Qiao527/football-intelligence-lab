"""Native possession identity audit, separate from derived process definitions."""

import json

import pyarrow as pa


def source_records(events: pa.Table) -> list[dict]:
    """Verify native possession labels against canonical rows without resegmentation."""
    fields = [
        "event_id",
        "provider_index",
        "period",
        "period_timestamp",
        "team_id",
        "player_id",
        "possession_id",
        "possession_team_id",
        "source",
        "coordinate_system",
        "source_record_json",
        "event_type",
        "x",
        "y",
    ]
    rows = events.select(fields).to_pylist()
    if len({r["event_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate original event IDs")
    if len({r["provider_index"] for r in rows}) != len(rows):
        raise ValueError("Duplicate provider sequence")
    records = []
    for r in rows:
        if r["source"] != "statsbomb_open_data" or r["coordinate_system"] != "raw_statsbomb_120x80":
            raise ValueError("Unsupported possession provider/frame")
        e = json.loads(r["source_record_json"])
        expected = {
            "id": r["event_id"],
            "index": r["provider_index"],
            "period": r["period"],
            "timestamp": r["period_timestamp"],
            "possession": r["possession_id"],
        }
        if (
            any(e.get(k) != v for k, v in expected.items())
            or any(
                (e.get(k) or {}).get("id") != r[v]
                for k, v in [
                    ("team", "team_id"),
                    ("player", "player_id"),
                    ("possession_team", "possession_team_id"),
                ]
            )
            or (e.get("type") or {}).get("name") != r["event_type"]
        ):
            raise ValueError("Possession identity differs from original source")
        point = e.get("location") or []
        if any(r[k] != (point[i] if i < len(point) else None) for i, k in enumerate(("x", "y"))):
            raise ValueError("Possession position differs from original source")
        if r["possession_id"] is not None and (
            type(e["possession"]) is not int or e["possession"] <= 0
        ):
            raise ValueError("Invalid native possession ID")
        records.append(e)
    return records
