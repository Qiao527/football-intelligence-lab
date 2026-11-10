# Player involvement foundation — engineering evidence

Historical PR #12 foundation evidence. Later UX and performance measurements are
in [the stabilization report](STABILIZATION_REPORT.md) and [local product review](PRODUCT_DEMO.md).

## Integration and stack

GitHub API access works. PR #7 remains OPEN/DRAFT and unmerged at
`195a3efb4bef7441757f4e66f98d1ad410374dc9`, MERGEABLE/CLEAN, with successful
hosted `lint-and-test` checks. Its complete integration patch was retrieved and
reviewed (3 commits, 39 unique files, 5420 additions / 38 deletions). Main remains
`0fd8306e6d09a2ab062acb39443272f145114572`, `protected:false`.

Actual applicable-rules readback returned HTTP 403: “Upgrade to GitHub Pro or make
this repository public to enable this feature.” The administration endpoint
separately returned “Resource not accessible by integration.” These restrictions
were checked once; documentation and green CI do not satisfy enforced protection.
No ready transition, merge, downstream transplant, retarget, deployment, plan
purchase or visibility change was performed.

Existing PR #8 (`363494ccd8b7f42f40526d0b0d54a19c112f1d68`), #10
(`2645eb916e0a1980eb6e650c494ce8395a7ebd32`) and #11
(`83586739faeeb351dabe364db1df33747960bf4e`) remain open drafts with their existing
bases and successful hosted CI. This branch is based exactly on #11; the new
review must stay stacked there. The one owner action remains activating the
supported plan and completing/readback-verifying [main protection](MAIN_PROTECTION.md).
An authorized owner readback can resolve the App administration restriction;
broader App permissions are not automatically required. New product merges
still need separate acceptance/authorization.

## Implemented and independently verified

See [metric definitions](PLAYER_EVIDENCE.md) and the
[future discovery research design](HIDDEN_DISCOVERY_RESEARCH_DESIGN.md).
Player Evidence shares filters and offers exact original action/shot drilldown,
observed involvement, completed/failed/unknown passing, progression, pre-shot
participation, native position metadata and explicit uncertified exposure.
Versioned immutable exports preserve per-source/match/team/player grain. No
ratings, causal allocations, inferred minutes, role assignments or off-ball claims.

Possession v2 fixes own-goal/turnover overlap and missing terminal evidence, with
regression tests. It leaves v1 outputs intact. All 2978 original events remain;
182 native IDs, 594 opposition-context records, 36 turnover endings, 82 unresolved
boundaries and cross-half ID 91 are retained. Native ID is not a claim of continuous
physical control. Physical attacking ends remain unknown.

Original JSON reconciliation reports 45 lineup records, 27 observed actors,
2919 actor-attributed records and 59 actorless records; 650 completed passes,
151 progressive passes, 73 progressive carries, and 16 reciprocal native
pass-to-shot links with descriptive linked source xG 1.0024921537. Independent
score and source-xG checks preserve France 4–2 Croatia and total source xG
2.5782512977. Tactical verification includes 160 filter/context queries;
possession verification includes 480 period/window/team/score queries and the
new terminal-evidence audit. Production extraction is not used to generate
expected raw values in these scripts.

## Validation executed

All commands below exited 0 after fixes; no skips reported:

- `uv lock --check`; `uv sync --frozen --no-editable --reinstall-package football-intelligence-lab`
  in a fresh `/tmp/fil-player-wheel` environment, pinned Python 3.11.14.
- `uv run --frozen ruff check .`; `uv run --frozen pytest -q`: **354 passed**
  (11.83 seconds latest editable run).
- Fresh regular installed package: `uv run --frozen --no-editable pytest -q`:
  **354 passed**, 8.98 seconds. `uv build`: wheel and sdist succeed.
- `fil.explorer.player_data` and `fil.possessions.artifacts` generated new local
  versioned bundles at implementation SHA `82e713a996ca4e4f3e15d2affd7d0b9707619830`.
  Tests cover repeat reuse without byte/mtime changes and rejection of corruption.
- Independent `verify_players_source.py`, `verify_possessions_source.py`,
  `verify_explorer_source.py`, `verify_tactics_source.py` and `verify_score_source.py`:
  PASS on the original France–Croatia files, including original source SHA checks.
- Real Chromium: `check_explorer_browser.py`, `check_tactics_browser.py`,
  `check_possessions_browser.py`, `check_players_browser.py`: PASS at desktop and
  390px mobile, zero page errors/blocked external requests. Actual plotted clicks,
  filter resets, empty selections, stale-player reset, outside-filter shot context,
  official-score/source-xG synchronization and opt-in audit restoration verified.
- All 23 snapshotted raw/canonical/clock/score/metrics/config input files preserve
  original SHA-256 and modification nanoseconds.

Early synthetic own-goal test failed because the fixture assigned conflicting
owners to one native ID; corrected the fixture. Browser checks initially failed
on a rerun race, an input `inner_text` assertion and an audit-table count; fixed
synchronization/locators/counts and reran. No failed check was ignored.

Local evidence is intentionally ignored by git: `data/interim/player-review/`
contains raw reconciliation JSON, browser reports and screenshots (desktop player
summary, original shot context, mobile players, plus Explorer/Tactical/Possession
regression screenshots). Source data and derived evidence are not uploaded to GitHub.

## Performance: targets remain unmet

Paired runs use the same verified local bundle and current benchmark script,
parent source via `PYTHONPATH=/tmp/fil-mission-parent/src` versus current source.
Three parent runs then three current runs, fresh server/browser per run, Chromium
1600×1150, no OS cache eviction, identical ledger/evidence milestones. Server
readiness/browser launch are separately measured. No other browser/test workload
was intentionally run during this final pair. This small sequential experiment
cannot establish a causal performance regression or improvement on a shared host.

| Seconds, median of 3 | Parent #11 | Current |
| --- | ---: | ---: |
| Navigation → Event ledger (cold milestone) | 3.412 | 5.176 |
| Navigation → charts and original evidence | 4.932 | 5.657 |
| Tactical opening | 2.230 | 2.732 |
| Possession opening | 2.080 | 2.057 |
| Tactical period filter | 1.461 | 1.713 |
| Tactical team filter | 0.980 | 1.049 |

All cold ledger samples: parent [3.379, 4.862, 3.412], current
[4.082, 10.246, 5.176]. No sample discarded. This is **no demonstrated end-to-end
improvement**; the ≤3-second startup and normal interaction budgets remain open.
These paired results are not directly comparable to earlier 6.545-second Tactical
runs on another session. Other browser-suite timings were concurrent/warm and
are functional evidence, not replacement performance results.

Server profiles: median cold verification 0.806 → 0.868 seconds; chart work
0.205 → 0.191 seconds. Possession view work 0.425 → 0.358 seconds after deferring
unrequested full audit serialization. Tactical view work 0.587 → 0.640 seconds.
Browser-visible time includes rerun scheduling, transport and rendering beyond
these stage timers; those components are not separately attributed by this probe.
Readiness and browser launch each remain about 0.4–0.5 seconds outside navigation.

Audit tables now render only when requested, with integrity checks unchanged.
Dense-network names default to hover with an all-names toggle. Player tables
remain wide and require horizontal table navigation on mobile; per-player evidence
is available beneath them. Larger rerun/render costs and occasional long-tail
interactions remain acceptance blockers. Next performance work needs browser/IPC
tracing and a larger interleaved benchmark before any speed claim.

## Scientific and acceptance limits

Only one fixture is independently verified. Cross-match concatenation contracts
are implemented; cross-match findings are not. Minutes certification, sufficient
role/state/opponent exposure, power/stability analysis, preregistered screening,
held-out replication, independent review and multiplicity/counterevidence tests
are prerequisites for defensible Player Intelligence/Hidden Discovery claims.
The research document proposes eligibility floors for future evaluation; they
are not validated production thresholds. Product acceptance and protected merge
authorization remain outstanding.
