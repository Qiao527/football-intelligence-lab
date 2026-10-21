# FIL v0.3 — local source-verified Interactive Match Explorer

Parent: `integrate/fil-003-005` at `329362e86612d8320f1ee9ccd6d0eb6be01260ae`.
Integration PR targets main; this product branch stays independently reviewable
against the integration while hosted delivery is blocked. No automatic product
merge is claimed or authorized by the integration-only merge grant.

Builds the handbook's Streamlit/Plotly vertical slice: verified source shot xG,
NPxG, cumulative progression, 5/10/15-minute period bins, source-native shot map,
score-state view, shared period/window/team/player/type/outcome filtering and
exact event JSON/source-manifest drilldown. Data, screenshots and local config
stay ignored; raw/canonical/clock/score records remain immutable. Streamlit
1.50.0 and Plotly 6.3.1 are the scoped runtime additions; Playwright 1.55.0 is
optional browser tooling. Lockfile hashes pin transitive dependencies.

Use README's frozen setup, `python -m fil.explorer.bootstrap --raw ...
--pipeline-revision "$(git rev-parse HEAD)"`, then launch `python -m fil.explorer
--config ...`. Loopback only, telemetry disabled, no deployment/external dataset
service. No ratings, networks, AI or new data rights.

Actual source totals: France 8 shots / 1.097963608 xG / 0.314463608 NPxG;
Croatia 15 shots / 1.4802876897 xG/NPxG. Final score 4–2 independently reconciles
with official metadata; shot-goal count is five plus one linked own goal.
See METRICS.md and reports/MISSION.md for definitions, commands/exits, real/fresh
verification, browser screenshots/interactions, limitations and gate assessment.

Includes an optional dispatch-only Actions integration workflow, restricted to
the one explicitly approved integration branch/SHA, with no bypass flag, future
merge grant, credential extraction or provider-data upload. It has not run on
GitHub and needs maintainer installation/permission setup. Environment draft
adds only api.github.com; runtime activation/authorization is unconfirmed.

Hosted CI and independent human product review remain pending; no acceptance,
merge or deployment claimed. API limitation and one-time remedy:
GITHUB_AUTOMATION.md. Exact product PR link:
https://github.com/Qiao527/football-intelligence-lab/compare/integrate/fil-003-005...feat/fil-v03-match-explorer?expand=1
