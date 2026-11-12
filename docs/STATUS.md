# FIL project status

**Current:** the scouting decision study is complete. A tournament-stage design
stopped at its measurement ceiling; the league-stage design passed both gates and the
source-xG increment replicated in a held-out league. Nothing is merged, deployed or
claimed as player ability.
[Research summary](research/SCOUTING_RESEARCH_SUMMARY.md) ·
[Replication](research/LEAGUE_CONFIRMATION_RESULT.md).

The delivery notes below are kept as history and are unchanged.


- The first factual v0.5 slice adds source-traceable possession reconstruction and
  interactive Possession Flow on `feat/fil-v05-possession-flow`, stacked on
  unchanged PR #10 at `2645eb9`. All 2978 records / 182 native possession IDs and
  594 opposition-context records are preserved; cross-half ID 91 stays flagged.
  Independent raw verification passes 480 window/team/score queries, official
  4–2 and source xG. 342 tests pass in editable and fresh regular installations;
  lint/build pass. No ratings, player candidate labels, off-ball movement or intent.
- Tactical arrow construction now assigns all 194 annotations once; complete
  real-team chart payloads equal the parent. Three-run tactical opening median
  4.925 → 2.309s, period filter 3.261 → 1.628s, team filter 1.818 → 1.043s.
  Default cold ledger median 3.706s still misses the 3s budget. Several tactical
  filters remain outside normal latency targets. Acceptance remains pending.
  Exact commands, source/UX evidence and limitations:
  [possession delivery report](reports/POSSESSION_DELIVERY.md).
- FIL-012 / Issue #9 adds the scoped Tactical Dashboard on a new stacked branch
  `feat/fil-012-tactical-dashboard`, parent Explorer SHA `363494c`. Source-verified
  completed passes, directed networks, event-average positions, progression v1,
  shared filters, comparisons and exact evidence are implemented. Physical
  directions remain unknown. 318 tests pass in editable and fresh regular installs;
  independent real-source counts: 650 completed passes, 194 pairs, 151 progressive
  passes and 73 progressive carries. All 2978 events/4–2/source xG preserved.
  Current cold-start median 4.134s still misses the 3s budget. See the exact
  [tactical delivery report](reports/TACTICAL_DELIVERY.md) for commands, browser
  evidence, performance limits and acceptance items. PR #7/#8 remain untouched.
- GitHub REST/GraphQL access recovered. PR #7 remains draft at 195a3ef, against
  main 0fd8306, with successful hosted CI. The private repository plan prevents
  enforcing the required protection guard. One owner decision/setup is recorded
  in [MAIN_PROTECTION.md](MAIN_PROTECTION.md); no merge or bypass.
- Existing PR #8 and feat/fil-v03-match-explorer continue on integration anchor
  195a3ef. Runtime implementation d0ea933 adds reduced Arrow/Python conversion,
  explicit spatial evidence/uncertainty, cache structure validation, filter fixes,
  mobile metrics layout and chart-title/legend separation. No dependency drift.
- Fresh same-method benchmark median 7.108 → 3.659s (48.5% reduction); final runs
  3.440–5.264s. Target ≤3s remains unmet. Final full-browser run 5.007s; filter/reset
  updates 0.586–2.409s, median 1.242s. Performance acceptance remains pending.
- Native 120×80, y-down coordinate audit passes. Coordinates/IDs are unchanged.
  Physical team/period attacking ends cannot be certified from available inputs;
  metadata explicitly retains unknown directions. No team/half flip or tracking.
- Editable and regular installation: 288 tests pass, zero skipped; lint/build pass.
  All 2978 original events independently reconcile to official France 4–2 Croatia.
  Shot xG, all bins, coordinate provenance and exact event drilldown reverified.
  All 23 previous input files retain their hashes and mtimes; 16 rebuilt files
  also preserve bytes/mtimes on reuse. Ten real-browser check groups pass with
  updated desktop/mobile screenshots kept local/ignored.
- Human product acceptance, cold/interaction budgets and integration governance
  remain open. No product merge, deployment, new data rights, AI or causal tactical claims.
  Prior v0.3 evidence, executed commands and limitations:
  [AUTONOMOUS_DELIVERY.md](reports/AUTONOMOUS_DELIVERY.md). Hosted CI is checked on
  the current pushed PR head separately; earlier local results do not imply it.
