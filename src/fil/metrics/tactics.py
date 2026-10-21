"""FIL-012 descriptive passing graphs and native-frame progression, no causal ratings."""

import math
from collections import defaultdict
from dataclasses import dataclass, replace

import pyarrow as pa

from fil.metrics.shots import MatchFilter, apply_filter

VERSION = "fil-tactics-1"
PROGRESSION_VERSION = "fil-progression-1"


class TacticalError(ValueError):
    """Unresolved action semantics or inconsistent tactical evidence."""


ACTION_SCHEMA = pa.schema(
    [
        pa.field(
            name,
            kind,
            nullable=name
            not in {
                "event_id",
                "event_type",
                "period",
                "provider_index",
                "status",
                "reason",
                "progression_reason",
                "source_manifest_sha256",
            },
        )
        for name, kind in (
            [
                (n, pa.string())
                for n in (
                    "event_id",
                    "event_type",
                    "player_name",
                    "recipient_name",
                    "display_clock",
                    "status",
                    "reason",
                    "score_state",
                    "progression_reason",
                    "source_manifest_sha256",
                    "coordinate_system",
                )
            ]
            + [
                (n, pa.int64())
                for n in (
                    "match_id",
                    "team_id",
                    "player_id",
                    "recipient_id",
                    "period",
                    "provider_index",
                    "period_elapsed_ms",
                )
            ]
            + [(n, pa.float64()) for n in ("x", "y", "end_x", "end_y", "delta_x", "distance_gain")]
            + [(n, pa.bool_()) for n in ("progressive", "final_third_entry", "box_entry")]
        )
    ],
    metadata={b"fil.tactics_version": VERSION.encode()},
)
EDGE_SCHEMA = pa.schema(
    [
        ("team_id", pa.int64()),
        ("passer_id", pa.int64()),
        ("recipient_id", pa.int64()),
        ("weight", pa.int64()),
        ("event_ids", pa.list_(pa.string())),
    ]
)
NODE_SCHEMA = pa.schema(
    [
        ("team_id", pa.int64()),
        ("player_id", pa.int64()),
        ("player_name", pa.string()),
        ("x", pa.float64()),
        ("y", pa.float64()),
        ("sample_count", pa.int64()),
        ("x_min", pa.float64()),
        ("x_max", pa.float64()),
        ("y_min", pa.float64()),
        ("y_max", pa.float64()),
        ("sent", pa.int64()),
        ("received", pa.int64()),
        ("event_ids", pa.list_(pa.string())),
        ("position_event_ids", pa.list_(pa.string())),
    ]
)
SUMMARY_SCHEMA = pa.schema(
    [
        ("selection", pa.string()),
        ("team_id", pa.int64()),
        ("selected_events", pa.int64()),
        ("completed_passes", pa.int64()),
        ("directed_pairs", pa.int64()),
        ("progressive_passes", pa.int64()),
        ("observed_carries", pa.int64()),
        ("progressive_carries", pa.int64()),
        ("unresolved_progression", pa.int64()),
        ("final_third_entries", pa.int64()),
        ("box_entries", pa.int64()),
    ]
)


def valid_point(x: float | None, y: float | None) -> bool:
    return (
        x is not None
        and y is not None
        and math.isfinite(x)
        and math.isfinite(y)
        and 0 <= x <= 120
        and 0 <= y <= 80
    )


def progression(row: dict) -> dict:
    """Custom native +x convention, not recovered physical orientation or xT.

    Eligible completed passes/observed carries advance in +x and reduce Euclidean
    distance to the conventional (120,40) goal by >=10 provider units. Invalid
    endpoints are unknown, never zero-valued/imputed or flipped.
    """
    unknown = {
        "progressive": None,
        "final_third_entry": None,
        "box_entry": None,
        "delta_x": None,
        "distance_gain": None,
    }
    if row["status"] not in ("completed", "observed_carry"):
        return {**unknown, "progression_reason": "ineligible_action"}
    if not valid_point(row["x"], row["y"]) or not valid_point(row["end_x"], row["end_y"]):
        return {**unknown, "progression_reason": "missing_or_unsupported_endpoints"}
    x, y, end_x, end_y = (row[k] for k in ("x", "y", "end_x", "end_y"))
    gain = math.hypot(120 - x, 40 - y) - math.hypot(120 - end_x, 40 - end_y)

    def inside(a: float, b: float) -> bool:
        return a >= 102 and 18 <= b <= 62

    return {
        "delta_x": end_x - x,
        "distance_gain": gain,
        "progressive": end_x > x and gain >= 10,
        "final_third_entry": x < 80 <= end_x,
        "box_entry": not inside(x, y) and inside(end_x, end_y),
        "progression_reason": "native_positive_x_convention; physical_direction_unknown",
    }


def select_actions(actions: pa.Table, selected: pa.Table) -> pa.Table:
    ids = set(selected["event_id"].to_pylist())
    return actions.filter(
        pa.array([i in ids for i in actions["event_id"].to_pylist()], type=pa.bool_())
    )


def completed_passes(actions: pa.Table) -> pa.Table:
    return actions.filter(
        pa.array([s == "completed" for s in actions["status"].to_pylist()], type=pa.bool_())
    )


def passing_network(actions: pa.Table) -> tuple[pa.Table, pa.Table]:
    """Distinct native completed-pass IDs; positions use only pass-origin samples.

    Recipient-only nodes have null positions. They and their edges remain in the
    tables even when no faithful map placement is possible. No centrality rating.
    """
    rows = completed_passes(actions).to_pylist()
    ids = [r["event_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise TacticalError("Duplicate completed-pass event IDs")
    edges = defaultdict(list)
    nodes = {}
    for r in rows:
        if any(type(r[k]) is not int for k in ("team_id", "player_id", "recipient_id")):
            raise TacticalError("Completed-pass graph requires native team/passer/recipient IDs")
        edges[r["team_id"], r["player_id"], r["recipient_id"]].append(r["event_id"])
        for identifier, name in (
            (r["player_id"], r["player_name"]),
            (r["recipient_id"], r["recipient_name"]),
        ):
            nodes.setdefault(
                (r["team_id"], identifier),
                {
                    "team_id": r["team_id"],
                    "player_id": identifier,
                    "player_name": name,
                    "sent": 0,
                    "received": 0,
                    "event_ids": [],
                    "samples": [],
                },
            )
        sender = nodes[r["team_id"], r["player_id"]]
        receiver = nodes[r["team_id"], r["recipient_id"]]
        sender["sent"] += 1
        receiver["received"] += 1
        sender["event_ids"].append(r["event_id"])
        if receiver is not sender:
            receiver["event_ids"].append(r["event_id"])
        if valid_point(r["x"], r["y"]):
            sender["samples"].append((r["event_id"], r["x"], r["y"]))
    output = []
    for _, node in sorted(nodes.items()):
        samples = node.pop("samples")
        xs, ys = [s[1] for s in samples], [s[2] for s in samples]
        output.append(
            {
                **node,
                "sample_count": len(samples),
                "x": math.fsum(xs) / len(xs) if xs else None,
                "y": math.fsum(ys) / len(ys) if ys else None,
                "x_min": min(xs) if xs else None,
                "x_max": max(xs) if xs else None,
                "y_min": min(ys) if ys else None,
                "y_max": max(ys) if ys else None,
                "position_event_ids": [s[0] for s in samples],
            }
        )
    return (
        pa.Table.from_pylist(
            [
                {"team_id": t, "passer_id": a, "recipient_id": b, "weight": len(v), "event_ids": v}
                for (t, a, b), v in sorted(edges.items())
            ],
            schema=EDGE_SCHEMA,
        ),
        pa.Table.from_pylist(output, schema=NODE_SCHEMA),
    )


def compare(
    events: pa.Table,
    actions: pa.Table,
    teams: tuple[int, ...],
    selections: list[tuple[str, MatchFilter]],
) -> pa.Table:
    """Explicit temporal/context selections; raw counts, no fabricated exposure/rates."""
    result = []
    for label, state in selections:
        for team in teams:
            if state.team_id is not None and state.team_id != team:
                continue
            selected = apply_filter(events, replace(state, team_id=team))
            rows = select_actions(actions, selected).to_pylist()
            passes = [r for r in rows if r["status"] == "completed"]
            result.append(
                {
                    "selection": label,
                    "team_id": team,
                    "selected_events": selected.num_rows,
                    "completed_passes": len(passes),
                    "directed_pairs": len({(r["player_id"], r["recipient_id"]) for r in passes}),
                    "progressive_passes": sum(r["progressive"] is True for r in passes),
                    "observed_carries": sum(r["status"] == "observed_carry" for r in rows),
                    "progressive_carries": sum(
                        r["event_type"] == "Carry" and r["progressive"] is True for r in rows
                    ),
                    "unresolved_progression": sum(
                        r["status"] in ("completed", "observed_carry") and r["progressive"] is None
                        for r in rows
                    ),
                    "final_third_entries": sum(r["final_third_entry"] is True for r in rows),
                    "box_entries": sum(r["box_entry"] is True for r in rows),
                }
            )
    return pa.Table.from_pylist(result, schema=SUMMARY_SCHEMA)


@dataclass(frozen=True)
class TacticalFacts:
    actions: pa.Table
    edges: pa.Table
    nodes: pa.Table
    quality: dict
