# Autonomous delivery after API recovery — 2026-10-21

Runtime implementation: `d0ea933c8aa9432b10eaabd62000219d1f0e1c98` on the existing
`feat/fil-v03-match-explorer` branch. Subsequent evidence-documentation commits
do not change this implementation. No integration/product merge or deployment.

## Integration eligibility and one owner decision

PR #7 remains draft at `195a3efb4bef7441757f4e66f98d1ad410374dc9`, targeting main
`0fd8306e6d09a2ab062acb39443272f145114572`. Its exact 39-file integration diff
and three commits were rechecked; no FIL-002 history replay or whitespace errors.
It is MERGEABLE/CLEAN and both observed lint-and-test runs succeeded, including
[PR merge-ref CI](https://github.com/Qiao527/football-intelligence-lab/actions/runs/39656148449).
Repository REST/PR GraphQL access succeeds. The previous Forbidden problem is resolved.

The applicable-rules endpoint still returns HTTP 403, explicitly requiring
GitHub Pro or public visibility for this private repository. No enforced required
checks are established. This is one owner-level plan/protection decision, not a
software failure. No merge, paid purchase, visibility change or bypass attempt
was made. [MAIN_PROTECTION.md](../MAIN_PROTECTION.md) supplies the minimal owner
setup: PRs, actual GitHub Actions lint-and-test, no force pushes/deletion or
administrator bypass, and approval only if an eligible independent reviewer
exists. Enforcement must be read back before any authorized squash merge.
Product work continued while this remained unresolved. PR #8 retains its
integration base and stays unmerged pending acceptance.

## Cold-start result and profile

Historical report: 5.419 seconds in the previous environment/session. A new
three-run baseline on unchanged `abcb3cb` was measured before runtime edits;
it is the comparison baseline below rather than assuming identical host speed.

The benchmark starts a fresh server process and Chromium context for every run,
at 1600×1150. It uses exactly the original navigation → **Event ledger heading**
milestone. The original pinned local config is identical for both sets. Server
readiness and browser launch are recorded separately, outside navigation. No OS
page-cache eviction, preload, skipped verification, external request or synthetic
match data is used. The later evidence-element milestone is reported separately;
the ledger heading alone is not a claim that every browser component has painted.

| Seconds | Baseline | Final implementation |
| --- | ---: | ---: |
| Navigation → ledger, run 1 | 7.140 | 3.659 |
| Navigation → ledger, run 2 | 6.141 | 3.440 |
| Navigation → ledger, run 3 | 7.108 | 5.264 |
| Median | **7.108** | **3.659** |
| Navigation → evidence element, median | 7.196 | 5.317 |

Median ledger improvement is **48.5%**. All runs, including the slower third run,
are retained. **The ≤3-second target is not met.** The separate final full-browser
acceptance run measured 5.007 seconds to the ledger. No universal speed claim.

Final process timings (seconds): server ready 0.417–0.429; Chromium/context launch
0.429–0.525; post-import page setup 0.105–0.107; full source verification
0.809–1.025; view preparation 0.022–0.024; shared filtering 0.052–0.056; chart
construction/submission 0.191–0.242; ledger/evidence submission 0.024–0.045.
A separate fresh-process import probe measured Streamlit 0.236 and data modules
0.154 seconds; Plotly graph_objects import was already satisfied through the
Streamlit dependency path. Imports and chart submission are not browser paint.
Remaining navigation time includes frontend hydration/rendering, transport and
scheduling; those contributions are not individually certified by these probes.

The data cProfile identified repeated wide Arrow→Python conversions and per-event
SourceContext copies. The fix projects only consumed columns, retains original
Arrow columns when appending score states, filters shots with Arrow kernels,
renders the ledger as Arrow, and loads full JSON for the selected event only.
The full raw→canonical→clock→score recomputation still runs on a cache miss.
No source validation, manifest/hash check, reconciliation or exception was removed.

Profiling also led to a cache correctness fix: roles, directory structure and
file-byte digests participate in a versioned key. Added empty directories now
invalidate cached verification, and symlink roots fail. Cache keys cannot hide
these changes behind previously verified file bytes.

## Spatial validation

[SPATIAL.md](../SPATIAL.md) records the audited pinned provider PDF, its SHA-256
and visually inspected pitch diagram. Native extent is 120×80 with y downward.
All start/end coordinates are checked for finite values/bounds; nulls stay null.
The map uses identity display, retaining original event IDs, coordinates and JSON.

The five Shot/Goal records end at x=120, with goal evidence for each team in each
observed period. This corroborates the unchanged positive-x shot frame. It is not
proof of physical stadium ends or all non-shot conventions. Recursive field
inspection of events/lineups and the official match found no explicit direction/
orientation/attacking-end field; match metadata declares data_version 1.0.2.
No home/away or period-parity flip is applied. Physical directions remain
explicitly null/uncertified. Event coordinates are not tracking.

Ten new spatial cases exercise both teams/halves, identity preservation, missing/
opposite goal evidence, no-shot/null uncertainty, invalid domains, nonfinite
coordinates and start/end bounds. Independent source verification now checks each
shot's original start/end coordinates and the spatial QA's goal IDs/endpoints.
The scoped native-coordinate audit passes; physical-direction certification is
unavailable from these inputs and broader gate acceptance remains with the owner.

## Product checks, regression evidence and remaining acceptance

Desktop and 390px mobile screenshots were inspected. Corrected overlapping
chart titles/legends, made mobile metrics a compact two-column grid, and replaced
ambiguous cleared dropdown placeholders with explicit All/Entire labels.
Period/width changes clear time bins; period-specific charts omit other periods;
Reset restores the default 15-minute width. Incompatible player selections clear
when teams change. All selected foreground panels retain the same event IDs.

Two runs of the expanded UI regression against the original app reproduced:
reset retained a 5-minute width instead of 15; and a Period 2 threat chart still
contained Period 1 bars. They pass against the corrected app. The first temporary
test invocation needed the repository on PYTHONPATH; its collection failure was
not treated as a reproduced product defect. Browser-harness fixes use the
combobox's observed aria-label and await rerun completion to avoid testing an
empty search input or a detached Plotly path; real mouse clicks remain in use.

The final browser run passes ten groups: full-match 2978/23/source xG/4–2;
period/team synchronization; empty state; complete reset; period/width windows;
team/player consistency; exact shot-click ID/timestamp; actual threat-bar bin
selection; mobile no horizontal overflow; mobile sidebar/filter updates. No page
exceptions or external requests. Sixteen measured filter/reset interactions,
waiting for metric AND chart state, range **0.586–2.409s**, median **1.242s**.
The handbook's usual 0.5–1.0s interaction budget is not consistently met.

Actual final validation at the implementation SHA:

| Commands | Result |
| --- | --- |
| `uv lock --check`; `uv sync --frozen`; `uv run --frozen ruff check .`; `uv build` | exit 0 |
| `uv run --frozen pytest -q` | 288 passed, 0 skipped, 4.65s, exit 0 |
| Frozen regular installation in `/tmp/fil-product-regular`; regular Ruff/pytest | 288 passed, 0 skipped, 6.09s, exit 0 |
| `python -m fil.explorer.bootstrap --raw RAW --pipeline-revision d0ea933c8aa9432b10eaabd62000219d1f0e1c98 --root data/interim/delivery-match` | full derived chain rebuilt, exit 0 |
| `scripts/verify_score_source.py RAW CANONICAL CLOCK SCORE` | 2978 states, six awards, one own goal, one scored penalty, official France 4–2 Croatia; exit 0 |
| `scripts/verify_explorer_source.py CONFIG` | 23 shots, 23 cumulative points, 80 window rows, exact source xG/coordinates and explicit direction uncertainty; exit 0 |
| Repeated bootstrap | 16 generated files retain identical bytes and mtimes |
| Original fixture/artifact snapshot | all 23 prior input files retain identical bytes and mtimes |
| `scripts/check_explorer_browser.py CONFIG --output data/interim/review-final` | ten real-browser groups pass, exit 0 |
| `scripts/benchmark_explorer.py ORIGINAL_CONFIG --output data/interim/benchmark-final` | three fresh-process runs recorded, exit 0 |

Python 3.11.14 / uv 0.12.23, pinned Streamlit/Plotly/Arrow unchanged. Initial regular
installation exited 2 because uv tried a read-only home Python directory. Selecting
the existing pinned Python executable via UV_PYTHON fixed setup; no test was
skipped. Exact command arrays, exits, earlier setup failure and full stdout/stderr
are retained in ignored `data/interim/delivery-review/commands.json`.

CONFIG is recorded in `data/interim/delivery-review/summary.json`, under
`data/interim/delivery-match/metrics/8cbc37c73a3e8108f4076a74f6769deb121a561081f953e493f332c6cfd96b97/fil-source-xg-1/d0ea933c8aa9432b10eaabd62000219d1f0e1c98/local-config.json`.
Original and final benchmark JSON, app stage profiles, and final browser-report
JSON remain in their ignored output directories. Updated screenshots are
`data/interim/review-final/{desktop,event-evidence,window-selection,mobile,mobile-filters}.png`.
Provider data/screenshots are not committed or uploaded to CI.

Remaining acceptance: cold/interaction performance budgets; explicit acceptance
of the scoped spatial frame and its uncertifiable physical directions; independent
human product review and final product merge authorization. Cross-platform and
broad accessibility certification remain unperformed. PR #8 is not merged or
deployed. Hosted CI belongs to the exact pushed head and is checked separately
through the existing PR; local passes alone are not a hosted success claim.
