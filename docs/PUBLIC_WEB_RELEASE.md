# Public full-stack web release

Implemented: dependency-free responsive HTML/CSS/JS frontend, Python HTTP API, three fictional
match choices, real-time computation, shared filters, original JSON evidence, comparison actions,
complete conventional baseline and explicit scientific limits. Existing Streamlit/local research
mode is unchanged. Public endpoints refuse real match IDs, arbitrary parameters and uploads.

Validation: 590 tests pass; local Chromium verifies API→report→evidence→baseline, match-change
invalidation, no-Shot abstention and 390px layout with no JavaScript errors. The exact allowlisted
bundle runs in isolation without the checkout. It contains no provider records or credentials.
The new public workload has not yet received the 20-run performance evaluation used by the older
Streamlit product; do not transfer those timing claims to this web frontend.

## Current release blocker

Vercel production deployment was rejected by automatic approval. The reviewed dependency closure
includes private provider ingestion and research source modules as transitive dependencies of the
existing scoring engine. The reviewer did not accept broad external code sharing as authorized by
the synthetic-demo request. No deployment was performed, no URL is claimed, and no workaround was
attempted. Exact target, 45 paths, sizes and hashes: `PUBLIC_WEB_RELEASE_MANIFEST.json`.

Owner decision: approve external sharing of this exact code bundle with Vercel, or require a
smaller independently reviewed public computation package. No repository visibility change,
historical merge, data-rights expansion or paid service purchase is included in that decision.

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
