"""Provider-neutral, versioned Arrow contract for source-preserving events."""

from dataclasses import dataclass

import pyarrow as pa

SCHEMA_VERSION = "fil-canonical-events-1"


class SchemaError(ValueError):
    """Canonical or source values violate the declared normalization contract."""


@dataclass(frozen=True)
class SourceContext:
    """Verified source identity, independent of a provider's event structure."""

    source: str
    source_revision: str
    upstream_revision: str
    source_manifest_sha256: str
    pipeline_git_sha: str
    match_id: int
    competition_id: int
    season_id: int
    raw_event_path: str


_REQUIRED = [
    (name, pa.string())
    for name in (
        "source",
        "source_revision",
        "upstream_revision",
        "source_manifest_sha256",
        "source_manifest_path",
        "pipeline_git_sha",
        "raw_event_path",
        "normalizer_version",
        "schema_version",
        "event_id",
        "period_timestamp",
        "event_type",
        "source_record_json",
        "coordinate_system",
    )
] + [
    (name, pa.int64())
    for name in (
        "match_id",
        "competition_id",
        "season_id",
        "raw_event_row",
        "provider_index",
        "period",
        "provider_minute",
        "provider_second",
        "event_type_id",
    )
]
_OPTIONAL = (
    [
        (name, pa.int64())
        for name in (
            "team_id",
            "player_id",
            "possession_id",
            "possession_team_id",
            "play_pattern_id",
            "position_id",
            "recipient_player_id",
            "outcome_id",
            "shot_type_id",
        )
    ]
    + [
        (name, pa.string())
        for name in (
            "team_name",
            "player_name",
            "possession_team_name",
            "play_pattern",
            "position_name",
            "recipient_player_name",
            "outcome",
            "pass_outcome",
            "shot_outcome",
            "shot_type",
        )
    ]
    + [
        (name, pa.float64())
        for name in (
            "x",
            "y",
            "z",
            "end_x",
            "end_y",
            "end_z",
            "duration_s",
            "shot_xg",
        )
    ]
    + [
        ("under_pressure", pa.bool_()),
        ("related_event_ids", pa.list_(pa.field("element", pa.string()))),
    ]
)

EVENT_SCHEMA = pa.schema(
    [pa.field(name, kind, nullable=False) for name, kind in _REQUIRED]
    + [pa.field(name, kind) for name, kind in _OPTIONAL]
    + [pa.field("quality_flags", pa.list_(pa.field("element", pa.string())), nullable=False)],
    metadata={b"fil.schema_version": SCHEMA_VERSION.encode()},
)


def validate_table(table: pa.Table) -> None:
    """Validate shape, nullability, identity, row lineage and provider sequence."""
    if not table.schema.equals(EVENT_SCHEMA, check_metadata=True):
        raise SchemaError("Canonical schema or metadata mismatch")
    if not table.num_rows:
        raise SchemaError("An empty dataset is not a verified match")
    table.validate(full=True)
    for field in EVENT_SCHEMA:
        if not field.nullable and table[field.name].null_count:
            raise SchemaError(f"Null required canonical field: {field.name}")
    identities = list(
        zip(
            table["source"].to_pylist(),
            table["match_id"].to_pylist(),
            table["event_id"].to_pylist(),
            strict=True,
        )
    )
    if len(set(identities)) != table.num_rows:
        raise SchemaError("Duplicate canonical event ID")
    if table["raw_event_row"].to_pylist() != list(range(table.num_rows)):
        raise SchemaError("Source row lineage is not contiguous original file order")
    indexes = table["provider_index"].to_pylist()
    if any(b <= a for a, b in zip(indexes, indexes[1:], strict=False)):
        raise SchemaError("Provider indexes must be strictly increasing; source is not reordered")
    if any(p not in range(1, 6) for p in table["period"].to_pylist()):
        raise SchemaError("Invalid event period")
