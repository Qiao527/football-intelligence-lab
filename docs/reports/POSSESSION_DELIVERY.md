# Source-traceable possession processes — first v0.5 slice

Development branch `feat/fil-v05-possession-flow`, stacked on unchanged PR #10 /
`feat/fil-012-tactical-dashboard` at
`2645eb916e0a1980eb6e650c494ce8395a7ebd32`. Runtime and immutable artifact revision:
`f8ff810152179e6e98de8958f45dbf4861d72c21`. Later delivery commits only record
verification evidence. No change to PR #7/#8/#10, merge, deployment or data rights.

## Implementation and interpretation

Provider-labelled possession reconstruction and typed ordered sequences retain
every original record, including opposition and administrative events. The local
Possession Flow view adds full-chain entry/exit facts, recorded pass/carry paths,
repeated/backward zone visits, conditional native progression/entries, conservative
turnover endings, zero/multi-shot sequences and source xG. Shared filters choose
touched possessions; the full context ledger marks which original records match
the filter. Bar/endpoint clicks and original-event selectors support exact source
ID/JSON/manifest drilldown. Metric numerators and denominators are explicit.

[POSSESSIONS.md](../POSSESSIONS.md) is the metric dictionary: provider semantics,
owner-action vocabulary, source inclusion/exclusion, nulls, terminal priority,
zone/progression conventions, eligibility/exposure, uncertainty and source IDs.
It follows Handbook §13 and Master Reference §3.3; the requested first factual
v0.5 slice does not implement player ratings/candidates or causal bottlenecks.

Raw StatsBomb revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`, fixture 8658,
2018 France–Croatia final. Source manifest SHA-256:
`f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c`.
Coordinates are original 120×80 provider units, y down; physical attacking ends
remain unknown. No silent flip, inferred off-ball path, intention or rating.

## Independently verified real-source results

- **2,978 events / 182 native possession IDs**, preserving all original IDs once
  in the action table and every source-labelled member once in its possession.
  **594 opposition-context records** remain in their native groups.
- Native ID **91 crosses the half-time boundary**. It is retained with an explicit
  quality warning and null continuous span/time-to-shot, rather than resegmented.
- **181 analytically eligible possessions** (one administrative-only ID retained
  outside the denominator). **113** have observed conventional final-third
  evidence; **41** of those have box evidence. These include starts in those zones.
- **23 shots across 21 possessions**, **19 shot-ending possessions** under the
  last-owner-action definition. Multiple shots within one possession are retained.
  Combined source xG **2.5782512977**; conditional shot/final-third ratio **21/113**
  and box/final-third ratio **41/113**. First-shot span median **9.467s** over 21
  same-period shot-producing possessions; this is a selected subset, not every
  possession's attack duration.
- **36 supported turnover endings**, 26 foul-observed, 16 out/offside, one recorded
  own goal, 19 shot, two period-boundary and **82 unresolved** provider endings.
  A team change alone is insufficient to infer a turnover; next-owner restarts
  explicitly exclude that label. These are conservative categories, not all losses.
- Owner-labelled process actions include **634 completed passes / 574 carries**,
  **206 progressive actions**, **94 final-third entries / 25 box entries**.
  The full Tactical Dashboard still has **650 completed passes / 617 carries**;
  native possession-owner labels place the remaining movement records in
  opposition context. All are preserved; no owner is relabelled to force totals.
- Original team xG unchanged: France eight shots / **1.097963608 xG** /
  **0.314463608 NPxG**; Croatia 15 shots / **1.4802876897 xG/NPxG**.
  Independent score reconstruction remains **France 4–2 Croatia**, with six goal
  awards including one linked own goal and one match-play penalty goal.

The independent verifier derives expected native groups, order, actors, start/end
coordinates, paths/revisits, entry/exit states, supported losses, shots/xG,
durations and nulls directly from original JSON. It checks **480** period/window/
acting-team/score-state cohort queries, covering all 5/10/15-minute bins.
Existing Tactical verification passes its **160** queries; existing Explorer
verification passes 23 shot/cumulative points and 80 team/window rows. All 2,978
per-event score states independently reconcile.

All **23 original input files**, including local config, retain SHA-256 and
nanosecond modification time. Four new possession artifact files retain bytes/
mtime on recomputation/reuse. No original bundles were overwritten or repaired.
The final immutable local bundle is:
`data/interim/possessions/8cbc37c73a3e8108f4076a74f6769deb121a561081f953e493f332c6cfd96b97/fil-possession-1/f8ff810152179e6e98de8958f45dbf4861d72c21`.
Its two Parquet tables, quality JSON and manifest record input chain, code SHA,
`fil-possession-1`, inherited `fil-tactics-1` / `fil-progression-1`, UTC generation,
Arrow/writer settings and unchanged local-research rights. Provider data,
configs, screenshots and browser reports remain ignored and were not pushed.

## Tactical performance investigation

cProfile identified repeated Plotly `add_annotation` work: 194 calls consumed
7.199 profiled seconds, repeatedly copying/validating the growing annotation
array. Profiling adds overhead and is not the browser startup measurement.
The fix constructs the same arrow dictionaries and assigns the array once.
Both complete real-team chart JSON payloads equal the parent exactly, including
all **194** arrows, directions, positions, traces and labels. No thinning,
removed interaction, altered football calculation or skipped verification.

App code also reuses the fingerprint associated with the already verified
snapshot when keying derived views. The full input tree is still hashed on every
rerun, and the complete source/normalization/clock/score verification runs on a
verification cache miss. Immutable generated artifacts recompute/reconcile and
check input fingerprints before/after as before. No integrity checks were disabled.

Three fresh-server/browser runs use the same config, 1600×1150 viewport, original
navigation→Event ledger milestone and an added tactical milestone (View click→
source-count/chart/axis/comparison readiness). No OS cache eviction or preload.
The unchanged parent was extracted with `git archive 2645eb9` to
`/tmp/fil-v05-parent`; `PYTHONPATH` selects it while the benchmark script and
locked environment remain the same. Controls measure period 2, then France.

| Seconds | Unchanged PR #10 parent | Optimized runtime |
| --- | ---: | ---: |
| Tactical opening run 1 | 4.925 | 2.309 |
| Run 2 | 5.215 | 2.472 |
| Run 3 | 4.019 | 2.265 |
| Tactical opening median | **4.925** | **2.309** |
| Period-filter median | **3.261** | **1.628** |
| Team-filter median | **1.818** | **1.043** |
| Original Explorer cold ledger median | **4.532** | **3.706** |
| Navigation→evidence element median | 5.525 | 5.353 |

Observed tactical opening median improves **53.1%**, period filtering **50.1%**,
team filtering **42.6%**. Cold ledger samples are variable (parent 3.511–6.606s;
current 3.548–4.960s), so this does not establish a general cold-start speedup.
The earlier **6.545s** tactical opening remains documented in the v0.4 report.
**The ≤3s original cold-start budget remains unmet**, as do several usual
0.5–1s tactical interaction targets. No global performance acceptance claimed.

Measurements are retained under `data/interim/v05-benchmark-parent` and
`data/interim/v05-benchmark-current`. The subsequent version-metadata changes
have no effect on the default/tactical render paths measured here.

## Commands and final checks

Linux x86_64, CPython 3.11.14, uv 0.12.23, unchanged frozen dependencies. Commands
run from repository root with `UV_CACHE_DIR=/tmp/fil-uv-cache`. `CONFIG` denotes
the existing absolute local config in `data/interim/delivery-match/metrics/.../`
`d0ea933c8aa9432b10eaabd62000219d1f0e1c98/local-config.json`; `BUNDLE` is above.
Final commands below exited **0**:

| Command | Actual result |
| --- | --- |
| `uv lock --check` / `uv sync --frozen` | Manifest/lock agree; frozen editable environment installed |
| `uv run --frozen ruff check .` | All checks passed |
| `uv run --frozen pytest -q` | **342 passed**, zero skipped, 8.07s |
| `uv build` | Wheel and source distribution built |
| `UV_PROJECT_ENVIRONMENT=/tmp/fil-v05-final-regular uv sync --frozen --no-editable --reinstall-package football-intelligence-lab` | Empty regular environment, pinned Python via `UV_PYTHON`, current package rebuilt |
| Same environment `uv run --frozen --no-editable ruff check .` | All checks passed |
| Same environment `uv run --frozen --no-editable pytest -q` | **342 passed**, zero skipped, 10.42s |
| Same environment `uv run --frozen --no-editable python -m fil.possessions.artifacts --help` | Installed CLI works; also added to hosted CI |
| `uv run --frozen python -m fil.possessions.artifacts --config CONFIG --pipeline-revision f8ff810152179e6e98de8958f45dbf4861d72c21 --output data/interim/possessions` | Immutable bundle generated and reused without changes |
| `uv run --frozen python scripts/verify_possessions_source.py CONFIG BUNDLE` | Independent raw reconciliation and 480 queries PASS |
| Existing `verify_tactics_source.py CONFIG TACTICAL_BUNDLE` | Existing tactical facts / 160 queries PASS |
| Existing `verify_explorer_source.py CONFIG` | Existing shots/xG/windows/spatial lineage PASS |
| Existing `verify_score_source.py RAW CANONICAL CLOCK SCORE` | Independent raw score and all event states PASS |
| `PYTHONPATH=/tmp/fil-v05-parent/src uv run --frozen --group browser python scripts/benchmark_explorer.py CONFIG --output data/interim/v05-benchmark-parent --port 8507 --tactical` | Three parent runs, original milestone plus tactical opening/filters |
| Same benchmark without parent `PYTHONPATH`, output `data/interim/v05-benchmark-current` | Three optimized runs; all source counts/charts verified |

Self-review/regressions cover native membership, tied timestamps, backward and
repeated entries, missing/unassigned IDs, unknown owners, half/stoppage/cross-period
boundaries, shootout exclusion, explicit versus unsupported turnover evidence,
next-possession restarts, zero/multi-shot and conditional possession denominators,
null positions, exact source identity, immutable corruption/extra/symlink/manifest
rejection, shared UI context/empty/reset states and arrow direction preservation.
Inherited metric versions are explicitly stored in tables/QA/manifest.

Initial development failures identified a test fixture assigning two owners to
one ID, the need for an explicit unknown-owner context role, and a browser
selection racing a rerender. These were corrected and regression checked.
A regular-install build initially lacked sandbox network permission for the
already pinned backend; the authorized network-enabled clean install/build
passed. No test or verification failure was bypassed. Hosted final-head and PR
merge-ref `lint-and-test` are verified separately in the stacked draft PR.

## Real-browser verification and screenshots

Chromium `/usr/bin/chromium`, Playwright 1.55.0, loopback only. Final possession
server restarted on `f8ff810` before acceptance. These commands exited **0**:

```sh
uv run --frozen --group browser python scripts/check_possessions_browser.py CONFIG \
  --url http://127.0.0.1:8508 --output data/interim/v05-possession-final
uv run --frozen --group browser python scripts/check_tactics_browser.py CONFIG \
  --url http://127.0.0.1:8508 --output data/interim/v05-tactical-regression
uv run --frozen --group browser python scripts/check_explorer_browser.py CONFIG \
  --url http://127.0.0.1:8508 --output data/interim/v05-explorer-regression
```

- **Nine Possession Flow groups pass**: original totals/scopes, retained opposition
  records, actual path endpoint→original action click, multiple shots in native
  sequence, actual terminal-state bar selection, ID 91 / cross-period warning /
  outside-filter context, period/team/type/outcome/score filters and empty state,
  windows/width/reset, mobile/sidebar and return to Explorer preserving Croatia's
  15 shots / 1.480 source xG and four charts.
- **Nine existing Tactical groups pass**: 650/194/151/73 original metrics,
  actual edge/node/progression clicks, shared filters and window/reset, explicit
  phase/score comparisons, native desktop/mobile axis bounds and title/legend
  separation, original Explorer context on return.
- **Ten original Explorer groups pass**: 2,978 records / 23 shots / original
  xG/final score, period/team/player/window consistency, empty/reset states,
  actual shot-map and threat-bar clicks, mobile/sidebar.
- Zero browser page exceptions and zero blocked external requests in all suites.
- Final possession opening **3.293s**; eight measured filter changes
  **0.434–1.095s**, median **0.716s**. A prior run measured 1.903s opening and
  is retained; neither is a universal startup promise. These measurements wait
  for expected metrics and app completion; they do not individually certify
  every browser pixel's paint time.
- Full Tactical regression opening **2.918s**; eight measured filters
  **0.623–1.893s**, median **1.144s**. This complements the separate three-run
  paired benchmark; usual latency budgets remain unresolved for slower actions.
- Full Explorer regression opening **3.874s**; 16 metric/chart updates
  **0.503–1.099s**, median **0.636s**. No claim that earlier variable latency
  and cold-start issues have all been eliminated.

Generated/visually inspected final research screenshots in
`data/interim/v05-possession-final/`: `desktop-flow.png`, `mobile-flow.png`,
`shot-sequence.png`, `action-evidence.png`, `mobile-filters.png`. An additional
real mobile check generated `mobile-terminal-states.png` and `mobile-path.png`;
terminal selection, native #2 recorded segments, no page overflow and no
exceptions pass. Both were visually inspected. Source-derived screenshots and
JSON results remain local/ignored, not uploaded to GitHub.

## Delivery and remaining acceptance

The draft PR targets `feat/fil-012-tactical-dashboard` / PR #10. Parent head
`2645eb916e0a1980eb6e650c494ce8395a7ebd32` was reverified unchanged and open/draft.
Hosted push CI for runtime `f8ff810` succeeded:
[Actions run](https://github.com/Qiao527/football-intelligence-lab/actions/runs/39697561064).
Final delivery-head and PR merge-ref results are recorded separately in the
PR after verification; this intermediate run is not substituted for them.

Independent human product acceptance remains open. Physical attacking direction
cannot be recovered from these sources, 82 provider endings remain explicitly
unresolved, and this event-only analysis cannot establish intentions, off-ball
movement, continuous control, causal bottlenecks or player ability. Single-match
exposure and conditional +x geometry limit interpretation. No xT/VAEP training,
player rating/candidate, merge, deployment, source-rights or visibility/plan change.
The existing integration protection decision remains separate from product work.
