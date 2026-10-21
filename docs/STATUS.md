# FIL project status — local v0.3 review candidate

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
  remain open. No product merge, deployment, new data rights, AI or tactical claims.
  Exact evidence, executed commands and limitations:
  [AUTONOMOUS_DELIVERY.md](reports/AUTONOMOUS_DELIVERY.md). Hosted CI is checked on
  the current pushed PR head separately; earlier local results do not imply it.
