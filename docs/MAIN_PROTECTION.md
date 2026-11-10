# One-time integration governance setup

The repository stays private. On 2026-10-21 the branch-rules API returned HTTP
403: “Upgrade to GitHub Pro or make this repository public to enable this
feature.” This is one owner-level plan decision, not an implementation failure.
Do not purchase a plan, change visibility, weaken the merge guard, or repeatedly
request the same owner action. Product development continues on PR #8 meanwhile.

PR #7 head is `195a3efb4bef7441757f4e66f98d1ad410374dc9`; main is
`0fd8306e6d09a2ab062acb39443272f145114572`. Its 39-file diff is the FIL-003–005
integration plus reviewed score-semantic corrections, with no FIL-002 history
replay. Both push CI and the PR merge-ref CI passed. No merge is authorized
while the agreed protection guard is unenforced.

## Owner setup when a supporting plan is available

In repository **Settings → Branches → Add classic branch protection rule**,
select exactly `main` and configure:

1. Require a pull request before merging.
2. Require status checks to pass. Select the actual **lint-and-test** check
   with source **GitHub Actions** (App ID **15368**). Enable “Require branches
   to be up to date before merging.”
3. Enable **Do not allow bypassing the above settings**, including administrators.
4. Leave **Allow force pushes** and **Allow deletions** disabled.
5. For a solo maintainer, leave **Require approvals** disabled (zero required
   approvals). Enable an independent approval only when an eligible reviewer
   with repository write access is actually available. Do not require approval
   by the PR author or create an impossible solo-maintainer requirement.

Save the rule. No delivery workflow installation, PAT, public visibility,
unrelated repository access or broader App administration grant is needed.
If a ruleset is used instead, it must be **Active**, target the default/main
branch, enforce equivalent rules, and have no administrator bypass list.

## Read-back and merge conditions

The owner can read back a classic rule with their own authorized CLI:

```bash
gh api repos/Qiao527/football-intelligence-lab/branches/main/protection
```

Confirm `required_pull_request_reviews` is non-null, the check is exactly
`lint-and-test` from App 15368, `required_status_checks.strict=true`,
`enforce_admins.enabled=true`, `allow_force_pushes.enabled=false`, and
`allow_deletions.enabled=false`. Confirm the approval count matches reviewer
availability. The managed GitHub App cannot read this administration endpoint;
its HTTP 403 alone does not establish whether a protection rule exists.

Codex must then verify enforcement, rather than accepting a saved guide as
proof: read applicable active rules where permitted, obtain the owner-authorized
protection read-back if administration access is unavailable, and confirm
`gh pr checks 7 --required` returns a **nonempty** set containing the actual
successful `lint-and-test` check. A missing/inaccessible read-back remains an
unverified guard. Verify no bypass applies to the merging actor.

Recheck PR/base/head SHA, fresh mergeability, all required check outcomes and
any required independent approvals. Mark the existing PR ready only when its
remaining gates pass. Use squash merge with the expected exact head; never use
`--admin`, direct main pushes, or a zero-check fallback. If main/head changed,
review the changed diff and rerun affected validation first.

After legitimate merge, back up the Explorer head and reconcile only its
downstream changes from incorporated anchor `195a3ef` onto updated main. Retarget
the existing PR #8, rerun source/tests/CI, and keep it unmerged pending product
acceptance and authorization. Do not create duplicate PRs or deploy.
