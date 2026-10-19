# FIL-001 — Reproducible Python engineering foundation

## Change summary

Start from merged bootstrap PR #1 (`main` at `f6ee527`). Add a Python 3.11.14
src-layout package with no runtime dependencies, uv 0.12.23 tooling, a committed
`uv.lock`, Ruff and pytest configuration, and four installation/metadata smoke
tests. Add read-only-permission GitHub Actions CI with pinned action commits
for lock consistency, frozen install, lint, tests, build and a regular install.

Files: `.python-version`, `pyproject.toml`, `uv.lock`, `.gitignore`,
`src/fil/__init__.py`, `tests/test_foundation.py`, `.github/workflows/ci.yml`,
README, STATUS, gate mapping and verification documents.

## Setup

With uv 0.12.23 installed, run from the checkout:

```bash
uv python install
uv lock --check
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen pytest -q
```

README documents writable uv storage overrides for this cloud machine and the
separate `UV_PROJECT_ENVIRONMENT=.venv-wheel` regular-install check.

## Verification

- Frozen editable install: exit 0; Ruff: exit 0; pytest: exit 0, 4 passed, 0 skipped.
- Fresh local clone with empty dependency cache: frozen install, lint, all four
  tests and source/wheel builds passed (all exit 0); manifest and lock unchanged.
- A separate non-editable installation passed lint/tests (4 passed, 0 skipped)
  and imports from site-packages in an isolated interpreter.
- First pytest attempt: 3 passed, 1 failed on metadata whitespace; corrected
  the comparison without changing the required Python constraints.
- Dependency versions, commands and failures are in `docs/FIL-001_VERIFICATION.md`.
- Hosted CI observation is blocked: `gh run list` returned Forbidden. No hosted
  PASS is claimed; inspect the Actions result before merge.

## Gate consistency correction

AGENTS.md and handbook §§10.1, 19.1, 25 and 33.2 now distinguish `ENG-FOUNDATION`,
`DEL-*` delivery stages and `DATA-*` validation checks. `docs/GATES.md` maps every
legacy label. All original acceptance/failure requirements remain. FIL-001 no
longer appears to satisfy the source-data G0 gate. Master Reference, LICENSE
and historical bootstrap evidence are unchanged.

## Limitations and FIL-002 readiness

Locally verified only on Linux x86_64 / Python 3.11.14. CI is configured but its
hosted result is unverified due to API access. No v0.2 notebook is in this repo.
No analytics dependencies, fixtures, ingestion, xG/xT, dashboard, scraping or
AI agent were added. FIL-002 can begin after review of this foundation; it must
separately verify permitted source access, license/attribution and real raw-data
provenance. No football delivery/validation gate has passed. Human review and
merge approval remain required; no merge or deployment performed.
