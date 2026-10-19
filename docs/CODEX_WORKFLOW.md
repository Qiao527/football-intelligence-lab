# FIL Codex-first delivery playbook

## Responsibility
- Human project owner: chooses scope and success conditions, authorizes new dependencies, data redistribution and merges.
- Codex Lead Engineer: implements vertical slices, owns tests and PR readiness; may propose design changes as explicit ADRs.
- Independent reviewer: separate Codex review context or human code review; must check raw event facts and tests independently, not accept a self-report as proof.
- Optional Claude: product/UX critique or second opinion; no default ownership or conflicting concurrent edits.

## Routine (every ticket)
1. **Inspect:** status, branch, relevant AGENTS.md files, handbook, source manifests, prior regressions.
2. **Plan:** state issue, in/out scope, files touched, input fixture, acceptance commands and risks.
3. **Implement:** one atomic, testable improvement; no unapproved new stacks or nonessential refactor.
4. **Verify:** ruff, pytest, independent source-event reconciliation; test data semantics not just UI.
5. **Review:** PR description and checklist. A separate reviewer checks a fresh diff, evidence and exceptions.
6. **Human gate:** developer reviews UI/analytics and explicitly authorizes merge/deploy.

## Recommended first execution
Read AGENTS.md and the two project reference documents. Inspect the existing repository without changing files. Audit current v0.2 code and manifests against FIL-001–FIL-004. Report what exists, test coverage and discrepancies. Then implement ONLY the first missing prerequisite in a reviewable change, run actual checks and show evidence. Do not start AI Analyst, network simulation, a new frontend stack or unauthorized API scraping.

## Autonomous stacked development (owner policy, 2026-10-19)

Do not stop solely because a completed upstream implementation is unmerged.
When its branch is available, suitable and validated, create the dependent
feature branch from that branch's verified SHA. Inspect its source/rights status,
run applicable checks, and record evidence and unresolved assumptions. Continue
planning, implementing, testing, self-reviewing and fixing within approved scope;
stop for material blockers, mandatory approvals or scope completion.

For FIL-003 the parent is `feat/fil-002-data-acquisition`, PR #3. The owner reports
that PR exists and hosted CI passed; independently record local checks rather
than treating that report as a newly observed CI run. A stacked FIL-003 PR should
target that parent branch so its diff contains FIL-003 changes only. Record the
exact parent SHA and use `git diff <parent-sha>...HEAD` for independent review.
Develop in the existing checkout; do not create worktrees unless requested.

Before delivery, fetch the parent again. If it changed, inspect and reconcile
with the downstream branch (preserve existing work), then rerun all affected
tests. Do not silently reset the branch or ignore conflicting schema/rights
changes. If upstream is squash-merged, reconcile downstream onto the resulting
main history and retarget its PR so upstream commits are not reintroduced.
Retargeting/reconciliation does not authorize merging into main.

Record parent branch/SHA, dependency PR, changed files, commands/exit codes,
source provenance, limitations and upstream assumptions in each stacked PR.
GitHub API Forbidden responses do not invalidate completed engineering work:
push/preserve the branch, save the prepared PR body and provide the exact
GitHub PR creation link with the intended base branch.

Never bypass failing tests, expand data rights, merge into main, deploy or make
material architecture changes without approval. Implemented, locally verified,
hosted-CI verified and human accepted are distinct states. A milestone is not
accepted until required validation and human approval are complete.

## FIL-004 stack and squash reconciliation

FIL-004 starts on `feat/fil-003-event-normalization` at
`3d81faf9ae66f1b2075a1aba5b877baefa42e418` (PR #4), which depends on FIL-002
PR #3. The owner reports #4 hosted CI passed; local validation remains separate.
Until the parents merge, the FIL-004 PR targets FIL-003, keeping only FIL-004
changes in its diff.

Before delivery, fetch main and both parents and inspect the actual merge state.
After #3/#4 are merged, identify the latest verified parent SHA used by FIL-004
and preserve a recoverable local branch ref before reconciliation. For squash
merges, transplant only commits **after that FIL-003 parent SHA** onto updated
main (`git rebase --onto origin/main <recorded-parent-sha> <fil-004-branch>`).
Do not merge old feature history wholesale or rebase the entire main-to-child
range: that can reintroduce already-squashed FIL-002/FIL-003 commits.
If the parent itself has advanced, reconcile and record its new anchor first.
If remote parent branches were deleted after merge, use the retained recorded
anchor and main merge/content evidence; a missing remote head alone is not a
reason to discard downstream work.

Inspect the resulting diff against main, resolve conflicts using the verified
contracts, rerun affected/full checks and real-data verification, regenerate
artifacts with the new actual implementation SHA, and retarget the PR base to
main. Coordinate any published feature-history update using the expected remote
head (`--force-with-lease` only if a rewrite is necessary); never force main.
These are conditional reconciliation instructions, not a claim the parent PRs
have merged or authorization to merge them. Record actual observations and
defer milestone acceptance to required validation and human approval.

## Starred-tool policy

- Frameworks are **references**, not mandatory global plugins. Default: repo-native AGENTS.md + three narrow FIL skills + tests.
- Evaluate addyosmani/agent-skills OR obra/superpowers on a throwaway branch; compare against baseline; adopt only a useful subset after license/security review.
- K-Dense scientific skills: selective use for research stage; not required for ingestion/UI.
- gstack: optional review discipline; not needed to achieve v0.3.
- FinceptTerminal: UI inspiration only until license analysis permits more.
- No autonomous multi-agent manager, unattended credential/tool permissions, browser scraping or repository-wide hooks by default.

## FIL-005 dependency and sequential squash plan

FIL-005 develops on FIL-004 PR #5 at
`48d566a2664a21b84b4ba8777de39116eff5480f`; the owner reports #5 hosted CI passed.
The complete #3/#4/#5 stack snapshot and downstream-only transplant procedure
are in [STACK_RECONCILIATION.md](STACK_RECONCILIATION.md). Reconcile each child
using its latest incorporated parent anchor, propagating rewritten parents
through the stack. Keep recoverable refs and rerun verification before updating
published feature branches. No merge is authorized by this procedure.
