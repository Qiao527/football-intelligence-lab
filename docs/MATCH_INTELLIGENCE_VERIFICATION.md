# Match Intelligence MVP — actual verification

Verified locally on 2026-10-26, Linux x86_64, Python 3.11.14, uv 0.12.23. The sprint starts
at PR #22 / `d5eb2189f90777149dbb0501f6b2e22bbd7fe0a1` and keeps the historical stack intact.
Implemented/locally verified, hosted CI, human acceptance and main integration are separate states.

## Completed product and checks

| Check | Actual result |
|---|---|
| Frozen manifest/lock agreement | PASS; no dependency or lock changes |
| Ruff | PASS |
| Full editable suite | **588 passed**, 9.11s; no failures/skips |
| Fresh regular installation, reinstalled after final code fix | **588 passed**, 9.25s; no failures/skips |
| Wheel + source distribution | PASS; all six intelligence modules packaged, no provider payloads |
| Installed isolated CLI outside checkout | PASS, resolves from `/tmp/fil-mvp-wheel/.../site-packages` |
| Separate original-record verification | **64 matches / 227,825 events**, all preserved; 320 full/filter selections reconciled |
| France–Croatia reference | 2,978 events, official 4–2; unchanged original source xG sum 2.5782512977 |
| Real Chromium product flow | Three fictional fixtures and real matches 8658 / 7570 PASS |
| Desktop/mobile | 1440px / 390px; rendered charts, original JSON, empty states, filters, reset, no page overflow/clipping |
| Browser page errors / external requests | **0 / 0** in the scripted flow |
| Historical evidence preservation | **2,001** pre-existing local data/artifact files retain identical SHA-256 |
| Legacy engines, policies and rights | Unchanged against the parent; all 557 previous tests retained |
| Human product/football acceptance | **Pending**, not replaced by browser checks |

The separate verifier uses raw JSON and Fraction arithmetic, distinct grouping and scoring logic.
It checks every selected Shot ID, native membership, full context sequence and arithmetic complement,
own-goal reconciliation, filtering, repeatability and no raw-input mutation. These are technical
correctness checks, not independent human judgments or confirmation on untouched matches.

The new regression cases cover dynamic input changes; duplicate IDs, order, team, score and invalid
weights; explicit-null pass outcomes; unknown membership/phase; missing weights; no-Shot selection;
shootouts/own goals; stale UI state; blocked local libraries; cache content and bundle-membership
changes; local export restrictions; and demo launcher isolation from inherited research settings.

Real defects fixed during review: unsupported Plotly sizing arguments surfaced a deprecation warning;
mobile branding needed clearance below the framework header; added source members could evade a
previous cache fingerprint. Four membership regressions and the warning/UI checks now cover these.
Early harness failures (expected count, hidden radio input, virtualized match search, resize timing,
routing callback) were corrected; no failing final check is skipped. Initial package commands needed
sandbox network access for the already-pinned build backend and writable uv Python storage.

## Reproduce local validation

```bash
uv lock --check
uv run --frozen ruff check .
uv run --frozen pytest -q
uv build
UV_PROJECT_ENVIRONMENT=/tmp/fil-mvp-wheel uv sync --frozen --no-editable \
  --reinstall-package football-intelligence-lab
UV_PROJECT_ENVIRONMENT=/tmp/fil-mvp-wheel uv run --frozen --no-editable pytest -q
```

On this managed cloud host, set writable tool storage first:

```bash
export UV_CACHE_DIR=/tmp/fil-uv-cache
export UV_PYTHON_INSTALL_DIR=/workspace/.local/share/uv/python
```

Browser checks need the frozen optional Playwright group and an installed Chromium. No remote
browser/model service is used. These checks do not install Chromium automatically:

```bash
uv sync --frozen --group browser
uv run --frozen --group browser python -m fil.intelligence run --port 8524
# Separate terminal:
uv run --frozen --group browser python scripts/check_intelligence_browser.py \
  --url http://127.0.0.1:8524
```

For optional real-data UI checks, launch with `--local-library` as documented in
[MATCH_INTELLIGENCE_LOCAL.md](MATCH_INTELLIGENCE_LOCAL.md), and pass the same library path to the
browser checker. Explicit screenshots are captured only on fictional fixtures, before real-data
checks. The default detailed receipts stay ignored under `data/interim/intelligence/`.

## Browser performance: actual final samples

The retained [performance-only evidence](benchmarks/match-intelligence-mvp.json) contains every sample,
variability, method and implementation hash. Ten fresh server/Chromium repetitions per workload,
with two verified filter interactions each. **20 openings and 40 interactions** overall.

| Workload | Opening median (s) | Opening min–max | Opening SD / p90 | Filter median (s) | Filter max | Filters ≤1s |
|---|---:|---|---|---:|---:|---:|
| Fictional demo | 5.345 | 5.265–5.796 | 0.164 / 5.556 | 0.492 | 0.600 | 20/20 |
| Local research reference | 6.083 | 5.487–7.582 | 0.671 / 7.388 | 0.533 | 1.079 | 19/20 |

Opening starts before launching Python and Chromium and ends after navigation, analysis, both
Plotly charts' real initialization, idle state and two animation frames. It includes browser
startup and, for local research, choosing the data source/match. Analysis-click timing starts
at the Run button. Filter timing waits for the expected changed Shot count, idle state and rendered
charts. Server-ready and landing stages are separately retained. These are process-cold runs with
warm OS/package caches on a shared cloud host, not machine-cold installs or end-user laptop guarantees.

**The ≤3s opening target is not met.** Typical interaction latency and tail samples are reported
separately; no universal ≤1s claim. These two workload series are sequential, **not an interleaved
paired parent/candidate experiment**. No legacy speedup, causal optimization effect or comparable
before/after percentage is claimed. Preliminary runs and failed harness logs remain local; changing
render readiness and source checks prevents treating them as a controlled comparison.

A server profile identified repeated native-context scans and unnecessary single-file dataset
initialization. The implementation indexes context once and reads a specific Parquet file directly,
while retaining full canonical/raw equality. A profile-guided implementation change is not itself
proof of a user-visible speedup. Browser startup, framework transport and first chart initialization
remain part of the observed opening cost. The UI's Python-execution footer explicitly excludes those
costs and must never be used as the cold-start number.

The existing four-view Explorer/Tactical/Possession/Player application was not re-benchmarked or
claimed fixed. Its [historical paired stabilization measurements](STABILIZATION_REPORT.md) and
startup/long-tail limitations remain visible and are a different workload.

Reproduce the two workloads from the repository root, sequentially:

```bash
uv run --frozen --group browser python scripts/benchmark_intelligence.py \
  --repetitions 10 --base-port 8610 \
  --output data/interim/intelligence/benchmark-release-demo.json
uv run --frozen --group browser python scripts/benchmark_intelligence.py \
  --repetitions 10 --base-port 8630 \
  --library data/interim/intelligence/library.json \
  --output data/interim/intelligence/benchmark-release-local.json
```

## Integration, rights and remaining acceptance

The bounded product branch is reviewable against PR #22's exact parent. Historical PR heads,
bases and draft states remain unchanged/unmerged; this is not a main-ready integration or deployment.
The MVP CLI is added to the existing `lint-and-test` regular-install check. Hosted MVP status is
reported separately on the product PR's Checks/current commit; no parent result is substituted.

No source acquisition, model fitting, external AI upload, provider-data export, rights expansion,
merge or deployment. Only self-authored synthetic screenshots are included in Git. Public hosting
and historical integration require owner authorization and their actual gates. Remaining product
acceptance items: cold opening, interaction tails on intended hardware, first-time usability and
independent analyst usefulness. No AI-discovery, expert-level performance, causal or ability claim.
