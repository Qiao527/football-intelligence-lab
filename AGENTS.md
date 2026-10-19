# Football Intelligence Lab — Codex Repository Instructions

## Mission and source of truth
- Build an interactive, evidence-traceable football event analytics system. First deliver **v0.3 Match Explorer** using an actual licensed/open historical match; only later add networks, possession value, scientific discovery, and an AI Analyst.
- Read `docs/Football_Intelligence_Lab_Master_Reference.md` (product scope) and `docs/Football_Intelligence_Lab_Engineering_Handbook_v3.0.md` (implementation contracts) if present. If unavailable, report the missing document; do not invent its contents.
- Current reference fixture is StatsBomb's historical **2018 France–Croatia final, match_id 8658**. Never label this dataset as a 2026 Brighton match. Verify metadata from downloaded source.
- Treat the existing v0.2 Notebook as an exploratory prototype, NOT proof that v0.3 infrastructure exists.

## Non-negotiable integrity rules
1. Raw provider files are immutable. Record source URL, fetch timestamp, SHA-256, licensing/attribution, schema adapter version and commit SHA in a manifest.
2. Preserve original `event_id`, `period`, provider sequence/index, player/team ID, provider timestamp and coordinates; any missing metric remains null/NA, not zero.
3. Implement period-aware match clocks. Do not infer half boundaries from `minute` alone; distinguish stoppage time, extra time, and penalty shootout.
4. Keep `team` and `possession_team` distinct. Treat own goals, open-play penalties, and shootout attempts separately. Reconcile scoring with source metadata.
5. Use the source-provided xG for v0.3. Do not generate xG, xT, pressures or spatial positions from prose or from an LLM. Event data does not equal tracking data.
6. Every public metric needs an explicit definition, data domain, inclusion/exclusion rules, model/version, uncertainty where relevant and source event IDs.
7. A player label such as `underrated_candidate` is a hypothesis pending contextual, historical and counter-evidence checks, not a causal judgement.
8. Never import third-party skills, hooks, dependencies or remote scripts solely because they are starred. Review source, license, permissions and pin a verified version before adoption.
9. Do not scrape commercial football sites or redistribute protected content without an explicit source policy and necessary permissions.
10. No invented results, screenshots, tests, metric totals, timings, coverage, or compatibility claims. State what was actually run and what was not.

## Development discipline
- **Codex is the primary implementing agent.** Work as lead engineer: inspect before editing; propose a scoped implementation plan; implement a vertical slice; test; self-review; provide actual evidence.
- Prefer small, reviewable PRs aligned with one FIL issue. Avoid refactoring unrelated modules or adding microservices/agent orchestration during v0.3.
- Python 3.11 target, type hints for public interfaces; use Pandas/Parquet/DuckDB. Keep math in `src/fil/`, never hidden in UI callbacks.
- Tests must cover happy path, malformed source, period transitions, own goal/penalty exceptions, no-shot windows, duplicate event IDs, data provenance, and idempotent rebuilds as applicable.
- Run `ruff check .` and `pytest -q` whenever environment supports them. If unavailable, record blockers and do not report PASS.
- Report changed files, exact commands/exit codes, fixture provenance, failed/skipped tests, UX evidence (for UI tasks), risks and next dependency.
- Do not publish/merge/deploy, enable broad network/credential permissions, install unreviewed plugins, or alter source data without explicit approval.

## Phase gate
- G0 Source usable + rights recorded → G1 Normalization and schema PASS → G2 Period-aware timing and score reconciliation PASS → G3 Shots/xG and windows PASS → G4 Shared filters + drilldown PASS → G5 v0.3 user review.
- No AI Analyst, cross-match causal claims or advanced simulation until their independent gates are met.
