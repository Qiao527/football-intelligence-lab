# FIL-002 — StatsBomb acquisition, provenance and integrity

## Scope and changed files

Start from merged FIL-001 PR #2 (`main` at `cde6c66`). Add a Python standard-library
acquisition/offline verification CLI in `src/fil/ingestion/statsbomb.py`, the
packaged audited `statsbomb_source.json` pin registry and package initializer.
Add 37 acquisition test cases, ignore `data/raw/`, extend existing CI push
coverage to feature branches, and update README/STATUS. Add source policy,
manifest specification and actual verification evidence documents.

No runtime/development dependencies added; existing lockfile, MIT LICENSE and
original reference documents remain unchanged. No normalization, xG/xT, score
calculation, network, dashboard, scraping or AI agent is implemented.

## Source and rights

Pinned official repository: `https://github.com/hudl/open-data` at
`4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`.
Source records confirm match 8658, FIFA World Cup 2018 Final, 2018-07-15,
France (771) vs Croatia (785). Lineups are included; no 360/tracking claim.
README and LICENSE.pdf were read before event acquisition. The license limits
use to research, restricts redistribution/commercial use, requires provider
branding for publications, and asks owner registration before access.

All six original files and the actual manifest remain local under ignored
`data/raw/statsbomb/8658/<upstream-revision>/`. No raw dataset or provider terms
are committed or packaged. **DATA-SOURCE and DEL-SOURCE remain PENDING** until
owner registration/terms compliance is confirmed. Integrity PASS does not grant
redistribution permission. See `docs/SOURCE_POLICY.md`.

## Setup and reproduction

Use Python 3.11.14 and uv 0.12.23, with writable uv storage configured per README:

```bash
uv sync --frozen
uv run --frozen python -m fil.ingestion.statsbomb acquire \
  --pipeline-revision "$(git rev-parse HEAD)"
uv run --frozen python -m fil.ingestion.statsbomb verify \
  data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb
uv run --frozen ruff check .
uv run --frozen pytest -q
```

## Actual evidence

- Real event file: 2,978 records and unique IDs, zero duplicates; SHA-256
  `a9aa72c042153fa351c3591ee11e7fba95b0c8841c4489da4aa6809de1edbdf5`.
- Six file hashes/sizes, acquisition timestamp, pipeline SHA, source identity,
  period/null counts and three independent ID reverse lookups are recorded in
  `docs/FIL-002_VERIFICATION.md`; the actual manifest is local and ignored.
- Final frozen sync, Ruff, pytest (41 passed, 0 skipped), source/wheel build and
  independent byte/hash verification all exit 0. Unit tests forbid live network.
- A fresh local clone with empty dependency cache and a regular installation
  independently reacquired identical provider bytes/QC. Offline repetition
  preserved bytes and modification times for every file and the manifest.
- Both release artifacts exclude provider data. Existing lock/reference/license
  diff checks pass. No dataset is staged or tracked.
- Initial lint line-length findings were corrected. An initial acquisition with
  a wrongly supplied FIL SHA was preserved in ignored quarantine and excluded
  from evidence; canonical acquisition uses the actual Git SHA. See report.

PR creation and hosted CI observation are currently blocked by GitHub API
Forbidden responses. The branch and this description are reviewable, but no PR
was created by the CLI and no hosted CI PASS is claimed.

## Limitations and review

The caller-supplied pipeline SHA must match the clean code checkout; it is not
a digital signature. Cache reuse verifies local bytes without contacting the
source. Changed/corrupt inputs fail closed; no automatic repair or overwrite.
Full schema/enum audit and normalization remain FIL-003 work. Linux x86_64 /
Python 3.11.14 is locally verified. Hosted Actions outcome must be inspected
separately when accessible; no hosted PASS is inferred from local results.

Review source rights/registration and the provenance evidence before closing
source gates or beginning dependent work. No merge or deployment performed.
