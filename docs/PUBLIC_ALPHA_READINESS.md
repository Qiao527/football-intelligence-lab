# Public Alpha package — review pending

The package is a 26-file explicit allowlist, recorded with byte sizes and SHA-256 hashes in [PUBLIC_ALPHA_MANIFEST.json](PUBLIC_ALPHA_MANIFEST.json). It contains the fictional frontend, synthetic Scout API, synthetic Match Intelligence API, minimal shared report logic, standard-library-only requirements, the static build descriptor and the project MIT license. It excludes research and ingestion source modules, local data, environment files, credentials and unrelated JSON. The scanner verifies explicit `fil.*` source imports against the allowlist; API entrypoint imports and the complete runtime were checked by executing the package. The allowlist is not a substitute for reviewing changes to the contents of allowed files.

The public score reconciler rejects anything other than the exact self-authored built-in fixtures. Its result matched the existing full reconciler for all three fixtures. The full local research reconciler remains in use for local research. The package uses no third-party runtime dependency; the project code is covered by its included MIT `LICENSE`. The self-authored sample actions are fictional. The pitch displays fictional action positions, not tracking or an interactive temporal replay; the Scout Copilot is explicitly rule-based and has no live model.

## Local verification

- `scripts/package_public_web.py --directory ... --manifest ...`: 26 files; a fresh package matched the committed manifest path set, sizes and SHA-256 hashes. A scan for common secret markers, private source imports and local dataset paths returned no matches; this is not an independent security assessment.
- The package ran on Python 3.11.14 from a separate temporary directory using `python -I`. The server was restricted by macOS Sandbox from reading the private repository; a direct read of the repository's `AGENTS.md` failed with `PermissionError`. The browser test process could read its test scripts; the application server could not read the repository. An initial attempt with the system Python 3.9 failed: Python 3.11 is required.
- Serverless entrypoints: `api/scout.py`, `api/scout-fixture.py`, `api/health.py`, `api/matches.py` and `api/analyze.py` were each executed as standalone top-level modules, the condition that previously raised `ImportError: attempted relative import with no known parent package`. Each exposes a top-level `handler` subclass with `do_GET` and `do_POST`. In the packaged bundle under `python -I`, `/api/health`, `POST /api/scout.py` with the interface's default request, `/api/scout-fixture` and the static index responded; `npm run build` (four `node --check` assertions) passed.
- `scripts/check_scout_copilot_browser.py`: PASS in Chrome at 1440×900 and 390×844, including discovery, rule-based Copilot, candidate, profile, pitch, supporting/contradictory evidence, a contradictory original action, abstention and local analytics.
- `scripts/check_scouting_browser.py`: PASS for discovery, filtering, player evidence, Match Intelligence, and mobile layout against the isolated server.
- `.venv/bin/ruff check .`: PASS; `.venv/bin/pytest -q`: 687 passed. Remote CI and Vercel runtime were not run.

## Independent review and remaining blockers

**PENDING: independent security and authorization review has not been submitted or passed.** This environment exposes no standalone authorization-review submission channel for an unpushed local package; a GitHub PR would first require a push, which is not authorized. The manifest and report are ready for a reviewer through an approved channel. Review the exact file contents and hashes, source boundaries, licenses, runtime and requested destination; a reviewer must make their own decision. Do not treat this self-review as approval.

The previous Vercel production deployment attempt was rejected by automatic approval because the broader bundle contained private research and ingestion source modules. This smaller package has not been submitted to that review, and the prior rejection remains in force for that attempt. No deployment of this review package was performed at that time. Vercel routing/build, production hardening and hosting authorization remained unverified. Later, the owner separately authorized a synthetic-only deployment of the same 26-file package; it passed public acceptance at https://fil-public-alpha.vercel.app. Independent security review is still pending and no provider data is involved. See [PUBLIC_WEB_RELEASE.md](PUBLIC_WEB_RELEASE.md). A complete interactive spatial replay is outside this packaging fix.

The artifact now declares a pinned Python build and a `/api/<route>` → `/api/<route>.py` rewrite for every API route, with a top-level `handler` class in each entrypoint. That configuration was verified locally and then on the hosted runtime recorded above. The production domain `https://fil-match-intelligence.vercel.app` serves a different repository, whose page has no Scout Copilot and whose `POST /api/scout` returns platform `404`; it is not evidence for this package and does not correspond to any commit in this repository.

## Reproduce

```sh
.venv/bin/python scripts/package_public_web.py --directory /path/to/new/empty-bundle --manifest /path/to/manifest.json
```

Compare the manifest with the committed manifest. Run the bundle under Python 3.11 in a temporary environment with private repository access denied, then use the two browser checks above. Never include `data/`, research code or local credentials in the review payload.
