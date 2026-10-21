# FIL-012 — Tactical Dashboard delivery evidence

Issue [#9](https://github.com/Qiao527/football-intelligence-lab/issues/9).
Development branch: `feat/fil-012-tactical-dashboard`, stacked on unchanged
`feat/fil-v03-match-explorer` / PR #8 at
`363494ccd8b7f42f40526d0b0d54a19c112f1d68`.
Runtime implementation: `86638f43112e9fd9936a7a7dba5da473aec232aa`;
independent exposure-check correction: `8cf62b16bef86f6da0ebed19ae5419f7c7a7d81a`;
final mobile-layout fix and validated artifact revision:
`c55e14b9cf73e7f41dce8c63ac4a4852fcdac79e`. Later delivery changes add only
this report/status documentation.

## Delivered behavior and limits

The local View selector opens directed completed-pass networks, event-average
pass-origin positions, native-frame progression for passes/carries, H1/H2,
explicit-window and acting-team pre-event score-state comparisons. All tactical
panels share Explorer filters. Actual player/link/endpoint clicks and selectors
resolve original IDs and source JSON. QA tables preserve excluded/unknown actions,
unplaced nodes, input manifests and individual edge/position sample IDs.
[TACTICS.md](../TACTICS.md) defines every inclusion, exclusion, threshold and
spatial uncertainty. No dependency changes, rating, xT/VAEP, physical direction
inference, tracking reconstruction, causal player claim or source-rights expansion.

The chart uses unchanged native 120×80 coordinates, y downward. Physical
team/period attacking ends remain unknown. Progression is the declared +x,
≥10-provider-unit distance-to-(120,40) gain proxy, not a certified physical
movement interpretation. Player means are completed-pass origin samples with
counts/extents, not continuous positions or stable formations. Dense full-match
networks and unequal temporal/player exposure require cautious interpretation;
shared filters and exact tables provide access to the underlying evidence.

## Real-source reconciliation and immutable artifacts

Pinned StatsBomb source revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`,
source manifest SHA-256
`f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c`.
The reviewed specification's explicit absent-outcome completion rule is isolated
in the provider adapter; explicit null/unknown and unsupported fields are audited.

- 2,978 original events; official and independently reconstructed France **4–2**
  Croatia; six goal awards including one linked own goal and one penalty goal.
- 846 native passes: **650 completed**, 188 failed, eight provider Unknown;
  617 observed carries, for 1,463 audited actions.
- **194 directed pairs**, 27 player nodes; **151 progressive passes / 73
  progressive carries** under progression v1. No unresolved eligible endpoints
  in this real fixture. Missing-coordinate cases remain covered by tests.
- Source xG unchanged: France eight shots / **1.097963608 xG** /
  **0.314463608 NPxG**; Croatia 15 shots / **1.4802876897 xG/NPxG**.
- Independent raw-JSON tactical verification checks all exact edge sets/weights,
  player-origin means/extents and sample IDs, action endpoints/progression,
  comparison exposure/counts and **160** window/score-context queries spanning
  every 5/10/15-minute bin. Existing Explorer verifier checks 23 shots, 23
  cumulative points and 80 team/window rows. Score verifier checks every event.
- All **22 input data files** snapshotted before final verification retain
  SHA-256 and nanosecond mtime (local config is excluded from this snapshot).
  Seven tactical files retain bytes/mtime on recomputation/reuse. No old bundle
  was repaired or overwritten; development preview bundles are not delivery
  evidence.

Validated local bundle:
`data/interim/tactics/8cbc37c73a3e8108f4076a74f6769deb121a561081f953e493f332c6cfd96b97/fil-tactics-1/c55e14b9cf73e7f41dce8c63ac4a4852fcdac79e`.
It contains five typed Parquet tables, quality JSON and hash manifest with input
chain, code/version, UTC creation and pinned Arrow/writer settings. Provider
artifacts, screenshots and local configs remain ignored and were not pushed.

## Executed engineering checks

Linux x86_64, pinned CPython 3.11.14, uv 0.12.23. Commands run from repository
root with `UV_CACHE_DIR=/tmp/fil-uv-cache`; `CONFIG` denotes the existing verified
`data/interim/delivery-match/metrics/.../d0ea933c8aa9432b10eaabd62000219d1f0e1c98/local-config.json`.
`BUNDLE` denotes the exact bundle above. All final checks below exited **0**:

| Command | Actual result |
| --- | --- |
| `uv lock --check` | Lock and manifest agree; no dependency/lock changes |
| `uv sync --frozen` | Frozen editable environment installed |
| `uv run --frozen ruff check .` | All checks passed |
| `uv run --frozen pytest -q` | **318 passed**, zero skipped, 6.70s |
| `uv build` | Wheel and source distribution built |
| `UV_PROJECT_ENVIRONMENT=/tmp/fil-v04-final-regular uv sync --frozen --no-editable --reinstall-package football-intelligence-lab` | Fresh regular environment, current package rebuilt |
| Same environment `uv run --frozen --no-editable ruff check .` | All checks passed |
| Same environment `uv run --frozen --no-editable pytest -q` | **318 passed**, zero skipped, 9.11s |
| Same environment `python -m fil.explorer.tactical_data --help` via frozen uv | Installed CLI works; also added to hosted CI |
| `uv run --frozen python -m fil.explorer.tactical_data --config CONFIG --pipeline-revision c55e14b9cf73e7f41dce8c63ac4a4852fcdac79e --output data/interim/tactics` | Verified artifact created and reused immutably |
| `uv run --frozen python scripts/verify_tactics_source.py CONFIG BUNDLE` | Independent tactical reconciliation PASS |
| `uv run --frozen python scripts/verify_explorer_source.py CONFIG` | Independent existing xG/window/spatial verification PASS |
| `uv run --frozen python scripts/verify_score_source.py RAW CANONICAL CLOCK SCORE` | Independent original score verification PASS |

Tests cover supported absent versus explicit-null outcomes, malformed native
contracts, missing recipients/actors/coordinates, duplicate IDs, directed/reverse
pairs, no-pass/empty windows, exact threshold/bounds, native π rounding, tied
timestamps, period/stoppage/shootout boundaries, acting versus possession team,
pre-own-goal score state, immutable outputs/tampering and shared UI/reset states.
Self-review fixes include typed empty Arrow masks, valid native angle rounding,
null-actor exclusion, reset of tactical focus/chart selection epochs, and mobile
chart legends separated from titles. Screenshot inspection caught the latter;
a real-browser title/legend bounding-box regression check now guards it.

Initial development checks exposed fixture/selector mistakes, corrected before
delivery. One regular-install attempt reused a stale package before new files
were staged and failed collection (two errors); a new empty environment with an
explicit current-package rebuild passed all 318. The first build lacked sandbox
network access to the already pinned backend; the authorized network-enabled
build succeeded. A newly expanded independent check initially compared total
selected exposure to only pass/carry rows; it now compares to all original events.
No failed check was bypassed.

Hosted push `lint-and-test` at `8cf62b1`:
[successful Actions run](https://github.com/Qiao527/football-intelligence-lab/actions/runs/39692019796).
Final branch-head and PR merge-ref CI are checked separately in the draft PR;
this successful intermediate run is not presented as a final-head result.

## Performance measurement

Fresh server/process and Chromium context for each run; identical pinned local
config and original navigation → **Event ledger heading** milestone. Server
readiness and browser/context launch measured separately. No OS cache eviction,
preload, weakened source verification or fabricated metric. Parent code was
extracted with `git archive 363494c` into `/tmp/fil-v04-parent` and selected with
`PYTHONPATH`; its actual `fil.__file__` was verified. Both sets use identical
locked dependencies and viewport (1600×1150).

| Seconds | Unchanged Explorer parent | Final tactical runtime |
| --- | ---: | ---: |
| Navigation → ledger, run 1 | 3.672 | 4.134 |
| Run 2 | 6.244 | 3.614 |
| Run 3 | 5.516 | 5.425 |
| Median | **5.516** | **4.134** |
| Navigation → evidence element, median | 6.281 | 5.507 |

Observed median difference is −1.382s (−25.0%), but overlapping ranges and
host/browser variability prevent attributing this to a tactical speedup.
Tactical extraction/rendering is lazy on View selection; the default Explorer
cold path retains full source verification. The earlier v0.3 report's median
3.659s and historical 5.419s remain visible; this run does **not** establish that
those earlier acceptance problems are solved. **The ≤3s startup budget fails.**
A preliminary current-code set (before the reset fix) also measured
3.472/3.755/5.285s and is retained under `data/interim/v04-benchmark-current`;
the final measurements above include the reset fix. The subsequent
tactical-only legend layout fix does not run in the default Explorer cold path.

Final server readiness 0.396–0.488s; Chromium launch 0.468–0.537s. App-side full
source verification 0.827–1.193s, view preparation 0.024–0.028s, shared filtering
0.054–0.112s, chart submission 0.227–0.370s. Remaining browser hydration/paint,
transport and scheduling are not individually certified by these probes.
Raw benchmark/profile JSON remains local in `data/interim/v04-benchmark-parent`
and `data/interim/v04-benchmark-final`.

## Real Chromium verification and screenshots

The loopback server was restarted on the final runtime revision before tactical
acceptance. Commands exited **0**, Chromium `/usr/bin/chromium`, Playwright
1.55.0 from the frozen optional browser group:

```sh
uv run --frozen --group browser python scripts/check_tactics_browser.py CONFIG \
  --url http://127.0.0.1:8504 --output data/interim/tactical-review-delivery
uv run --frozen --group browser python scripts/check_explorer_browser.py CONFIG \
  --url http://127.0.0.1:8504 --output data/interim/explorer-v04-regression
```

- **Nine tactical check groups pass**: full raw-source counts; actual edge,
  player and progressive-endpoint clicks to exact original events; period/team/
  score/type/no-pass synchronization; 15/5-minute windows and reset; explicit
  window/score comparisons; 390px mobile controls with no page overflow; return
  to Explorer preserving Croatia's 15 shots / 1.480 source xG and four charts.
  Mobile chart title/legend bounds do not overlap after the screenshot-driven fix.
- **Ten existing Explorer check groups pass**: all original totals and charts,
  period/team/player/type/window consistency, empty selections, reset and stale
  window prevention, actual shot-map and threat-bar clicks, mobile/sidebar.
- Zero page exceptions and zero blocked external requests in both suites.
- Tactical run: navigation → original Explorer ledger **5.188s**; first tactical
  View selection → synchronized tactical counts **4.893s**; eight measured
  filter changes **0.736–3.976s**, median **1.792s**. This click-to-count milestone
  is not a claim that every chart has finished painting. Tactical interaction
  performance remains outside the handbook's usual 0.5–1s target.
- Explorer regression run: ledger **3.819s**; 16 updates including metric/chart
  waits **0.499–1.052s**, median **0.672s**. This better sample does not remove
  the earlier variable v0.3 latency results or establish human acceptance.

Generated and visually inspected final desktop/mobile network screenshots:
`data/interim/tactical-review-delivery/desktop-network.png` and
`data/interim/tactical-review-delivery/mobile-network.png`. Additional screenshots
in that directory: `mobile-overview.png`, `mobile-filters.png`, `comparison.png`,
`event-evidence.png`. Source evidence/comparison screenshots were also inspected.
Original Explorer screenshots and both machine-readable `browser-report.json`
files remain local/ignored. No provider screenshots were uploaded to GitHub.

## Product acceptance and integration

Automated evidence establishes this scoped implementation, not independent human
product acceptance. Performance budgets, dense-graph usability review and the
meaning of the deliberately conditional progression proxy remain visible review
items. Physical directions cannot be certified from these inputs; that is an
explicit scope limit, not a claim that they have been recovered.

GitHub REST and GraphQL access work. PR #7 stays draft/open at `195a3ef` and
PR #8 stays draft/open at the exact parent `363494c`; neither was edited or
merged. Student benefits activation/protection remains one existing owner-level
decision in [MAIN_PROTECTION.md](../MAIN_PROTECTION.md). Product engineering did
not wait, retry the paid-plan restriction, change visibility/plan or bypass any
merge guard. The new draft targets the Explorer branch. No merge or deployment.
