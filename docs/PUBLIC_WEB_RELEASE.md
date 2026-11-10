# Public full-stack web release

Implemented: dependency-free responsive HTML/CSS/JS frontend, Python HTTP API, three fictional
match choices, real-time computation, shared filters, original JSON evidence, comparison actions,
complete conventional baseline and explicit scientific limits. Existing Streamlit/local research
mode is unchanged. Public endpoints refuse real match IDs, arbitrary parameters and uploads.

Validation: 691 tests pass; local Chromium verifies API→report→evidence→baseline, match-change
invalidation, no-Shot abstention and 390px layout with no JavaScript errors. The exact allowlisted
bundle runs in isolation without the checkout. It contains no provider records or credentials.
The new public workload has not yet received the 20-run performance evaluation used by the older
Streamlit product; do not transfer those timing claims to this web frontend.

## Earlier release blocker

Vercel production deployment was rejected by automatic approval. The reviewed dependency closure
includes private provider ingestion and research source modules as transitive dependencies of the
existing scoring engine. The reviewer did not accept broad external code sharing as authorized by
the synthetic-demo request. That broader bundle was not deployed and no workaround was attempted.
Exact target, 45 paths, sizes and hashes: `PUBLIC_WEB_RELEASE_MANIFEST.json`. A later, separately
authorized deployment of the smaller 26-file package is recorded below.

Owner decision: approve external sharing of this exact code bundle with Vercel, or require a
smaller independently reviewed public computation package. No repository visibility change,
historical merge, data-rights expansion or paid service purchase is included in that decision.

## Serverless routing

The five `web/api/*.py` entrypoints previously re-exported the shared handler as an import alias
with a relative import. Run as a standalone function module that raises `ImportError: attempted
relative import with no known parent package`, and the file exposes no top-level `handler` class
for the Vercel Python builder to discover. Static HTML therefore loads while `/api/scout` never
becomes a working function. Each entrypoint now defines a `handler` subclass, and `web/vercel.json`
declares a pinned `@vercel/python@28.0.0` build plus a `/api/<route>` → `/api/<route>.py` rewrite
for all five routes, with `@vercel/static-build` serving `public/` after the JavaScript syntax check
in `package.json`. `api/index.py` accepts the `.py`-suffixed rewrite path without widening query
validation, and `GET /api/health` reports the deployed commit from `VERCEL_GIT_COMMIT_SHA` when the
platform provides it.

Verified locally: every entrypoint imports as a standalone module, the packaged bundle serves
`/api/health`, `POST /api/scout.py` with the interface's default request, `/api/scout-fixture` and
`/`, and the full suite passes. **Not verified: any Vercel build or runtime.** No project link, credential
or deployment authorization was available, so no hosted URL is claimed for this repository.

The production domain `fil-match-intelligence.vercel.app` serves a different repository
(`Qiao527/fil-match-intelligence`). It has no Scout Copilot, and `POST /api/scout` returns platform
`404 NOT_FOUND`; it is not this application and is archived; do not use it as evidence for this release. The hashes in `PUBLIC_WEB_RELEASE_MANIFEST.json`
describe the earlier rejected 45-file attempt, not the current 26-file package recorded in
`PUBLIC_ALPHA_MANIFEST.json`.

## Release pipeline

`scripts/verify_public_alpha.py` builds the allowlisted bundle into a fresh directory, compares it
byte-for-byte with the committed manifest, loads every API entrypoint under `python -I -B`, serves
the bundle with an isolated interpreter and exercises `/api/health`, `POST /api/scout` with the
interface's default request, `/api/scout-fixture` and `/`. It re-checks the manifest afterwards so
execution residue cannot ship. The `public-alpha` CI job runs exactly that command.

`.github/workflows/public-alpha-release.yml` is dispatch-only and restricted to `main` with an
exact 40-character reviewed commit. It re-runs lint, tests and the package verification, then
force-updates the generated `release/public-alpha` branch with the 26 bundle files and nothing
else. It has no deploy step, no repository secret and no write access outside that job.

Owner steps after review and merge:

1. Create the hosting project from `release/public-alpha` (framework Other, no environment
   variables, no build overrides: `vercel.json` and `package.json` ship inside the bundle).
2. Record the resulting domain and commit in this document only after acceptance passes.
3. Run acceptance against the public URL:

   ```bash
   uv run --frozen python scripts/check_deployment.py \
     --url https://YOUR-DOMAIN --expect-commit "$(git rev-parse HEAD)" \
     --browser /path/to/chromium
   ```

The pinned builders (`@vercel/python@28.0.0`, `@vercel/static-build@24.0.0`) require
`@vercel/build-utils@15.0.0`. Vercel CLI 65.14.0 installs 15.2.1 and the remote build fails with
npm `ERESOLVE`; Vercel CLI 65.1.0 is the compatible client for this configuration. Build locally
with it and deploy with `--prebuilt`, or deploy remotely with it. Do not bypass peer resolution
with `--force`.

The acceptance script fails when the domain serves a platform 404, returns no candidate evidence,
abstains, omits the discovery control, or reports a commit that differs from the reviewed one.

## Verified synthetic deployment

The owner authorized a deployment of the 26-file synthetic package. It is live at
https://fil-public-alpha.vercel.app (Vercel project `fil-public-alpha`). It serves fictional players
only: no provider records, credentials, uploads or model calls.

Deployed artifact: the bundle produced by `scripts/verify_public_alpha.py` from tree
`266af6e15ca4af400851a503d63876f5e10c4804`, which is the tree of `Qiao527/afanc` commit `aaaa2c7`
(merges of #25 and #26). The committed manifest recorded 26 files and the bundle matched it
byte-for-byte before deployment. The deployment was created with
`npx vercel@65.1.0 deploy --prebuilt --prod`.

Acceptance was executed against the public URL, not locally:

- `GET /` returns 200 and serves the discovery page.
- `GET /api/health` returns 200 `{"status":"ok","mode":"synthetic-only","commit":null}`.
- `POST /api/scout` with the interface's default request returns 200, `source_mode` `synthetic`,
  with candidates Mara Vale and Tess Rowe.
- `GET /api/scout-fixture` returns 200 with `provenance.mode` `synthetic`.
- `scripts/check_scout_copilot_browser.py` PASS at 1440x900 and 390x844, including player profile,
  pitch markers, supporting and contradictory evidence, abstention and the local journey.
- `scripts/check_deployment.py --url https://fil-public-alpha.vercel.app` PASS.

Identity limitation: a CLI deployment carries no Git metadata, so `/api/health` reports
`commit: null` and `--expect-commit` cannot be used. Identity rests on the tree hash and manifest
comparison above, not on a platform-reported commit. Linking the project to `release/public-alpha`
through the Git integration would restore platform-reported identity; that is not configured.

Still unverified: custom domain, hosted performance, the separate `fil-match-intelligence.vercel.app`
application, and any non-synthetic data service. No data rights, repository visibility or paid
service were changed.

## Run the full-stack web application locally

```bash
uv sync --frozen
uv run --frozen python scripts/serve_public_web.py
```

Open http://127.0.0.1:8650. This serves the frontend and the live Python API.

## Reproduce packaging

From the repository root:

```bash
uv run --frozen python scripts/package_public_web.py > /tmp/fil-public-payload.json
uv run --frozen pytest -q
```

The packager starts only at `web/` and the required `src/fil` dependency closure. It does not
traverse `data/`, `.git`, environment files or local research artifacts. Real-match handling is
not exposed by the public API. Public third-party model/API calls and user accounts are absent.

Local Streamlit remains available through the root README. The standalone web assets live in
`web/public`; `web/api/index.py` implements the server boundary. Hosting configuration is
`web/vercel.json`, with the sole runtime dependency pinned in `web/requirements.txt`.
