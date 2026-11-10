# FIL-003–005 clean integration / 2026-10-21 UTC

Base: origin/main `0fd8306e6d09a2ab062acb39443272f145114572` (FIL-002 squash #3).
Source anchor: FIL-002 `5a18a4e1a417cfbf33941796552b25c9c8ab0c36`.
Source head: FIL-005 `9afe745d701cbb695dc45ddbc32332878f6aa99d`.

Recoverable refs: `backup/mission-20261021/fil-002-data-acquisition`,
`.../fil-003-event-normalization`, `.../fil-004-period-aware-clock`,
`.../fil-005-score-reconstruction`, retaining the original remote heads.
Previous branches/PRs are intact. The FIL-002 anchor and main trees are identical.
Created `integrate/fil-003-005` from main and applied only the binary tree diff
from FIL-002 anchor to FIL-005 head using `git apply --3way --index`.
No conflicts; first integration commit `bfe22de` has an exactly identical tree
to FIL-005 head. No FIL-002 feature history was replayed. No force push/rebase.

## Critical review

Reviewed canonical/source hash and record preservation, clock endpoint/ties/
stoppage/extra/shootout policy, linked own-goal attribution, malformed fields,
artifact publication, dependency pins and repository automation boundaries.
Discovered scoring signals could mislabel a penalty, or swap same-team goal/miss
while passing final reconciliation. Two regression tests reproduced the defect
(2 failures / 71 passing score tests); fixed by comparing scored/penalty flags
with verified canonical shot fields. Full suite now 253 passing, no skipped;
Ruff/build pass. CI push scope now includes `integrate/**`.

This is independent-style review and independent source recomputation by the
implementing agent, not a claim that a separate human reviewer approved it.
No known critical findings remain after corrections; hosted CI is still required
before the specifically owner-authorized integration merge.

## Delivery/API diagnosis

Native Git fetch/push succeeds via the platform's scoped HTTPS Git proxy.
`gh api repos/Qiao527/football-intelligence-lab` exits 1, HTTP Forbidden.
Git and REST/GraphQL are separate authorization surfaces. No usable alternative
API connector is exposed. Token presence, login prompts and Git access cannot
establish API permission; exact upstream denial policy cannot be inspected.
No credential values were inspected/copied and no proxy route was bypassed.

One-time supported remedy: authorize repository REST/GraphQL operations through
the platform GitHub connection/App, including PR read/write, checks/Actions read,
and repository contents write for the already-authorized integration merge.
Alternatively, a maintainer can activate a reviewed repository Actions workflow
with a repository-scoped GITHUB_TOKEN. Branch protections/required reviews and
CI remain mandatory. Do not grant organization-wide or unrelated repository access.

Hosted CI is unobserved while API access is denied; no merge is attempted or
claimed. The integration PR targets main:
https://github.com/Qiao527/football-intelligence-lab/compare/main...integrate/fil-003-005?expand=1
Local verification details are recorded in the mission report after execution.

## Executed clean-environment and real-data evidence

Implementation `329362e86612d8320f1ee9ccd6d0eb6be01260ae` was cloned with
no hardlinks into `/tmp/fil-integration-4ksmw_52/checkout`, initially empty uv
cache. All commands below exited **0** on Python 3.11.14 / uv 0.12.23:

- `uv lock --check`; `uv sync --frozen`; `uv run --frozen ruff check .`
- `uv run --frozen pytest -q`: **253 passed**, 0 skipped (2.43s).
- `uv build`: wheel and source distribution built.
- `UV_PROJECT_ENVIRONMENT=.venv-regular uv sync --frozen --no-editable`
- Regular frozen Ruff and pytest: **253 passed**, 0 skipped (2.21s).
- Regular `python -m fil.ingestion.normalize build`, `python -m fil.time build`,
  `python -m fil.metrics.score_cli build` and `verify`, all with actual integration
  implementation SHA and verified raw/canonical/clock arguments.
- `python scripts/verify_score_source.py RAW CANONICAL CLOCK SCORE`: independently
  verifies all **2,978** source/canonical/clock/score states, six goal awards,
  one own goal (two linked representations counted once), one scored penalty,
  final **France 4–2 Croatia**, matching original official metadata.

Raw source remains the official reviewed Hudl/StatsBomb revision
`4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. Event SHA-256
`a9aa72c042153fa351c3591ee11e7fba95b0c8841c4489da4aa6809de1edbdf5`;
match metadata SHA-256
`f89dbd4aedcaf9c9e4ec9d8e745d5d54596500ec357d7489c914a2f126805adf`.
All original bundle file hashes/mtimes were checked before/after and unchanged.
Exact command arrays, exits and generated input/output paths are retained locally
in `/tmp/fil-integration-verification.json` and fresh-clone logs. Earlier FIL-005
reports retain original code-specific manifest/output hashes as historical evidence.

No licensing change, dependency drift beyond FIL-003's PyArrow 21.0.0, raw data
modification, existing branch rewrite or conflict. Two regression failures were
corrected rather than bypassed. No hosted success or merge is claimed.

Later environment inspection identified api.github.com missing from the current
network destination list. A draft adds only that custom host, preserving presets,
plus tested install/start instructions; save returned requires_publish=true.
Owner must review/save/publish that environment draft, then retry the authorized
API once. Exact denial cause/API auth remains unconfirmed until activation;
no credentials were extracted or replaced. This is the one-time delivery action,
not a reason to discard the verified integration or block product implementation.
