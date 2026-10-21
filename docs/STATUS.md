# FIL status — autonomous integration and local v0.3 candidate

- Main contains FIL-002 squash #3 at 0fd8306. Clean integration branch
  `integrate/fil-003-005` at 195a3ef adds only FIL-003–005, two score-semantics
  regressions/fix and evidence/CI scope. Original stack branches and PRs remain
  intact with recoverable backup refs. No merge, rebase or deployment performed.
- `feat/fil-v03-match-explorer` builds on that validated integration and contains
  the working local Streamlit/Plotly Explorer: source shots/xG/NPxG, cumulative
  steps, transparent 5/10/15-minute threat bins, native shot map, score-state
  view, one shared filter, source event/JSON drilldown, desktop/mobile UI.
- Real pinned StatsBomb 8658: 2,978 retained events; France 4–2 Croatia official
  score reconciles independently; 23 shots/23 cumulative points/80 window rows.
  France: 8 shots, 1.097963608 xG, 0.314463608 NPxG. Croatia: 15 shots,
  1.4802876897 xG/NPxG. No invented observations or tracking.
- Integration: 253 passing tests. Product: 276 passing tests, 0 skipped;
  frozen lint/lock/build, fresh editable/regular installs and independent source
  reconstruction pass. All 23 local input/output files preserve bytes/mtimes on
  bootstrap reuse; fresh regular fixed-input facts/QA reproduce byte-for-byte.
  Eight real browser interaction checks pass, including native chart clicks,
  empty/reset/rerun behavior, exact ID/timestamp lookup and mobile filtering.
- Cold startup exceeds the handbook's 3s target (about 5.4s observed); warm
  check about 1.9s. No blanket performance PASS. Only Linux/Chromium verified;
  full spatial-direction gate and independent human review remain pending.
- Local technical evidence supports source shots/time/score and shared-filter/
  drilldown requirements, not full v0.3 acceptance or hosted CI. No ratings,
  networks, xT, AI, deployment, source mutation or rights expansion.
- Git API Forbidden blocks PR creation/hosted inspection. Config inspection
  identifies missing api.github.com destination; saved narrow network plus
  tested install/start draft requires owner review/save/publish. No credentials
  extracted/replaced. Integration-only Actions workflow is prepared, unactivated
  and untested on GitHub. Only the specifically approved integration may merge
  autonomously after actual hosted checks/guards pass; product automatic merge
  permission is not inferred.
- README has reproducible setup/bootstrap/launch and optional browser commands.
  docs/reports/MISSION.md records actual code versions, commands/exits, artifact
  hashes, screenshots, critical fixes, remaining limits and exact PR links.
  Data and screenshots remain ignored local noncommercial research artifacts.
