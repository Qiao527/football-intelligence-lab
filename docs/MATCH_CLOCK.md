# Period-aware event clock v1 — FIL-004

Implementation: `fil.time.clock` (pure functions and frozen models),
`fil.time.artifacts` (immutable output/verification), `python -m fil.time`
(offline CLI). Version: `fil-period-clock-1`. No dependencies added.

## Three clock meanings

- `period_elapsed_ms`: exact integer milliseconds parsed from the preserved
  provider period timestamp. `period_elapsed_s` is a convenience float view.
  Parsing accepts `HH:MM:SS` with optional 1–3 fractional digits, pads fractional
  precision without rounding, rejects negative/malformed/non-string timestamps.
  Minutes/seconds must be 00–59. Canonical input retains its original spelling.
- `chronological_ms`: sum of preceding observed match-play period durations,
  plus period elapsed time. `chronological_s` is a float view. No fixed 45-minute
  offset, real half-time break, stoppage padding or wall-clock/video claim.
  Match-play periods are 1–4. Period 5 has null chronology and a separate domain.
- `display_clock`: nominal spectator labels with exact seconds/milliseconds.
  For example H1 elapsed 47:00 → `45+2:00.000`; H2 elapsed 0 → `45:00.000`;
  H2 elapsed 50:00 → `90+5:00.000`; ET1 starts `90:00.000`, ET2 `105:00.000`;
  extra-time stoppage is `105+...` / `120+...`. At the exact nominal end use
  `45:00.000` etc.; the next millisecond is `45+0:00.001`. Shootout labels use
  `SO ...`. Display labels, like scalar times, are not unique event identifiers.

`provider_minute`, `provider_second`, `period_timestamp`, period, provider index
and all original canonical fields remain unchanged. Provider minutes alone are
never used for timing or filters. The original canonical schema remains v1;
this is a separate enriched table, not a destructive schema migration.

## Observed boundaries and uncertainty

Derive duration from Half End timestamps. Matching duplicate team markers are
retained with all event IDs; disagreeing end timestamps fail closed rather than
choosing an unexplained boundary. An event after the final Half End, regressing
timestamp/period order or nonzero Half Start also fails. Equal timestamps are
valid and keep provider order/IDs.

If Half End is absent, duration is the largest visible elapsed timestamp and
`period_end_estimated=true`; this is an event-observation estimate, not precise
physical period duration. Estimated earlier durations propagate to subsequent
`chronological_estimated` offsets. A missing end does not make that same period's
timestamp-derived elapsed time or already-known offset uncertain. Missing Half
Start produces a warning and never shifts elapsed times to the first event.
Shorter-than-nominal observed periods are warned, never padded to nominal length.

Observed match-play periods must be a contiguous prefix starting at 1. Missing
intermediate periods fail; no duration is invented. One-/three-period prefixes
are allowed as partial observed data, not evidence of full match completion.
Each match-play duration must be positive. Shootout requires regular periods
1/2 or all four match-play periods; competitions without extra time are allowed.
Shootout may have zero observed duration (one event at elapsed zero).

## Scope and boundary selection

`PeriodRange(period, start_ms, end_ms, include_terminal=False)` uses integer,
nonnegative bounds. Ordinary windows are left-closed/right-open `[start,end)`.
Ranges cannot overlap within a period or extend beyond its observed duration.
There is no ambiguous single elapsed range applied to multiple periods.

`include_terminal=True` may only include that period's duration endpoint. It
includes **all** events at that endpoint, not just Half End markers. This also
preserves the last observed action when a missing end is estimated from it.
A zero-width range is permitted only as an explicit terminal-point selection
at the period endpoint. Arbitrary inclusive internal window boundaries fail.

`partition_period` returns disjoint bins; only the last bin includes the terminal
instant. Therefore every event belongs to exactly one full-period bin, including
equal-time events and both team Half End records. Empty event windows return an
empty typed table; no statistics or fabricated zero metrics are produced.

`select_scope` supports `regular` (1/2), `extra` (3/4), `match_play` (1–4,
default) and explicit `shootout` (5). PeriodRange filters reject period 5 unless
`include_shootout=True` is explicitly passed. All source rows remain in the
stored table; exclusion applies to the selected match-play view only. Ordinary
match-play penalty shots are retained; no xG/score is calculated.

`segments_from_chronological` converts a continuous half-open range to explicit
period ranges, excluding shootouts. At a period boundary the prior Half End and
next Half Start can share the same scalar time. A continuous interval containing
that instant legitimately contains both; a period-relative H2 window never
includes H1 events. Explicit terminal-point segments preserve exact equivalence
to scalar interval selection, including a range starting on a shared boundary.
Do not add epsilon time or merge events to force scalar uniqueness. Stable event
identity/order is period + provider index + original event ID. Optional final
terminal inclusion is allowed only at the last match-play endpoint.

## Enriched Arrow fields

All 53 canonical columns, their types and values are preserved. The clock
schema adds 13 columns and `fil.clock_version` metadata:

| Column | Type | Nullable / meaning |
| --- | --- | --- |
| period_elapsed_ms | int64 | no; exact parsed duration |
| period_elapsed_s | float64 | no; millisecond value / 1000 |
| period_end_ms | int64 | no; observed/estimated period duration |
| period_offset_ms | int64 | null in period 5 |
| period_end_estimated | bool | no; missing Half End fallback |
| chronological_ms | int64 | null in period 5 |
| chronological_s | float64 | null in period 5 |
| chronological_estimated | bool | null in period 5; earlier duration uncertainty |
| display_clock | string | no; period-specific label |
| is_shootout | bool | no; period == 5 |
| clock_version | string | no; fil-period-clock-1 |
| clock_pipeline_git_sha | string | no; caller-supplied matching implementation SHA |
| canonical_manifest_sha256 | string | no; verified FIL-003 artifact manifest digest |

This preserves lineage to canonical manifest → raw manifest/event digest →
original event ID/array offset/source JSON. The canonical implementation SHA is
not replaced; the clock implementation SHA is a separate field. The caller's
SHA is an audit assertion, not a signature; run from the matching clean checkout.

## Persistence, verification and limits

The CLI reverifies the full FIL-002/FIL-003 chain and reads clocks from the exact
canonical byte buffer checked against its recorded digest. Outputs are ignored:

```text
data/interim/clocks/match_id=8658/<canonical-manifest-sha>/fil-period-clock-1/<clock-FIL-SHA>/
  clock_events.parquet
  quality.json
  manifest.json
```

The quality report retains all period marker IDs, estimates/warnings, scope
counts and 15-minute period-bin counts. The manifest binds source/canonical
digests, code/version, exact row count, writer settings, UTC creation time and
output hashes. Parquet settings match FIL-003: 2.6, Zstandard, no dictionaries,
statistics enabled, row groups 65,536. Fixed inputs/code generate identical
tables/Parquet on the verified pinned platform; creation times may differ.

Temporary sibling staging is verified before atomic rename. Existing artifacts
are verified and reused without writes; corrupt/missing/unexpected/symlink
members fail, never silently repair. Output inside either immutable input bundle
is rejected. Failure cleans staging. Offline verify regenerates all canonical
and clock cells, QA, metadata and hashes through the full upstream chain.
Raw and canonical bytes, timestamps, IDs and data rights remain unchanged.

DATA-TIME is the only new technical gate assessed. DEL-TIME-SCORE still requires
independent score reconciliation (FIL-005); no spatial, score, xG/xT, player,
dashboard, AI, acceptance or publication gate follows from this clock. Real
fixture evidence has no extra time or shootout; those cases are TEST-ONLY unit
coverage. No video alignment or wall-clock inference is provided.
