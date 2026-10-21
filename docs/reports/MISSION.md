# Autonomous integration and local v0.3 delivery report

Historical pre-recovery evidence. Current API, governance, performance, spatial and
product verification: [AUTONOMOUS_DELIVERY.md](AUTONOMOUS_DELIVERY.md).

Recorded 2026-10-21 UTC. Implemented a locally runnable product-review candidate,
not a human-accepted release. No PR/main merge or deployment was performed. Hosted CI
and API-mediated delivery remain unobserved/blocked; no PASS is manufactured.

## Built and branch structure

FIL-002 squash merge is verified on main at
`0fd8306e6d09a2ab062acb39443272f145114572`.
FIL-002 feature anchor `5a18a4e1a417cfbf33941796552b25c9c8ab0c36` has an
identical tree to that main commit. Original FIL-005 head:
`9afe745d701cbb695dc45ddbc32332878f6aa99d`.

Created `integrate/fil-003-005` from main, applied only the anchor→FIL-005 tree
patch. Its first commit `bfe22de` exactly reproduces the FIL-005 tree, without
replaying historical FIL-002 commits or rebasing three branches. No conflicts.
Added a score-semantics correction, two regressions, integrate/** push CI and
actual verification evidence. Final integration head:
`195a3efb4bef7441757f4e66f98d1ad410374dc9` (last change is documentation only).
Original branch heads are recoverable under backup/mission-20261021, with all
remaining local heads additionally preserved under its all/ namespace. Original
feature branches/PRs remain intact. See INTEGRATION.md.

The product branch `feat/fil-v03-match-explorer` initially used integration
329362e, then incorporated the doc-only parent update 195a3ef by ordinary merge.
No integration source history is duplicated. Runtime code verified at
`c3b28e2a2ad1d4b86e023a90f8886098ea61b736`; subsequent source-verifier/evidence/
parent-documentation/report changes leave the runtime unchanged.

Built verified match-play shots/xG/NPxG, cumulative source-only step points,
5/10/15-minute period windows, source-native shot maps, score-state progression,
shared period/team/player/type/outcome/window filters, native threat-bar and
shot-marker interactions, full-match context, exact original event/JSON/source
file and manifest drilldown, responsive desktop/mobile UI and reset behavior.
Read-only Streamlit + Plotly follows the handbook. Arrow handles the small
verified dataset directly; no extra database, services, mplsoccer/Matplotlib or
football-model packages were needed. No xT, ratings, networks, AI or tracking.

## Critical review and corrections

Independent-style review and separate raw-source recomputation were performed
by the implementing agent. This is not a fabricated separate reviewer/human approval.

- Pure score signals could relabel penalties or swap a same-team goal/miss while
  preserving final score. Both regression tests first failed, then passed after
  canonical shot-semantic comparison was enforced. Full source artifact output
  remains unchanged on valid inputs.
- Real browser checks caught header HTML displayed as code, dark-theme contrast,
  reset values returning on a later interaction, missing click-selection mode,
  and a toolbar rule hiding the mobile sidebar toggle. Corrected these and
  retained offline reset/rerun and real browser interaction regression checks.
- Browser harness selectors were corrected for virtualized searchable options,
  Plotly's native overlay hit-testing and Streamlit elements whose test-ID is on
  the element itself. Real mouse coordinates/click events are used; no fake
  Streamlit state injection or bypass of assertions.
- An initial decimal-expectation test was corrected to the documented 1e-12
  float regrouping tolerance; actual source totals/cumulative prefixes also
  reconcile directly using fsum. No fabricated probabilities or zero substitution.
- Reviewed immutable staging/reuse, invalid source xG, duplicate IDs, missing
  locations, coordinate bounds, missing scoring semantics, own-goal graph
  ambiguity, ordinary/extra penalties, shootout separation, period endpoints,
  source metadata, raw lookup, corrupt/symlink/extra members, manifest tampering,
  dependency pins, HTML escaping, loopback-only serving and telemetry disabling.

No known critical football/security findings remain in this scoped fixture after
correction. Unsupported schemas/ambiguous scoring fail closed. A missing included
shot xG blocks analytics. Cold-start performance remains a limitation below.

## Independently verified real match

Official Hudl/StatsBomb revision:
`4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`.
Original events SHA-256:
`a9aa72c042153fa351c3591ee11e7fba95b0c8841c4489da4aa6809de1edbdf5`.
Original match metadata SHA-256:
`f89dbd4aedcaf9c9e4ec9d8e745d5d54596500ec357d7489c914a2f126805adf`.
Source manifest:
`f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c`.

Match 8658: 2018-07-15, FIFA World Cup 2018 Final, France home (771), Croatia
away (785). All 2,978 records preserve original IDs, sequence, source JSON and
clock fields. Observed H1/H2 duration 2,906,080 / 3,003,760 ms; no estimates.
Final score independently reconstructed **France 4–2 Croatia**, six awards:
five Shot/Goal records, one scored penalty among them, and one own goal from
two explicitly linked source representations (not two goals).

| Team | Match-play shots | Source xG | Non-penalty xG |
| --- | ---: | ---: | ---: |
| France | 8 | 1.097963608 | 0.314463608 |
| Croatia | 15 | 1.4802876897 | 1.4802876897 |

All 23 shot records retain source IDs and raw probabilities; zero missing xG or
shot x/y locations in this fixture. The independent source script reconciles
23 cumulative points and all **80** team/bin rows across 5/10/15-minute windows,
including exact bounds, count/sum and ID partitioning. All three window sets
partition each included shot exactly once; own goals add no shot xG. This is
provider source xG, not a model trained by FIL or a prediction of final score.

## Actual commands, outcomes and reproducibility

Integration: **253 tests**, no skips, clean-cache fresh editable 2.43s / regular
2.21s. Explorer: **276 tests**, no skips, final workspace 4.01s; fresh editable
5.92s / regular 5.69s. Final runtime fresh checkout:
`/tmp/fil-product-release-srs70phj/checkout`, isolated empty dependency cache. All commands below
ran and exited **0**; equivalent GitHub-hosted execution is **unobserved**.

Paths in the long commands are the actual generated local manifests/datasets;
they are ignored local evidence, not redistributed provider files.

| Scope | Install | Actual command | Exit |
| --- | --- | --- | ---: |
| Integration | Editable | `uv lock --check` | 0 |
| Integration | Editable | `uv sync --frozen` | 0 |
| Integration | Editable | `uv run --frozen ruff check .` | 0 |
| Integration | Editable | `uv run --frozen pytest -q` | 0 |
| Integration | Editable | `uv build` | 0 |
| Integration | Regular | `uv sync --frozen --no-editable` | 0 |
| Integration | Regular | `uv run --frozen --no-editable pytest -q` | 0 |
| Integration | Regular | `uv run --frozen --no-editable ruff check .` | 0 |
| Integration | Regular | `uv run --frozen --no-editable python -m fil.ingestion.normalize build --raw-bundle /workspace/football-intelligence-lab/data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb --pipeline-revision 329362e86612d8320f1ee9ccd6d0eb6be01260ae` | 0 |
| Integration | Regular | `uv run --frozen --no-editable python -m fil.time build --raw-bundle /workspace/football-intelligence-lab/data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb --canonical-dataset data/interim/events/match_id=8658/f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c/fil-statsbomb-adapter-1/329362e86612d8320f1ee9ccd6d0eb6be01260ae --pipeline-revision 329362e86612d8320f1ee9ccd6d0eb6be01260ae` | 0 |
| Integration | Regular | `uv run --frozen --no-editable python -m fil.metrics.score_cli build --raw-bundle /workspace/football-intelligence-lab/data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb --canonical-dataset data/interim/events/match_id=8658/f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c/fil-statsbomb-adapter-1/329362e86612d8320f1ee9ccd6d0eb6be01260ae --clock-dataset data/interim/clocks/match_id=8658/e4847e6a152e589755935041cceeec0d45b2d0e885dddc55cbb53788967156c0/fil-period-clock-1/329362e86612d8320f1ee9ccd6d0eb6be01260ae --pipeline-revision 329362e86612d8320f1ee9ccd6d0eb6be01260ae` | 0 |
| Integration | Regular | `uv run --frozen --no-editable python -m fil.metrics.score_cli verify --raw-bundle /workspace/football-intelligence-lab/data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb --canonical-dataset data/interim/events/match_id=8658/f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c/fil-statsbomb-adapter-1/329362e86612d8320f1ee9ccd6d0eb6be01260ae --clock-dataset data/interim/clocks/match_id=8658/e4847e6a152e589755935041cceeec0d45b2d0e885dddc55cbb53788967156c0/fil-period-clock-1/329362e86612d8320f1ee9ccd6d0eb6be01260ae --score-dataset data/interim/scores/match_id=8658/cb2bc476ed52c40d2c04a31c6e2ec60c5f73792423856d34ef5e6e7dd101b619/fil-score-1/329362e86612d8320f1ee9ccd6d0eb6be01260ae` | 0 |
| Integration | Regular | `uv run --frozen --no-editable python scripts/verify_score_source.py /workspace/football-intelligence-lab/data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb data/interim/events/match_id=8658/f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c/fil-statsbomb-adapter-1/329362e86612d8320f1ee9ccd6d0eb6be01260ae data/interim/clocks/match_id=8658/e4847e6a152e589755935041cceeec0d45b2d0e885dddc55cbb53788967156c0/fil-period-clock-1/329362e86612d8320f1ee9ccd6d0eb6be01260ae data/interim/scores/match_id=8658/cb2bc476ed52c40d2c04a31c6e2ec60c5f73792423856d34ef5e6e7dd101b619/fil-score-1/329362e86612d8320f1ee9ccd6d0eb6be01260ae` | 0 |
| Explorer | Editable | `uv lock --check` | 0 |
| Explorer | Editable | `uv sync --frozen` | 0 |
| Explorer | Editable | `uv run --frozen ruff check .` | 0 |
| Explorer | Editable | `uv run --frozen pytest -q` | 0 |
| Explorer | Editable | `uv build` | 0 |
| Explorer | Regular | `uv sync --frozen --no-editable` | 0 |
| Explorer | Regular | `uv run --frozen --no-editable pytest -q` | 0 |
| Explorer | Regular | `uv run --frozen --no-editable ruff check .` | 0 |
| Explorer | Regular | `uv run --frozen --no-editable python -m fil.ingestion.normalize build --raw-bundle /workspace/football-intelligence-lab/data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb --pipeline-revision c3b28e2a2ad1d4b86e023a90f8886098ea61b736` | 0 |
| Explorer | Regular | `uv run --frozen --no-editable python -m fil.time build --raw-bundle /workspace/football-intelligence-lab/data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb --canonical-dataset data/interim/events/match_id=8658/f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c/fil-statsbomb-adapter-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736 --pipeline-revision c3b28e2a2ad1d4b86e023a90f8886098ea61b736` | 0 |
| Explorer | Regular | `uv run --frozen --no-editable python -m fil.metrics.score_cli build --raw-bundle /workspace/football-intelligence-lab/data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb --canonical-dataset data/interim/events/match_id=8658/f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c/fil-statsbomb-adapter-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736 --clock-dataset data/interim/clocks/match_id=8658/2ba6fab27200dcec273a98de8ebdc79b0b88d538b8d467a9c551a310cf9b5264/fil-period-clock-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736 --pipeline-revision c3b28e2a2ad1d4b86e023a90f8886098ea61b736` | 0 |
| Explorer | Regular | `uv run --frozen --no-editable python -m fil.metrics.score_cli verify --raw-bundle /workspace/football-intelligence-lab/data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb --canonical-dataset data/interim/events/match_id=8658/f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c/fil-statsbomb-adapter-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736 --clock-dataset data/interim/clocks/match_id=8658/2ba6fab27200dcec273a98de8ebdc79b0b88d538b8d467a9c551a310cf9b5264/fil-period-clock-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736 --score-dataset data/interim/scores/match_id=8658/c7d08064f9c35eeac87b22434ad17fc9048345cf4dfc7ccec3cd084b4f798b4c/fil-score-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736` | 0 |
| Explorer | Regular | `uv run --frozen --no-editable python scripts/verify_score_source.py /workspace/football-intelligence-lab/data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb data/interim/events/match_id=8658/f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c/fil-statsbomb-adapter-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736 data/interim/clocks/match_id=8658/2ba6fab27200dcec273a98de8ebdc79b0b88d538b8d467a9c551a310cf9b5264/fil-period-clock-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736 data/interim/scores/match_id=8658/c7d08064f9c35eeac87b22434ad17fc9048345cf4dfc7ccec3cd084b4f798b4c/fil-score-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736` | 0 |

Additional executed checks (all exit **0**):

```bash
uv run --frozen python -m fil.explorer.bootstrap \
  --raw data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb \
  --pipeline-revision c3b28e2a2ad1d4b86e023a90f8886098ea61b736
# Repeat the same bootstrap to verify reuse.
uv run --frozen python scripts/verify_explorer_source.py CONFIG
uv run --frozen --group browser python scripts/check_explorer_browser.py CONFIG
```

CONFIG is the exact local path:
`/workspace/football-intelligence-lab/data/interim/local-explorer/metrics/8a46e6e862a59afc1032c0c5b3467bb5228be259a23249d51a97671f5c9311a4/fil-source-xg-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736/local-config.json`.
Regular-install `fil.explorer.data` against the exact same verified inputs also
rebuilt fact/QA files byte-for-byte; CLI --help checks passed for fil.explorer,
fil.explorer.data and fil.explorer.bootstrap. Wheel/sdist inspection excludes
raw/interim/Parquet/PNG provider-derived files. Repeated bootstrap preserves all
**23** raw/canonical/clock/score/metric input/output files' bytes and mtimes.
New roots reproduce fact/QA bytes with fixed inputs/code; fresh manifest creation
timestamps may differ. The raw files and historical manifests were never altered.

Fact bundle: `data/interim/local-explorer/metrics/8a46e6e862a59afc1032c0c5b3467bb5228be259a23249d51a97671f5c9311a4/fil-source-xg-1/c3b28e2a2ad1d4b86e023a90f8886098ea61b736`.

| Local artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `window_threat.parquet` | 6052 | `8cd951771b1652ce703445265813ffc008b72a3aa4ccba936dae2dcf28dc8811` |
| `manifest.json` | 1265 | `914c2d7cbff1513129e05a9677356367d4d98783562e3d484b99ff4b8e2ae720` |
| `xg_cumulative.parquet` | 4624 | `84ded31413d7853f5ed14bf0149057f2e218316a49a8f26ce1e08d794a608042` |
| `shots.parquet` | 43230 | `e0e3d7be820828573dd61fcf0fcfd8ba5c24c87b695d8cd2b54810b76dee024b` |
| `quality.json` | 2816 | `2a1c8c967b081579c624d29b56865874aaca8c4dc49ad16c64667a16be43054e` |

Versions: Python 3.11.14, uv 0.12.23, PyArrow 21.0.0, Streamlit 1.50.0,
Plotly 6.3.1, pytest 8.4.2, Ruff 0.14.0, uv_build 0.9.5; optional Playwright
1.55.0 with system Chromium 154.0.8037.57 on Linux. Direct dependency provenance/
license reviewed from official PyPI metadata and installed license files:
Streamlit Apache-2.0, Plotly MIT, Playwright Apache-2.0. All transitive package
versions/artifact hashes are frozen in uv.lock; no vulnerability-free claim is made.

Local evidence JSON/logs: /tmp/fil-integration-verification.json,
/tmp/fil-product-release-verification.json, /tmp/fil-product-source-verification.json,
/tmp/fil-explorer-final-regular.json and data/interim/review/browser-report.json.
These supplement the retained commands/hashes here. No unrun or skipped check is
reported as successful. Earlier failures and corrections are described above.

## Actual browser evidence and limitations

Eight real Chromium checks pass: full-match counts/source xG and fixed score;
period/team synchronization; empty results without stale evidence; reset plus
subsequent interaction; native shot marker → exact source ID/timestamp; native
threat bar → P1 [30,45) window; 390px viewport without horizontal page overflow;
mobile sidebar opens and its team filter drives the same metrics. Provider JSON
is the verified original record, not text composed by an agent. Source shot click:
`57a6526e-9652-4195-8151-674c888e04d3`, provider timestamp `00:01:10.027`, period 2.

Actual accepted screenshots, kept local/ignored:

- data/interim/review/desktop.png
- data/interim/review/event-evidence.png
- data/interim/review/window-selection.png
- data/interim/review/mobile.png
- data/interim/review/mobile-filters.png

Latest measured cold first-render time: **5.419s**.
An earlier warm-session check measured 1.945s. The handbook's ≤3s cold-start
budget is **not met reliably** on this environment; no universal interaction
latency promise or performance PASS. Source verification is retained, not skipped
to make the UI appear faster. Window aggregation was limited to validated shots
to reduce redundant full-event projections; further cold-start profiling remains.
Only local Linux/Chromium tested; no cross-platform or broad accessibility audit.

Real fixture has no extra time/shootout; these remain TEST-ONLY coverage. No
separate official shootout certification, generalized source-schema support,
VAR adjudication, physical direction normalization, continuous player tracking,
scientific causal claims or full-match clock/video alignment. Card/substitution
records can be selected in the ledger; there is no dedicated narrated card/
substitution timeline or cross-chart freeform lasso brush.

DATA-SHOTS and shared-filter/evidence requirements have scoped local technical
evidence. DATA-TIME/DATA-SCORE are reverified; coordinate bounds/null handling is
verified, **not a declaration of complete DATA-SPATIAL direction validation**.
No blanket v0.3 gate acceptance, independent human approval, hosted CI PASS or
later research/product milestone is declared. Ready for **local product review**
of this real-fixture Explorer; final acceptance remains pending.

## Delivery, one-time owner action and next integration

Integration branch is pushed, targeting main. Product branch is pushed separately,
targeting the integration parent while unmerged. No existing PR is closed,
rewritten or merged; no direct main push or deployment. Exact creation links:

- https://github.com/Qiao527/football-intelligence-lab/compare/main...integrate/fil-003-005?expand=1
- https://github.com/Qiao527/football-intelligence-lab/compare/integrate/fil-003-005...feat/fil-v03-match-explorer?expand=1

API diagnosis: Git succeeds, supported repository API returns Forbidden. Config
inspection shows api.github.com absent from network destinations. A saved draft
adds only that host (preserving presets) plus install_script/start_skill; save
returned requires_publish=true. Owner action: review/save/publish the environment
draft. That is configuration activation, not new data-rights permission. After
activation retry authorized API once; if still denied, grant the platform GitHub
connection/App the repository-scoped PR/check/content permissions described in
GITHUB_AUTOMATION.md. No credentials were extracted or altered, no PAT requested,
and the same denied request was not repeatedly retried.

The dispatch-only Actions workflow is prepared on the product branch, not
installed/activated on main or hosted-tested. Its exact-SHA integration-only
scope, read-only verification job, separate limited delivery job, mandatory
nonempty passing protected checks, clean merge state and no admin bypass are
reviewed. Maintainer installation must itself use a reviewed PR. This is an
optional supported route, not a claimed completed automation deployment.

Only the explicitly approved FIL-003–005 integration may merge autonomously
when hosted checks and all guards actually pass. Product/future automatic merges
need an explicitly established authorized workflow; the integration-only grant
is not blanket permission. After the integration squash merges, preserve a
backup and transplant only product commits after the latest incorporated
integration anchor `195a3efb4bef7441757f4e66f98d1ad410374dc9` onto updated main,
review the diff, rerun affected/full checks, retarget the product PR and preserve
new code/manifest lineage. Do not replay the old FIL-002–005 stack.

Existing registration/noncommercial-research confirmation persists. Provider
raw, derived records and screenshots stay local; no commercial/redistribution
permission or source terms are expanded. Original reference documents and MIT
LICENSE remain unchanged. Hosted merge eligibility, full spatial validation,
performance budget and human product review are the outstanding limits, not
reasons to discard the functioning verified local product.
