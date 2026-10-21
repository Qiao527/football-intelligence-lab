"""Source xG v1: explicit match-play domain, exact lineage, no model fitting."""

import math
from collections import defaultdict
from dataclasses import dataclass

import pyarrow as pa
import pyarrow.compute as pc

from fil.time.clock import CLOCK_SCHEMA, PeriodRange, partition_period, select_segments

METRIC_VERSION = "fil-source-xg-1"


class MetricError(ValueError):
    """Unusable source probabilities, identity, coordinates or filter scope."""


@dataclass(frozen=True)
class MatchFilter:
    segments: tuple[PeriodRange, ...]
    team_id: int | None = None
    player_id: int | None = None
    event_type: str | None = None
    outcome: str | None = None


def clock_view(events: pa.Table) -> pa.Table:
    return events.select(CLOCK_SCHEMA.names).replace_schema_metadata(CLOCK_SCHEMA.metadata)


def apply_filter(events: pa.Table, state: MatchFilter) -> pa.Table:
    """One selector for every panel; ranges are period-aware and default to no shootout."""
    selected = set(select_segments(clock_view(events), state.segments)["event_id"].to_pylist())
    mask = [
        r["event_id"] in selected
        and (state.team_id is None or r["team_id"] == state.team_id)
        and (state.player_id is None or r["player_id"] == state.player_id)
        and (state.event_type is None or r["event_type"] == state.event_type)
        and (state.outcome is None or r["outcome"] == state.outcome)
        for r in events.select(
            ["event_id", "team_id", "player_id", "event_type", "outcome"]
        ).to_pylist()
    ]
    return events.filter(pa.array(mask, type=pa.bool_()))


def build_shots(events: pa.Table) -> pa.Table:
    """All match-play Shot rows, penalties included; unknown/missing xG fail publication."""
    if len(set(events["event_id"].to_pylist())) != events.num_rows:
        raise MetricError("Duplicate event IDs")
    result = events.filter(
        pc.and_(
            pc.equal(events["event_type"], "Shot"),
            pc.is_in(events["period"], value_set=pa.array([1, 2, 3, 4], type=pa.int64())),
        )
    )
    for r in result.to_pylist():
        xg = r["shot_xg"]
        if xg is None or not math.isfinite(xg) or not 0 <= xg <= 1:
            raise MetricError(f"Invalid/missing source xG: {r['event_id']}")
        if r["team_id"] is None or r["shot_type"] is None or r["shot_outcome"] is None:
            raise MetricError("Missing shot team/type/outcome")
        for name, bound in (("x", 120), ("y", 80)):
            v = r[name]
            if v is not None and (not math.isfinite(v) or not 0 <= v <= bound):
                raise MetricError(f"Invalid source-native coordinate {name}")
    return result


def totals(shots: pa.Table, team_id: int) -> dict:
    """A complete empty shot selection is a count/sum of zero; mean quality stays null."""
    rows = [r for r in shots.to_pylist() if r["team_id"] == team_id]
    return {
        "team_id": team_id,
        "shot_count": len(rows),
        "xg": math.fsum(r["shot_xg"] for r in rows),
        "non_penalty_xg": math.fsum(r["shot_xg"] for r in rows if r["shot_type"] != "Penalty"),
        "mean_xg": math.fsum(r["shot_xg"] for r in rows) / len(rows) if rows else None,
        "event_ids": [r["event_id"] for r in rows],
        "metric_version": METRIC_VERSION,
    }


def cumulative(shots: pa.Table) -> list[dict]:
    """Source-only step points, stable provider order; UI holds/adds explicit non-shot anchors."""
    history = defaultdict(list)
    result = []
    for r in sorted(shots.to_pylist(), key=lambda r: (r["period"], r["provider_index"])):
        history[r["team_id"]].append(r["shot_xg"])
        result.append(
            {
                "event_id": r["event_id"],
                "team_id": r["team_id"],
                "period": r["period"],
                "provider_index": r["provider_index"],
                "chronological_ms": r["chronological_ms"],
                "display_clock": r["display_clock"],
                "xg": r["shot_xg"],
                "cumulative_xg": math.fsum(history[r["team_id"]]),
                "metric_version": METRIC_VERSION,
                "source_manifest_sha256": r["source_manifest_sha256"],
            }
        )
    return result


def window_threat(events: pa.Table, teams: tuple[int, ...], width_ms: int) -> list[dict]:
    """Transparent period-bin sum of source xG, not possession/control/pressing intensity."""
    clock = clock_view(events)
    result = []
    all_shots = build_shots(events)
    records = all_shots.to_pylist()
    for period in sorted(set(events["period"].to_pylist()) - {5}):
        for segment in partition_period(clock, period, width_ms):
            shot_rows = all_shots.filter(
                pa.array(
                    [
                        r["period"] == period
                        and (
                            segment.start_ms <= r["period_elapsed_ms"] < segment.end_ms
                            or segment.include_terminal
                            and r["period_elapsed_ms"] == segment.end_ms
                        )
                        for r in records
                    ],
                    type=pa.bool_(),
                )
            )
            duration = (segment.end_ms - segment.start_ms) / 60000
            for team in teams:
                result.append(
                    {
                        **totals(shot_rows, team),
                        "period": period,
                        "width_ms": width_ms,
                        "start_ms": segment.start_ms,
                        "end_ms": segment.end_ms,
                        "include_terminal": segment.include_terminal,
                        "xg_per_minute": totals(shot_rows, team)["xg"] / duration
                        if duration
                        else None,
                    }
                )
    return result
