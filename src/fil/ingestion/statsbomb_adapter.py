"""StatsBomb-only projections; preserve every event and its full semantic source record."""

import json
import math
import re
from dataclasses import asdict
from typing import Any
from uuid import UUID

import pyarrow as pa

from fil.schema import EVENT_SCHEMA, SCHEMA_VERSION, SchemaError, SourceContext, validate_table

NORMALIZER_VERSION = "fil-statsbomb-adapter-1"
# Names reviewed in FIL-002's pinned fixture. Recognition never controls row retention.
RECOGNIZED_TYPES = frozenset(
    {
        "Ball Receipt*",
        "Ball Recovery",
        "Block",
        "Camera On",
        "Camera off",
        "Carry",
        "Clearance",
        "Dispossessed",
        "Dribble",
        "Dribbled Past",
        "Duel",
        "Error",
        "Foul Committed",
        "Foul Won",
        "Goal Keeper",
        "Half End",
        "Half Start",
        "Injury Stoppage",
        "Interception",
        "Miscontrol",
        "Own Goal Against",
        "Own Goal For",
        "Pass",
        "Player Off",
        "Player On",
        "Pressure",
        "Referee Ball-Drop",
        "Shield",
        "Shot",
        "Starting XI",
        "Substitution",
        "Tactical Shift",
    }
)
_DETAILS = {
    "Pass": "pass",
    "Shot": "shot",
    "Carry": "carry",
    "Goal Keeper": "goalkeeper",
    "Dribble": "dribble",
    "Duel": "duel",
    "Interception": "interception",
    "Ball Receipt*": "ball_receipt",
    "50/50": "50_50",
}


def _integer(value: Any, label: str, *, optional: bool = False) -> int | None:
    if value is None and optional:
        return None
    if type(value) is not int or not 0 <= value < 2**63:
        raise SchemaError(f"Invalid integer {label}: {value!r}")
    return value


def _number(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if type(value) not in (float, int):
        raise SchemaError(f"Invalid finite number: {label}")
    try:
        number = float(value)
    except OverflowError as exc:
        raise SchemaError(f"Number out of range: {label}") from exc
    if not math.isfinite(number):
        raise SchemaError(f"Invalid finite number: {label}")
    return number


def _entity(obj: dict, key: str, *, required: bool = False) -> tuple[int | None, str | None]:
    value = obj.get(key)
    if value is None and not required:
        return None, None
    if not isinstance(value, dict):
        raise SchemaError(f"Expected object: {key}")
    identifier = _integer(value.get("id"), f"{key}.id")
    name = value.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SchemaError(f"Missing or invalid name: {key}")
    return identifier, name


def _coordinates(value: Any, label: str) -> tuple[float | None, ...]:
    if value is None:
        return None, None, None
    if not isinstance(value, list) or len(value) not in (2, 3):
        raise SchemaError(f"Expected 2D/3D coordinates: {label}")
    if any(v is None for v in value):
        raise SchemaError(f"Partial null coordinates: {label}")
    coords = tuple(_number(v, label) for v in value)
    return coords if len(coords) == 3 else (*coords, None)


def _uuid(value: Any) -> UUID:
    if not isinstance(value, str):
        raise SchemaError("Missing/invalid original event UUID")
    try:
        return UUID(value)
    except ValueError as exc:
        raise SchemaError("Invalid original event UUID") from exc


def to_canonical(events: list[dict[str, Any]], context: SourceContext) -> pa.Table:
    """Map records without filtering, sorting, reconstructing clocks or computing metrics."""
    if not isinstance(events, list) or not events:
        raise SchemaError("Expected nonempty event array")
    rows = []
    ids: set[UUID] = set()
    source_fields = asdict(context)
    for offset, event in enumerate(events):
        if not isinstance(event, dict):
            raise SchemaError(f"Non-object source record at row {offset}")
        uid = _uuid(event.get("id"))
        if uid in ids:
            raise SchemaError(f"Duplicate original event ID at row {offset}")
        ids.add(uid)
        type_id, event_type = _entity(event, "type", required=True)
        stamp = event.get("timestamp")
        if not isinstance(stamp, str) or not re.fullmatch(r"\d{2}:[0-5]\d:[0-5]\d\.\d{3}", stamp):
            raise SchemaError(f"Invalid provider timestamp at row {offset}")
        details = event.get(_DETAILS[event_type]) if event_type in _DETAILS else None
        if event_type in {"Pass", "Shot", "Carry"} and not isinstance(details, dict):
            raise SchemaError(f"Missing/invalid nested {event_type} object at row {offset}")
        if details is None:
            details = {}
        if not isinstance(details, dict):
            raise SchemaError(f"Invalid nested action object at row {offset}")
        row = {
            **source_fields,
            "source_manifest_path": "manifest.json",
            "raw_event_row": offset,
            "normalizer_version": NORMALIZER_VERSION,
            "schema_version": SCHEMA_VERSION,
            "event_id": event["id"],
            "provider_index": _integer(event.get("index"), "index"),
            "period": _integer(event.get("period"), "period"),
            "provider_minute": _integer(event.get("minute"), "minute"),
            "provider_second": _integer(event.get("second"), "second"),
            "period_timestamp": stamp,
            "event_type_id": type_id,
            "event_type": event_type,
            "possession_id": _integer(event.get("possession"), "possession", optional=True),
            "duration_s": _number(event.get("duration"), "duration"),
            "coordinate_system": "raw_statsbomb_120x80",
            "under_pressure": event.get("under_pressure"),
            "quality_flags": [] if event_type in RECOGNIZED_TYPES else ["unrecognized_event_type"],
        }
        if row["provider_index"] < 1 or row["provider_second"] > 59:
            raise SchemaError("Invalid provider sequence/second")
        if row["under_pressure"] is not None and type(row["under_pressure"]) is not bool:
            raise SchemaError("under_pressure must be boolean or null")
        for key, prefix in (
            ("team", "team"),
            ("player", "player"),
            ("possession_team", "possession_team"),
            ("position", "position"),
        ):
            row[f"{prefix}_id"], row[f"{prefix}_name"] = _entity(event, key)
        row["play_pattern_id"], row["play_pattern"] = _entity(event, "play_pattern")
        row["x"], row["y"], row["z"] = _coordinates(event.get("location"), "location")
        row["end_x"], row["end_y"], row["end_z"] = _coordinates(
            details.get("end_location"), "end_location"
        )
        row["recipient_player_id"], row["recipient_player_name"] = _entity(
            details if event_type == "Pass" else {}, "recipient"
        )
        row["outcome_id"], row["outcome"] = _entity(details, "outcome")
        row["pass_outcome"] = row["outcome"] if event_type == "Pass" else None
        row["shot_outcome"] = row["outcome"] if event_type == "Shot" else None
        row["shot_type_id"], row["shot_type"] = _entity(
            details if event_type == "Shot" else {}, "type"
        )
        row["shot_xg"] = _number(
            details.get("statsbomb_xg") if event_type == "Shot" else None, "statsbomb_xg"
        )
        related = event.get("related_events")
        if related is not None:
            if not isinstance(related, list):
                raise SchemaError("related_events must be a list or null")
            for related_id in related:
                _uuid(related_id)
        row["related_event_ids"] = related
        try:
            row["source_record_json"] = json.dumps(
                event, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            )
        except (ValueError, TypeError) as exc:
            raise SchemaError("Source record is not finite JSON") from exc
        rows.append(row)
    try:
        table = pa.Table.from_pylist(rows, schema=EVENT_SCHEMA)
    except (pa.ArrowException, OverflowError) as exc:
        raise SchemaError(f"Cannot encode canonical values: {exc}") from exc
    validate_table(table)
    return table
