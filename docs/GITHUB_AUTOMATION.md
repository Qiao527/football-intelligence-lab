# Supported GitHub delivery and one-time setup

Git read/push is authorized through the injected platform Git proxy. REST/GraphQL
is a different destination and authorization surface. A supported read-only
repository API request returned Forbidden; no token/credential values were read
or changed. Current environment config has github.com/Git proxy destinations but
omits api.github.com. This is consistent with egress denial, not proof that
repository/API authentication is absent or that an App lacks permission.

Saved a draft adding only custom host api.github.com, preserving the preset
allowlist, plus tested install/start instructions. Draft save reports
requires_publish=true. The owner must review/save and publish in Environment
settings for activation; saving does not itself apply network policy or prove
API access. After activation, test the supported API once. If still denied,
authorize the platform GitHub connection/App for this repository's PR read/write,
checks/Actions read and contents write for the specifically approved integration.
Do not request a raw PAT in chat, extract proxy credentials, rewrite the proxy,
or grant unrelated repositories/organization administration.

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
