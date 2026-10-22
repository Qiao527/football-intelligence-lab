# Four-view product stabilization — PR #12

This report supersedes the foundation's three-run performance comparison.
No additional feature PR, rating, AI Analyst, discovery engine, merge or deployment.
PR #12 remains a draft stacked on #11. PRs #7/#8/#10/#11 remain untouched and unmerged.
Human acceptance is outstanding: use [the local demo/checklist](PRODUCT_DEMO.md).

## Changes and review

- Directed networks now batch arrowheads in one marker trace instead of constructing
  a separate SVG annotation tree for every edge. Every placed directed pair,
  native display position, weight and exact source link remains. Arrow angles use
  the fixed-aspect native y-down display; this is not a physical attacking direction.
  Regression coverage checks edge identity, 80%-along-edge placement, and cardinal/
  diagonal orientation. Existing diamond/node/source clicks still pass in Chromium.
- Optional minimum-passes display thresholds help read dense networks. Default 1
  shows all recorded pairs; threshold changes never remove passes from metrics or
  evidence. Visible displayed/total counts and Reset behavior are tested.
- Player selection precedes four concise measure groups. Compact selected-player
  measures remain readable without horizontal scrolling; comparison tables have
  four plain-labelled columns. Full original evidence/metadata remains available.
  Mobile metric labels wrap. Shared-filter scope appears in all views.
- Bounded display caches reuse read-only full-match context and selected player
  facts. Per-rerun content fingerprinting and existing source/clock/score validation
  remain in front of these caches. Keys include input/config content identity and,
  for player facts, exact selected IDs. A changed-input regression confirms that
  verification failure stops analytics before any display cache can be reused.
  Existing verification spinners and player-preparation loading feedback remain.

Self-review found no factual metric/segmentation changes. `fil.metrics`, ingestion,
clock/score and possession extraction are unchanged by this stabilization. Original
IDs, native uncertainty, uncertified minutes/roles and missing cross-match support
remain explicit. No unsupported causal allocation, off-ball inference or ranking.

## Verification actually executed

All commands exited 0 after fixes, with no skipped tests:

- `uv lock --check`; fresh `uv sync --frozen --no-editable
  --reinstall-package football-intelligence-lab` using Python 3.11.14.
- `uv run --frozen ruff check .`; full editable tests: **360 passed**, 7.53 seconds.
- Fresh regular installation full tests: **360 passed**, 10.25 seconds. `uv build`
  produced wheel and sdist. Existing tests were retained; the annotation-specific
  arrow test now verifies the new rendering representation with stronger geometry/
  identity assertions, supplemented by six directional cases.
- Independent original-JSON `verify_explorer_source.py`, `verify_score_source.py`,
  `verify_tactics_source.py`, `verify_possessions_source.py`, `verify_players_source.py`:
  PASS. Existing immutable exports were reverified, not overwritten.
- All five Chromium suites pass: original Explorer, Tactical, Possession, Player
  checks plus connected `check_product_browser.py`. Desktop and 390×844 mobile,
  actual chart clicks, original IDs, outside-filter context, shared navigation,
  empty/reset states, threshold counts and concise player groups verified.
  Zero page errors or blocked external requests.
- Original **2,978** events, official **France 4–2 Croatia**, source xG
  **2.5782512977**, **650** completed passes, **151** progressive passes, **73**
  progressive carries, **182** native possession IDs and **16** reciprocal native
  pass-to-shot links preserved. All **23** input/fact/config snapshots preserve
  SHA-256 and modification nanoseconds.
- Hosted push and PR `lint-and-test` passed for implementation commit
  `571a5e5b970e2c19d45f19aa636adf2474da00b4`. Final documentation/timing-evidence head
  and its hosted checks are reported in the delivery message/PR check rollup.

Local screenshots/traces stay in ignored `data/interim/stabilization-review/` and
`data/interim/stabilization-benchmark/`. Only timing numbers, source-code identity
and this report are committed; no provider records, screenshots or trace payloads.

## Reproducible interleaved comparison

Parent: PR #12 before stabilization, `ae6667936b3ad58cbbd1368aa471e4f0a6964133`.
Candidate: implementation `571a5e5b970e2c19d45f19aa636adf2474da00b4`.
Ten pairs / twenty fresh server-and-browser runs; order alternates parent→candidate
and candidate→parent. No warm-up or outlier discarded. Identical instrumentation,
verified fixture, Chromium 154.0.8037.57, viewport 1600×1150, pinned Python 3.11.14;
managed Linux host has a two-CPU cgroup quota. No local tests/browser suites were
intentionally run concurrently with this final experiment. No OS page-cache eviction.
Diagnostic and pilot pairs remain separate, excluded by predefined phase, not outcome.
Source tree digests are checked before every run and after completion; both source
snapshots remained unchanged across all ten pairs.

Reproduce using two unchanged source snapshots and the committed benchmark script:

```bash
mkdir -p /tmp/fil-stabilization-parent
# Run on a fresh directory; preserve the existing PR stack.
git archive ae6667936b3ad58cbbd1368aa471e4f0a6964133 | tar -x -C /tmp/fil-stabilization-parent
uv run --frozen --group browser python scripts/benchmark_product.py "$FIL_DEMO_CONFIG" \
  --parent /tmp/fil-stabilization-parent/src --candidate src --pairs 10 \
  --output data/interim/stabilization-benchmark
```

`explorer_cold` runs from navigation through the original ledger, four instantiated
plots, original evidence, synchronized metrics, script-idle state and two animation
frames. `ledger_seconds` separately preserves the earlier heading milestone.
View-opening stages include first-use work; `_period2` selects period 2, `_full`
returns to full match. Returns naturally benefit from caches in both versions.
Server readiness and Chromium launch are outside navigation and retained separately.
These measurements must not be substituted for older heading-only/warm/concurrent
suite timings. CDP tracing adds overhead equally to both versions; absolute results
apply to this host/probe, not an unmeasured normal laptop.

All 240 stage observations are retained in
[timing-only CSV](evidence/stabilization-timings.csv); full precision, CPU, logical
websocket payload and server profiles are included. Raw local JSON also retains
per-run readiness, launch time, source digest and trace summaries. CDP traces can
be opened in Chrome DevTools/Perfetto locally; trace category durations overlap
and must not be added as disjoint CPU costs.

| Stage, seconds | Parent median | Candidate median | Candidate min–max | Candidate SD / p90 | Faster pairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| explorer_cold | 5.375 | 5.257 | 4.993–5.658 | 0.182 / 5.469 | 5/10 |
| match_period2 | 1.029 | 0.996 | 0.913–1.413 | 0.143 / 1.045 | 7/10 |
| match_full | 0.840 | 0.821 | 0.763–1.155 | 0.115 / 0.930 | 6/10 |
| tactical_open | 2.363 | 1.297 | 1.147–1.712 | 0.215 / 1.647 | 10/10 |
| tactical_period2 | 1.561 | 0.937 | 0.863–1.262 | 0.145 / 1.176 | 10/10 |
| tactical_full | 1.680 | 0.938 | 0.897–1.097 | 0.071 / 1.079 | 10/10 |
| possession_open | 1.313 | 1.346 | 0.963–2.329 | 0.366 / 1.447 | 3/10 |
| possession_period2 | 0.697 | 0.638 | 0.547–2.396 | 0.560 / 0.678 | 7/10 |
| possession_full | 0.630 | 0.613 | 0.579–2.350 | 0.550 / 0.679 | 7/10 |
| player_open | 1.229 | 1.255 | 0.978–3.713 | 0.795 / 1.347 | 4/10 |
| player_period2 | 0.812 | 0.804 | 0.728–2.218 | 0.451 / 0.996 | 6/10 |
| player_full | 0.829 | 0.521 | 0.463–0.814 | 0.121 / 0.759 | 10/10 |

### Browser and server attribution

| Probe, median | Parent | Candidate |
| --- | ---: | ---: |
| Cold ledger milestone, seconds | 4.980 | 4.095 |
| Tactical opening logical websocket bytes | 242515.000 | 215301.000 |
| Tactical period filter logical websocket bytes | 169704.000 | 149751.000 |
| explorer_cold browser TaskDuration, seconds | 3.464 | 3.430 |
| explorer_cold browser LayoutDuration, seconds | 0.107 | 0.112 |
| explorer_cold browser RecalcStyleDuration, seconds | 0.088 | 0.088 |
| tactical_open browser TaskDuration, seconds | 2.071 | 1.118 |
| tactical_open browser LayoutDuration, seconds | 0.135 | 0.025 |
| tactical_open browser RecalcStyleDuration, seconds | 0.248 | 0.060 |
| tactical_period2 browser TaskDuration, seconds | 1.463 | 0.797 |
| tactical_period2 browser LayoutDuration, seconds | 0.090 | 0.016 |
| tactical_period2 browser RecalcStyleDuration, seconds | 0.163 | 0.039 |
| player_full browser TaskDuration, seconds | 0.497 | 0.427 |
| player_full browser LayoutDuration, seconds | 0.005 | 0.007 |
| player_full browser RecalcStyleDuration, seconds | 0.009 | 0.010 |
| explorer_cold server verification_seconds | 0.828 | 0.800 |
| tactical_open server tactical_view_seconds | 0.595 | 0.606 |
| player_full server player_view_seconds | 0.390 | 0.099 |
| match_period2 server view_preparation_seconds | 0.052 | 0.000 |

Websocket counts use decoded logical frame payload sizes from CDP, not compressed
wire size or a claim of bandwidth saturation. Browser Performance metrics capture
main-thread task/script/layout/style work. Server stage timers exclude Python
imports before app instrumentation; import/bootstrap and transport waits are not
separately attributable by subtraction because browser/server work overlaps. Raw
traces and websocket timing remain local for deeper inspection. The initial
identical-code diagnostic showed high Tactical layout/style cost versus Python
view work, motivating batched arrowheads; the final paired results above test it.

### Interpretation and remaining acceptance limits

Tactical opening improves **2.363 → 1.297 seconds** (about 45%), period-2
filtering **1.561 → 0.937**, and returning to full match **1.680 → 0.938**.
All ten paired observations are faster for each Tactical stage. Browser task,
layout/style and payload reductions support a rendering improvement on this
host, while server view time stays similar. Cached Player Evidence returns
improve **0.829 → 0.521 seconds**, faster in all ten pairs; its first opening
has no demonstrated improvement. This does not establish performance on other
machines, matches, mobile devices or filter combinations.

Complete Explorer startup **5.375 → 5.257 seconds** is faster in only five of ten
pairs: **no convincing overall cold-start improvement**, and the **≤3-second goal
fails**. The earlier ledger milestone also remains above three seconds. Cold
browser main-thread work is about 3.4 seconds and verification about 0.8 seconds;
imports, client bootstrap and rendering remain costs. They cannot safely be
removed by skipping source checks or changing the completion milestone.

For the eight period-filter/return probes across all views, **67/80 candidate
interactions ≤1 second**, versus **47/80 parent**. Most measured interactions meet
the typical budget, but slow paths and variability remain: candidate maxima
include **2.396-second** possession filtering, **2.350-second** possession return,
**2.218-second** player filtering and **3.713-second** first player opening. These
samples, including pair 8's slower candidate run, are retained. No cause for
those spikes is certified. First Possession/Player openings show no consistent
improvement, and no universal interaction-budget pass is claimed.

Full baseline/candidate standard deviations, min/max/p90, all sample timings and
paired differences are retained in [timing summary](evidence/stabilization-summary.json)
and the CSV. Parent/candidate source digests respectively:

- `1d93d5074000f225b555dd3fb9b5a1b49183c2935b77f27beb3958acce5c56af`
- `4d836f89621ea348c704534421fa0fc0e2a62c18ba1dbe4cec05fca07498bd09`

Median server readiness: 0.414 → 0.428 seconds; browser launch: 0.444 → 0.438,
measured separately outside navigation. The final benchmark completed without
browser errors, blocked external requests or source-digest changes.

Remaining product acceptance blockers are cold startup, long-tail responsiveness,
human review of dense networks/mobile comparison scrolling and the unsigned
acceptance checklist. Minutes/role uncertainty and insufficient cross-match
support remain research limits. No new feature expansion is authorized by this
report. Keep all PRs unmerged; protection, product acceptance and merge rights
remain separate from successful engineering/CI checks.
