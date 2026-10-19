# FIL-001 verification

## Scope and design choices

Started from merged PR #1 on `origin/main` at `f6ee527`, after verifying root
AGENTS.md, both reference documents, bootstrap audit and FIL-001 task brief.
Implementation branch: `feat/fil-001-engineering-foundation`.

Python 3.11.14 and uv 0.12.23 are pinned. The only direct development dependencies
are pytest 8.4.2 and Ruff 0.14.0; no runtime dependencies. The isolated build
backend is pinned separately to uv_build 0.9.5. `uv.lock` records the development
dependency graph and published artifact hashes. No TLS or checksum checks were
disabled. Source and wheel packages build successfully.

Intentional departures from handbook examples: uv replaces the sample pip/venv
workflow, only engineering tools are installed, and lock-based checks replace
the illustrative unpinned CI installation. No fixture compatibility claim is
made: FIL-002 has not downloaded data. [GATES.md](GATES.md) documents every
reference consistency correction; the Master Reference is unchanged.

## Engineering file inventory

```text
.python-version                    Python 3.11.14 pin
pyproject.toml / uv.lock            package, build, dev tools and locked artifacts
.gitignore                         local environments/build/cache outputs
src/fil/__init__.py                 importable foundation only
tests/test_foundation.py            four smoke tests
.github/workflows/ci.yml            lock/lint/test/build/regular-install checks
docs/GATES.md                      namespace mapping and reference corrections
docs/FIL-001_VERIFICATION.md        actual verification evidence
docs/FIL-001_PR.md                  prepared PR description
README.md / docs/STATUS.md          setup commands and verified current status
```

Existing scoped AGENTS files and project skills remain intact. No source data,
metric dictionary, fixtures or analytical implementations were created.

## Tests

Four tests verify: import from an isolated subprocess outside the repository;
installed distribution metadata matches project metadata and license; there
are no runtime requirements; and the running interpreter is Python 3.11.
There is no pytest source-path injection. Both editable and regular installs
are checked so an accidental namespace/source-directory import cannot replace
an installed-package check. No analytics tests/results are claimed.

## Current-instance results

Commands are from the repository root with writable uv storage configured as
documented in README.md. Each final command below exited 0.

| Command | Result |
| --- | --- |
| `uv python install` | Python 3.11.14 available; bin directory configured outside read-only home. |
| `uv lock` | Eight locked packages, including project and Windows-only colorama. |
| `uv lock --check` | Manifest agrees with lockfile. |
| `uv sync --frozen` | Editable project plus six dev/transitive packages installed. |
| `uv run --frozen ruff check .` | All checks passed. |
| `uv run --frozen pytest -q` | 4 passed, 0 skipped. |
| `UV_PROJECT_ENVIRONMENT=.venv-wheel uv sync --frozen --no-editable` | New regular installation created. |
| `UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable ruff check .` | All checks passed. |
| `UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable pytest -q` | 4 passed, 0 skipped. |
| `uv build` | Source distribution and wheel generated in ignored `dist/`. |
| `uv run --frozen python -I -c 'import fil; print(fil.__file__)'` | Installed editable package resolves to `src/fil/__init__.py`. |

Installed versions: football-intelligence-lab 0.1.0; pytest 8.4.2; ruff 0.14.0;
iniconfig 2.3.1; packaging 26.3; pluggy 1.7.0; pygments 2.21.0.
Windows-only colorama 0.4.6 is locked but not installed on this Linux host.

Initial failures and corrections:

- `uv python list --only-installed` exited 2 because the default home cache was
  read-only. Writable UV_CACHE_DIR/PYTHON_INSTALL_DIR/BIN_DIR overrides fix the
  environment. Initial Python installation completed with a link warning;
  subsequent `uv python install` with BIN_DIR succeeded.
- First pytest run exited 1: three passed, one metadata assertion failed on
  backend-inserted whitespace in Requires-Python. The test now compares
  comma-separated constraints ignoring whitespace, preserving all constraints.
  Subsequent editable and regular runs each pass all four tests.

## Fresh-checkout and hosted verification

A new local clone was created with
`git clone --no-local --branch feat/fil-001-engineering-foundation /workspace/football-intelligence-lab /tmp/fil-001-verify.wM5hpo/checkout`
(exit 0), at implementation commit
`7cedbd6780858a17f3bc756481e73a06011d2542`. The clone started with no project
environment and an empty dependency cache at `/tmp/fil-001-verify.wM5hpo/cache`.
The previously installed pinned Python interpreter was reused; this was not a
new operating-system image. Subsequent changes only finalize review evidence.

All commands below exited 0 from that fresh checkout, with the same writable
Python storage overrides as README.md and the new UV_CACHE_DIR:

| Command | Result |
| --- | --- |
| `uv --version` / `uv python install` | uv 0.12.23 / Python 3.11.14. |
| `uv lock --check` | Manifest and committed lock agree. |
| `uv sync --frozen` | Cold-cache editable install succeeds. |
| `uv run --frozen ruff check .` | All checks passed. |
| `uv run --frozen pytest -q` | 4 passed, 0 skipped. |
| `uv build` | Source distribution and wheel built. |
| `UV_PROJECT_ENVIRONMENT=.venv-wheel uv sync --frozen --no-editable` | Second empty environment, regular package installed. |
| `UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable ruff check .` | All checks passed. |
| `UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable pytest -q` | 4 passed, 0 skipped. |
| `UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable python -I -c 'import fil; from pathlib import Path; p=Path(fil.__file__); assert "site-packages" in p.parts; print(p)'` | Import resolves inside the regular environment's site-packages. |
| `sha256sum pyproject.toml uv.lock` before/after | Both files unchanged. |
| `git status --porcelain` | Empty; checkout remains clean after checks. |

Manifest SHA-256: `c5299cb30490f5aede59c56e7f7919a4fe47fa6db0c2a4f5ec040598739fa2e4`.
Lock SHA-256: `81c96366c239ca177a863ba4f11f480d35ec99b0fc96b626398c6900028d45d5`.

Action references were verified with `git ls-remote` (exit 0) against official
repositories: checkout v4.2.2 and setup-uv v6.0.1 match the workflow's pinned
commit SHAs. Official uv tag 0.12.23 and backend tag 0.9.5 exist (exit 0).
`git diff --exit-code origin/main -- LICENSE docs/Football_Intelligence_Lab_Master_Reference.md`
and `git diff --check` passed (exit 0).

The branch push succeeded (exit 0). After push,
`gh run list --repo Qiao527/football-intelligence-lab --branch feat/fil-001-engineering-foundation --limit 5 --json databaseId,headSha,status,conclusion,url`
failed (exit 1): GitHub API returned Forbidden. The repository metadata API
request also returned Forbidden (exit 1). Hosted Actions results are **blocked
from observation**, not reported as passed or failed. The workflow runs on
branch pushes, PRs and manual dispatch; the user should review its hosted
lint-and-test result before merge.

## Limitations and next task

Linux x86_64 / CPython 3.11.14 is the only locally verified platform. A defined
Actions workflow does not prove a hosted run; remote results must be checked
after push. No credentials, external services or football data are required for
these tests. Public package registries and Python distribution downloads are
needed on an uncached machine.

The foundation supports beginning FIL-002 after review. FIL-002 must separately
establish allowed source access, license/attribution, immutable raw files and
real provenance; no football gate has passed. No merge or deployment performed.


## PR delivery limitation

`gh pr create --repo Qiao527/football-intelligence-lab --base main --head feat/fil-001-engineering-foundation --title "feat: establish reproducible Python engineering foundation (FIL-001)" --body-file docs/FIL-001_PR.md`
failed (exit 1): `Post "https://api.github.com/graphql": Forbidden`.
The pushed branch and [prepared body](FIL-001_PR.md) are reviewable; **no PR was
created by this command**. GitHub supplied this
[PR creation link](https://github.com/Qiao527/football-intelligence-lab/pull/new/feat/fil-001-engineering-foundation).
A maintainer can create the PR with that body and inspect the hosted workflow,
or provide working GitHub API access for those operations. No credential values
were requested, printed or changed, and no permissions were broadened.
