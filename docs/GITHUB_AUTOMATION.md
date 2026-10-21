# Supported GitHub delivery and one-time setup

The published environment now permits api.github.com. Repository REST and PR
GraphQL checks succeed through the inherited platform proxy; PRs #7 and #8
exist and their hosted CI is independently verified. The prior Forbidden
problem is resolved. No credentials or proxy routes were changed.

The remaining integration condition is governance: the private repository's
current plan prevents enforceable branch protection, and PR #7 has no required
checks. Record this once as an owner-level plan decision and continue product
engineering. The exact minimal setup and read-back requirements are in
[MAIN_PROTECTION.md](MAIN_PROTECTION.md). Do not make the repository public,
purchase a plan, bypass guards, or request the same owner action repeatedly.

## Optional repository-scoped Actions path

.github/workflows/approved-integration.yml is prepared, dispatch-only and
NOT activated/hosted-verified here. A maintainer can review/install it on main,
enable Actions to create PRs, configure required protected-main checks/reviews,
then dispatch with the exact reviewed integrate/fil-003-005 SHA. It verifies
frozen lint/test/build/regular install with read-only checkout credentials,
then a separate credentialed job creates/reuses only that integration PR,
rechecks head SHA/mergeability/clean state and nonempty passing required checks,
and invokes gh pr merge --squash --match-head-commit. There is no admin bypass,
main push, arbitrary branch input, deploy, PAT, fork event or future-product
merge grant. No provider data is uploaded to Actions.

GITHUB_TOKEN-created PRs do not trigger new PR workflows. Integration push CI
must already exist for the head (ci.yml includes integrate/**). Missing/pending
checks or required reviews stop delivery; rerun dispatch after they resolve.
Protected main and its required-check configuration are prerequisites. Enabling
this workflow cannot weaken branch protections. This path is optional if the
platform API connection becomes usable. Existing PRs #4/#5 are left intact.

Automatic merging of future product changes is not enabled by this workflow.
Such changes need an explicitly established authorized quality-gated workflow;
this mission does not treat the integration-only grant as blanket approval.
