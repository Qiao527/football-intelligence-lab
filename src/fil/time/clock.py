"""Exact millisecond clock derivation over a complete, verified canonical event table."""

import re
from dataclasses import asdict, dataclass
from typing import Any

import pyarrow as pa

from fil.schema import EVENT_SCHEMA, validate_table

CLOCK_VERSION = "fil-period-clock-1"
_NOMINAL = {1: 2_700_000, 2: 2_700_000, 3: 900_000, 4: 900_000}
_DISPLAY_BASE = {1: 0, 2: 45, 3: 90, 4: 105}
_TIME_FIELDS = [
    pa.field("period_elapsed_ms", pa.int64(), nullable=False),
    pa.field("period_elapsed_s", pa.float64(), nullable=False),
    pa.field("period_end_ms", pa.int64(), nullable=False),
    pa.field("period_offset_ms", pa.int64()),
    pa.field("period_end_estimated", pa.bool_(), nullable=False),
    pa.field("chronological_ms", pa.int64()),
    pa.field("chronological_s", pa.float64()),
    pa.field("chronological_estimated", pa.bool_()),
    pa.field("display_clock", pa.string(), nullable=False),
    pa.field("is_shootout", pa.bool_(), nullable=False),
    pa.field("clock_version", pa.string(), nullable=False),
    pa.field("clock_pipeline_git_sha", pa.string(), nullable=False),
    pa.field("canonical_manifest_sha256", pa.string(), nullable=False),
]
CLOCK_SCHEMA = pa.schema(
    list(EVENT_SCHEMA) + _TIME_FIELDS,
    metadata={**EVENT_SCHEMA.metadata, b"fil.clock_version": CLOCK_VERSION.encode()},
)


class ClockError(ValueError):
    """Source clock or requested range has invalid/ambiguous semantics."""


def _nonnegative_int(value: Any, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ClockError(f"{label} must be a nonnegative integer millisecond value")


def parse_period_timestamp(value: str) -> int:
    """Parse a duration HH:MM:SS[.sss] without floating-point rounding or minute inference."""
    if not isinstance(value, str):
        raise ClockError("Provider timestamp must be a string")
    match = re.fullmatch(r"([0-9]{2}):([0-5][0-9]):([0-5][0-9])(?:\.([0-9]{1,3}))?", value)
    if match is None:
        raise ClockError(f"Invalid period timestamp: {value!r}")
    hours, minutes, seconds = (int(match[i]) for i in (1, 2, 3))
    millis = int((match[4] or "").ljust(3, "0"))
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def display_clock(period: int, elapsed_ms: int) -> str:
    """Spectator display with exact seconds/ms; period remains part of event identity."""
    _nonnegative_int(elapsed_ms, "elapsed")
    if type(period) is not int or period not in range(1, 6):
        raise ClockError("Invalid period")
    if period == 5:
        minutes, rest = divmod(elapsed_ms, 60_000)
        return f"SO {minutes}:{rest // 1000:02d}.{rest % 1000:03d}"
    nominal = _NOMINAL[period]
    if elapsed_ms > nominal:
        extra, rest = divmod(elapsed_ms - nominal, 60_000)
        end_minute = _DISPLAY_BASE[period] + nominal // 60_000
        return f"{end_minute}+{extra}:{rest // 1000:02d}.{rest % 1000:03d}"
    minutes, rest = divmod(elapsed_ms, 60_000)
    return f"{_DISPLAY_BASE[period] + minutes}:{rest // 1000:02d}.{rest % 1000:03d}"


@dataclass(frozen=True)
class PeriodInfo:
    period: int
    duration_ms: int
    offset_ms: int | None
    end_estimated: bool
    offset_estimated: bool | None
    half_start_event_ids: tuple[str, ...]
    half_end_event_ids: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class PeriodRange:
    """A period-relative [start,end) range, with explicit inclusion of its terminal instant."""

    period: int
    start_ms: int
    end_ms: int
    include_terminal: bool = False

    def __post_init__(self) -> None:
        if type(self.period) is not int or self.period not in range(1, 6):
            raise ClockError("Range period must be 1..5")
        _nonnegative_int(self.start_ms, "range start")
        _nonnegative_int(self.end_ms, "range end")
        if type(self.include_terminal) is not bool:
            raise ClockError("include_terminal must be boolean")
        if self.end_ms < self.start_ms or (
            self.end_ms == self.start_ms and not self.include_terminal
        ):
            raise ClockError("Empty/reversed range without explicit terminal point")


def derive_clock(
    canonical: pa.Table,
    pipeline_revision: str,
    canonical_manifest_sha256: str,
) -> tuple[pa.Table, tuple[PeriodInfo, ...]]:
    """Append clocks without changing canonical columns, source order, timestamps or IDs."""
    validate_table(canonical)
    if not re.fullmatch(r"[0-9a-f]{40}", pipeline_revision):
        raise ClockError("Expected full clock implementation SHA")
    if not re.fullmatch(r"[0-9a-f]{64}", canonical_manifest_sha256):
        raise ClockError("Expected canonical manifest SHA-256")
    for key in ("source", "match_id", "source_revision", "source_manifest_sha256"):
        if len(set(canonical[key].to_pylist())) != 1:
            raise ClockError("Clock input must be one verified source/match/revision")
    rows = canonical.select(["event_id", "period", "period_timestamp", "event_type"]).to_pylist()
    elapsed = [parse_period_timestamp(r["period_timestamp"]) for r in rows]
    period_order = [r["period"] for r in rows]
    if period_order != sorted(period_order):
        raise ClockError("Periods regress in provider order; input is never silently reordered")
    observed = sorted(set(period_order))
    play = [p for p in observed if p != 5]
    if not play or play != list(range(1, play[-1] + 1)):
        raise ClockError("Missing/discontinuous match-play periods; no durations are invented")
    if 5 in observed and play[-1] not in (2, 4):
        raise ClockError("Shootout requires observed complete regular or extra-time periods")
    info = []
    offset, offset_estimated = 0, False
    for period in observed:
        positions = [i for i, r in enumerate(rows) if r["period"] == period]
        times = [elapsed[i] for i in positions]
        if times != sorted(times):
            raise ClockError(f"Period {period} timestamps regress in provider order")
        starts = [i for i in positions if rows[i]["event_type"] == "Half Start"]
        ends = [i for i in positions if rows[i]["event_type"] == "Half End"]
        if any(elapsed[i] != 0 for i in starts):
            raise ClockError(f"Period {period} has a nonzero Half Start")
        duration = max(elapsed[i] for i in ends) if ends else max(times)
        if duration < max(times):
            raise ClockError(f"Period {period} contains an event after the final Half End")
        if duration == 0 and period != 5:
            raise ClockError(f"Period {period} has no positive observed duration")
        warnings = []
        if not starts:
            warnings.append("half_start_missing")
        if not ends:
            warnings.append("period_end_estimated_from_max_observed_timestamp")
        if len({elapsed[i] for i in ends}) > 1:
            raise ClockError(f"Period {period} has conflicting Half End markers")
        if period != 5 and duration < _NOMINAL[period]:
            warnings.append("observed_period_shorter_than_nominal_no_padding")
        info.append(
            PeriodInfo(
                period,
                duration,
                None if period == 5 else offset,
                not bool(ends),
                None if period == 5 else offset_estimated,
                tuple(rows[i]["event_id"] for i in starts),
                tuple(rows[i]["event_id"] for i in ends),
                tuple(warnings),
            )
        )
        if period != 5:
            offset += duration
            offset_estimated = offset_estimated or not bool(ends)
    by_period = {p.period: p for p in info}
    values = {field.name: [] for field in _TIME_FIELDS}
    for row, ms in zip(rows, elapsed, strict=True):
        p = by_period[row["period"]]
        chronological = None if p.offset_ms is None else p.offset_ms + ms
        new = {
            "period_elapsed_ms": ms,
            "period_elapsed_s": ms / 1000,
            "period_end_ms": p.duration_ms,
            "period_offset_ms": p.offset_ms,
            "period_end_estimated": p.end_estimated,
            "chronological_ms": chronological,
            "chronological_s": None if chronological is None else chronological / 1000,
            "chronological_estimated": p.offset_estimated,
            "display_clock": display_clock(p.period, ms),
            "is_shootout": p.period == 5,
            "clock_version": CLOCK_VERSION,
            "clock_pipeline_git_sha": pipeline_revision,
            "canonical_manifest_sha256": canonical_manifest_sha256,
        }
        for name, value in new.items():
            values[name].append(value)
    table = pa.Table.from_arrays(
        [canonical[f.name] for f in EVENT_SCHEMA]
        + [pa.array(values[f.name], type=f.type) for f in _TIME_FIELDS],
        schema=CLOCK_SCHEMA,
    )
    return table, tuple(info)


def _bounds(table: pa.Table) -> dict[int, tuple[int, int | None]]:
    if not table.schema.equals(CLOCK_SCHEMA, check_metadata=True):
        raise ClockError("Expected versioned clock schema")
    result = {}
    for row in table.select(["period", "period_end_ms", "period_offset_ms"]).to_pylist():
        value = row["period_end_ms"], row["period_offset_ms"]
        if row["period"] in result and result[row["period"]] != value:
            raise ClockError("Inconsistent period clock bounds")
        result[row["period"]] = value
    return result


def select_segments(
    table: pa.Table,
    segments: tuple[PeriodRange, ...],
    *,
    include_shootout: bool = False,
) -> pa.Table:
    """Select disjoint explicit ranges; no minute-only or implicit shootout filtering."""
    if type(include_shootout) is not bool:
        raise ClockError("include_shootout must be boolean")
    bounds = _bounds(table)
    prior: dict[int, PeriodRange] = {}
    for segment in sorted(segments, key=lambda s: (s.period, s.start_ms, s.end_ms)):
        if segment.period not in bounds:
            raise ClockError("Requested period is absent")
        if segment.period == 5 and not include_shootout:
            raise ClockError("Shootout selection must be explicitly enabled")
        duration = bounds[segment.period][0]
        if segment.end_ms > duration or (segment.include_terminal and segment.end_ms != duration):
            raise ClockError("Range exceeds duration or includes a non-terminal endpoint")
        previous = prior.get(segment.period)
        if previous and (
            segment.start_ms < previous.end_ms
            or (segment.start_ms == previous.end_ms and previous.include_terminal)
        ):
            raise ClockError("Overlapping/duplicate period ranges")
        prior[segment.period] = segment
    mask = [
        any(
            r.period == p
            and (
                r.start_ms <= ms < r.end_ms
                or (r.include_terminal and ms == r.end_ms and ms >= r.start_ms)
            )
            for r in segments
        )
        for p, ms in zip(
            table["period"].to_pylist(), table["period_elapsed_ms"].to_pylist(), strict=True
        )
    ]
    return table.filter(pa.array(mask, type=pa.bool_()))


def select_scope(table: pa.Table, scope: str = "match_play") -> pa.Table:
    """Default match-play includes regular/extra time; shootout is a separate explicit scope."""
    scopes = {"match_play": {1, 2, 3, 4}, "regular": {1, 2}, "extra": {3, 4}, "shootout": {5}}
    if scope not in scopes:
        raise ClockError("Unknown clock scope")
    ranges = tuple(
        PeriodRange(p, 0, duration, True)
        for p, (duration, _) in _bounds(table).items()
        if p in scopes[scope]
    )
    return select_segments(table, ranges, include_shootout=scope == "shootout")


def partition_period(
    table: pa.Table, period: int, width_ms: int = 900_000
) -> tuple[PeriodRange, ...]:
    """Partition a whole observed period; only the last bin includes the terminal instant."""
    _nonnegative_int(width_ms, "bin width")
    bounds = _bounds(table)
    if type(period) is not int or not width_ms or period not in bounds:
        raise ClockError("Positive bin width and an observed period are required")
    duration = bounds[period][0]
    if duration == 0:
        return (PeriodRange(period, 0, 0, True),)
    return tuple(
        PeriodRange(period, start, min(start + width_ms, duration), start + width_ms >= duration)
        for start in range(0, duration, width_ms)
    )


def segments_from_chronological(
    table: pa.Table,
    start_ms: int,
    end_ms: int,
    *,
    include_terminal: bool = False,
) -> tuple[PeriodRange, ...]:
    """Convert a continuous match-play interval to period ranges, never including shootouts."""
    if type(include_terminal) is not bool:
        raise ClockError("include_terminal must be boolean")
    _nonnegative_int(start_ms, "chronological start")
    _nonnegative_int(end_ms, "chronological end")
    bounds = _bounds(table)
    play = {p: (duration, offset) for p, (duration, offset) in bounds.items() if p != 5}
    total = max(offset + duration for duration, offset in play.values()) if play else 0
    if not start_ms < end_ms <= total or (include_terminal and end_ms != total):
        raise ClockError("Invalid chronological range or non-final terminal inclusion")
    segments = []
    for period, (duration, offset) in sorted(play.items()):
        lo = max(0, start_ms - offset)
        hi = min(duration, end_ms - offset)
        boundary = offset + duration
        terminal = start_ms <= boundary < end_ms or (include_terminal and boundary == end_ms)
        if lo < hi:
            segments.append(PeriodRange(period, lo, hi, terminal and hi == duration))
        elif lo == hi == duration and terminal:
            segments.append(PeriodRange(period, duration, duration, True))
    return tuple(segments)


def clock_report(table: pa.Table, periods: tuple[PeriodInfo, ...]) -> dict[str, Any]:
    """Clock QA/assumptions, preserving source counts and explicit scope/domain distinctions."""
    partition_counts = {}
    for p in periods:
        bins = partition_period(table, p.period)
        partition_counts[str(p.period)] = [
            select_segments(table, (b,), include_shootout=p.period == 5).num_rows for b in bins
        ]
    return {
        "clock_version": CLOCK_VERSION,
        "row_count": table.num_rows,
        "unique_event_ids": len(set(table["event_id"].to_pylist())),
        "periods": [asdict(p) for p in periods],
        "scope_counts": {
            s: select_scope(table, s).num_rows
            for s in ("regular", "extra", "match_play", "shootout")
        },
        "fifteen_minute_period_bin_counts": partition_counts,
        "warnings": [
            "Event-phase axis excludes real half-time breaks; not a video/wall clock.",
            "Boundary markers in adjacent periods may share a scalar timestamp.",
            "No score, xG/xT, spatial, player or UI gates are evaluated.",
        ],
        "gate_assessment": "DATA-TIME technical checks only; not DEL-TIME-SCORE or acceptance",
    }
