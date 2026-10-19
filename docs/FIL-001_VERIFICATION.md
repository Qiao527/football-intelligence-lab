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

Fresh clone/cache verification is in progress. Hosted Actions results have not
yet been observed. These pending checks are not reported as passed.

## Limitations and next task

Linux x86_64 / CPython 3.11.14 is the only locally verified platform. A defined
Actions workflow does not prove a hosted run; remote results must be checked
after push. No credentials, external services or football data are required for
these tests. Public package registries and Python distribution downloads are
needed on an uncached machine.

The foundation supports beginning FIL-002 after review. FIL-002 must separately
establish allowed source access, license/attribution, immutable raw files and
real provenance; no football gate has passed. No merge or deployment performed.
