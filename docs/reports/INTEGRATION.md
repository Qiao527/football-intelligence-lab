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
