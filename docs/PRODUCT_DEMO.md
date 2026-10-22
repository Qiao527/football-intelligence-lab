# FIL local product review

This stabilization updates existing draft PR #12. No new feature branch/PR,
ratings, AI Analyst, deployment or data-rights change. All five product/integration
PRs remain unmerged. This checklist is for human acceptance; automated verification
is separate and does not constitute human sign-off.

## Start and reproduce

Use Python 3.11 and the pinned uv version in `pyproject.toml`:

```bash
uv sync --frozen --group browser
export FIL_DEMO_CONFIG=/absolute/path/to/verified/local-config.json
uv run --frozen python -m fil.explorer --config "$FIL_DEMO_CONFIG" --port 8514
```

Open `http://127.0.0.1:8514`. The already-prepared local France–Croatia config in
this workspace is also recorded by `/tmp/fil-v05-config-path`. To locate it without
rebuilding any input: `rg --files --hidden --no-ignore data/interim -g local-config.json`.
For preparing a new verified bundle, follow README's source/clock/score pipeline;
do not create substitute data or edit a manifest to pass verification.

In another terminal, regenerate the connected review package:

```bash
uv run --frozen --group browser python scripts/check_product_browser.py "$FIL_DEMO_CONFIG" \
  --url http://127.0.0.1:8514 --output data/interim/stabilization-review
```

The script uses the installed `/usr/bin/chromium`. Screenshots and provider-derived
browser/CDP traces remain ignored under `data/interim/`. Do not attach them to
GitHub, publish them or redistribute the fixture without rights review.

## A connected 10-minute walkthrough

1. **Match Explorer.** Start with Reset filters. Confirm France **4–2** Croatia,
   **2,978** records, **23** shots and **2.578** total source xG (rounded). Select
   Period 2 and Croatia. The shared-selection caption and selected counts change;
   the official final score stays fixed. Click a shot and a threat bin. Inspect
   the exact original ID, provider timestamp, score state and JSON.
2. **Tactical Dashboard.** Switch View without resetting. Period/team/window stay
   selected. Click a diamond (directed pair) or circle (player), then inspect an
   original contributing action. Set minimum passes per displayed link to 3 to
   declutter: only the drawing changes, while counts and evidence retain every
   selected pass. Try hover names and the all-names toggle. Event-average pass
   origins are not player tracking or certified physical formations.
3. **Possession Flow.** The same filters select relevant native sequences. Pick a
   native ID and a plotted pass/carry endpoint; inspect source order, original ID,
   actor versus possession owner, and outside-filter context. Reset and inspect
   native ID 91: it spans periods and does not certify continuous control or a
   continuous path. Unresolved endings remain explicit.
4. **Player Evidence.** Shared filters still apply. Choose a player first, then
   Involvement, Passing, Progression or Shot context. Read the selected player's
   compact measures without horizontally scrolling a table. The comparison table
   contains four columns per group, with names and plain labels. Inspect a linked
   pass and its context shot; a shot may be outside the selected event type/window
   and must say so. Position intervals remain original metadata. Minutes/per-90,
   inferred roles, causal credit and cross-match ratings remain unavailable.
5. **Empty selection and reset.** Combine an incompatible event type/outcome or
   an actorless record with Player Evidence. Expect a clear empty explanation and
   no stale action. Reset filters restores source totals, clears incompatible
   player/window state and resets the network display threshold to 1.
6. **Mobile.** Repeat at 390×844. Open/close the sidebar, change a filter, navigate
   all four views and inspect a player measure group. Labels wrap; selected-player
   measures require no table scrolling. Comparison tables can still scroll within
   their own area. Check chart readability and exact event drilldown by touch.

## Human acceptance checklist

- [ ] Shared scope is clear while navigating all four views; official score and
      selected xG/counts cannot be mistaken for one another.
- [ ] Names, player measure cards, filters, loading indicators and empty states
      are understandable at desktop and mobile sizes.
- [ ] Dense networks are readable with display thresholds and hover labels;
      changing the drawing never suggests filtered-out passes disappeared from facts.
- [ ] Exact original-action drilldown is usable in every view, including contextual
      actions outside the current filter and native IDs spanning periods.
- [ ] Uncertified minutes/roles/physical ends and insufficient cross-match evidence
      remain clear; no player ranking or hidden-player claim is implied.
- [ ] Measured cold-start and interaction results in `STABILIZATION_REPORT.md`
      are acceptable, or their remaining failures are explicitly accepted/deferred.
- [ ] Local screenshots are reviewed. No provider-derived data, screenshots or
      traces are approved for publication by this checklist.

## Local evidence map

`data/interim/stabilization-review/` contains `product-browser-report.json`,
`{match,tactical,possession,player}-{desktop,mobile}.png`, and mobile detail images
showing charts/player measures rather than just page introductions. Subdirectories
`explorer/`, `tactical/`, `possessions/`, `players/` contain the original browser
regression suites and their source-evidence screenshots. Independent source audit
results are `{explorer,tactical,possession,player,score}-source.json`.

`data/interim/stabilization-benchmark/` contains all ten interleaved pairs,
per-stage browser/server/IPC measurements, raw CDP trace JSON and process logs.
Diagnostic and pilot runs are kept separately, never silently pooled into the
acceptance experiment. See `scripts/benchmark_product.py --help` and the report
for exact source snapshots, order, variability and known limitations.
