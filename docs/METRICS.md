# Source shot/xG and window metrics — fil-source-xg-1

Grain: one verified historical match. Inputs: immutable FIL-005 event states,
provider event IDs/order/period, native x/y, shot_type/outcome/xG and FIL-004
exact clock/provenance. All calculations are Python functions in metrics/shots.py;
no math is hidden in the UI. Data rights remain local noncommercial research.

- Shots: event_type=Shot, periods 1–4. Ordinary/extra-time penalties included;
  period-5 shootout excluded. Own-goal records are not shots and add no shot xG.
  A count of Shot/Goal can differ from the official score due to own goals.
- xG(T,W) = fsum(provider shot_xg) for included team T shots in W. Units: expected
  goals / sum of source-provided per-shot probabilities. NPxG adds exclusion
  shot_type=Penalty. No generated, trained, guessed or substituted probabilities.
  Every included shot requires finite xG in [0,1], team/type/outcome; missing xG
  is a hard failure. Source model internals/version beyond metadata are unknown;
  results are not assumed comparable across other providers/model releases.
- Cumulative xG: stable (period,provider_index) sequence of those source shots;
  each point retains its original ID/source manifest. UI adds zero-start and
  terminal hold anchors only for rendering, never fake source events. Equal-time
  shots remain separate updates. Full-match background persists under filtering;
  selected points are highlighted, never silently reset to zero.
- Window threat = xG sum in a period-specific 5/10/15-minute bin. It is not
  control, momentum prediction, pressure efficiency or xT. Each bin is [start,end)
  except the observed period's terminal endpoint is included exactly once.
  H1 stoppage/H2 opening remain distinct. Short final bins use actual exposure.
  Persist width_ms, exact bounds, period, terminal flag and original event IDs.
  Also record shot_count, mean_xg (null for no shots), xg_per_minute=sum/exposure.
  No-shot verified windows have count/sum zero, not a fabricated mean or rating.
  Compare different widths with exposure in mind; no causal conclusions.
- Map: source-native StatsBomb 120×80. Y is rendered downward; no coordinate
  mutation or team/period direction flip is inferred. Null locations stay in
  shot totals/table and are omitted from map markers; out-of-range/nonfinite
  coordinates block map publication. This validates bounds, not spatial-direction
  normalization or continuous player tracking. Size=8+22*sqrt(xG) pixels (8–30),
  star=Shot/Goal, circle=other source outcome. Own goals are in the score/ledger.

Shared MatchFilter is the sole foreground selection: tuple of typed PeriodRange
plus optional acting team/player/event type/outcome. It applies once, then all
selected charts/KPIs/ledger/evidence derive from exactly those IDs. Shootout is
not exposed in this match-play Explorer. Scoreboard is official full match;
score-state and cumulative backgrounds are explicitly full-match context.
Clear/reset clears period, window, team, player, type, outcome and event evidence.
A chart selection carries event IDs or exact period/range tuples, not point indexes.

Facts: shots.parquet preserves all FIL-005 columns; xg_cumulative.parquet uses
explicit typed ID/team/period/index/chronology/display/xg/cumulative/version/
source-manifest fields; window_threat.parquet fixes typed team/count/xg/NPxG/
nullable mean/event-ID-list/version/period/width/bounds/terminal/nullable rate.
quality.json and manifest.json bind code/version, input content fingerprint,
source/score manifest digests, file sizes/SHA-256, UTC generation, writer/PyArrow
and unchanged rights. Output is staged and never silently overwrites corruption;
reuse recomputes expected files/manifest. Same inputs/code on this pinned platform
produce identical fact/QA bytes. New manifest timestamps may differ. App cache
keys include actual input bytes, preventing stale analytics after source changes.
Local-config.json only identifies local bundle paths and remains ignored.

Numerical invariants: unique shot IDs, fsum team totals equal raw-source sums;
last cumulative point equals team total; all bin IDs partition each included
shot once; independent recomputation agrees at absolute tolerance 1e-12 for
floating-point regrouping. Raw/canonical/clock/score records remain unchanged.


Spatial metadata and uncertainty are defined in [SPATIAL.md](SPATIAL.md).
`raw_statsbomb_120x80` and a world-fixed frame are distinct. Observed goal
endpoints corroborate the identity shot display; physical attacking ends remain
unknown. No team/period flip is applied. Cache keys include input file bytes,
logical bundle roles and directory structure; invalid/symlink roots fail before
cached verification can be reused. Every cache miss still recomputes the complete
source → canonical → clock → score verification chain.
