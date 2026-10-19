# FIL-004 — period-aware clock verification

## Stack and merge observations

Branch: `feat/fil-004-period-aware-clock`.
Development parent: `feat/fil-003-event-normalization` at
`3d81faf9ae66f1b2075a1aba5b877baefa42e418`, dependency PR #4, itself stacked on
FIL-002 PR #3 (`5a18a4e1a417cfbf33941796552b25c9c8ab0c36`). The owner reports
#4 exists and hosted CI passed. Native Git confirms both PR head refs and parent
branch heads; this does not independently observe hosted CI. Parent local Ruff
and all 97 tests passed (exit 0).

Initial and subsequent fetches of main and both parent branches found main
still at `cde6c66` (FIL-001), with unchanged parent heads. Merge-base with the
FIL-003 parent is its exact recorded SHA. Thus #3/#4 have not reached the fetched
main and no reconciliation/rebase was needed. Intended FIL-004 PR base is FIL-003,
not main; its diff includes only FIL-004 changes.

CODEX_WORKFLOW.md records the squash-safe procedure once both parents merge:
preserve the downstream head, identify its latest validated parent anchor,
transplant only commits after that anchor onto updated main, resolve/verify,
regenerate evidence with actual new SHAs and retarget the PR. Do not merge old
feature history or replay squashed parent commits. Published feature rewrites
need expected-head protection; never rewrite/merge main without approval.
These instructions do not claim reconciliation happened or parents were merged.

## Implementation and scope

Tested implementation commit: `a377b77d0c672582210d915adca700062ba78b10`.
Later commits only finalize documentation and delivery evidence.

- `fil.time.clock`: exact integer-ms parsing, display formatting, frozen
  PeriodInfo/PeriodRange, observed/estimated offsets, domain scopes, half-open
  selection, partitions and chronological-to-period conversion.
- `fil.time.artifacts` and `python -m fil.time`: immutable, fully verified
  enriched Parquet/QA/manifests and offline build/verify CLI.
- Added 13 clock/provenance columns, preserving all 53 canonical columns/types/
  values, original source order, IDs, timestamps and source JSON. See MATCH_CLOCK.md.
- No dependencies, source policy/rights, canonical schema/adapter, ingestion,
  original reference documents or LICENSE changed. No score, xG/xT, player,
  network, dashboard, AI, video or wall-clock calculation implemented.
- DATA-TIME has local technical evidence for this fixture; no later analytics
  gate is passed. **DEL-TIME-SCORE is not passed** because score reconciliation
  is FIL-005. FIL-004 is ready for review, not human accepted or merged.

Environment: Linux x86_64, Python 3.11.14, uv 0.12.23, PyArrow 21.0.0,
pytest 8.4.2, Ruff 0.14.0, uv_build 0.9.5. Existing locked transitives are
unchanged. TLS/checksum verification and CI permissions remain unchanged.

## Actual source and clock artifacts

Source fixture: 2018-07-15 FIFA World Cup Final, France–Croatia, match 8658.
Upstream revision: `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`.
Raw event SHA-256: `a9aa72c042153fa351c3591ee11e7fba95b0c8841c4489da4aa6809de1edbdf5`.
Acquisition manifest SHA-256:
`f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c`.
Canonical manifest SHA-256:
`3a6120111756130ce1db76b3e320e67768ddd688d036c22e2cb1718cbd79d003`.
Canonical Parquet SHA-256:
`81154e82b1108231a1a96da9fa071a6880bddbf4b6a02d826a384fcef6b4eaf5`.
All were verified through the FIL-002/FIL-003 chain before clock generation.
The canonical artifact retains its original normalizer implementation SHA;
clock code provenance is separate, not substituted into upstream records.

Actual local clock bundle (ignored):

```text
data/interim/clocks/match_id=8658/3a6120111756130ce1db76b3e320e67768ddd688d036c22e2cb1718cbd79d003/fil-period-clock-1/a377b77d0c672582210d915adca700062ba78b10/
  clock_events.parquet
  quality.json
  manifest.json
```

Generated UTC: `2026-10-19T17:45:13.441677+00:00`.
Clock Parquet: 469,210 bytes, SHA-256
`194c72c5a2bc56ae434e6cd2d9fe85b9441f51ba6984d035daa0bf4905455bb3`.
Quality JSON: 1,595 bytes, SHA-256
`3557040504a929c558083d40b49dbed4ccca1e71a34ffcadeb37c28eec7dde64`.
Clock manifest SHA-256: `cf1ffbb424bda478107665abddf152bc66fb242ab4166657dc3abfc1daacc798`.
No raw or derived provider records are committed or redistributed.

## Real match observations

| Source period | Rows | Observed duration ms | Match-play offset ms | End/offset estimated | Last display |
| --- | --- | --- | --- | --- | --- |
| 1 | 1332 | 2906080 | 0 | false / false | 45+3:26.080 |
| 2 | 1646 | 3003760 | 2906080 | false / false | 90+5:03.760 |

The source contains two matching Half Start and two matching Half End records
per period; all eight marker records are retained. Markers agree and period
warnings are empty. No timestamps regress within provider order. Match-play
axis endpoint is **5,909,840 ms** (event-phase elapsed time, excluding real
half-time breaks); this is not a physical wall-clock duration or video code.
H1 terminal markers and H2 start markers share a scalar boundary as documented;
period-specific H2 selection excludes H1 events, without invented epsilon time.

All **2,978** canonical events remain present with unique original IDs.
Regular/match-play scopes each contain 2,978 records; extra/shootout scopes each
contain 0. This fixture does not test real extra time or shootouts; TEST-ONLY
fixtures cover those cases without claiming additional real observations.

15-minute period-relative bin counts, with only the last bin terminal-inclusive:

- H1: `[575, 359, 293, 105]` = 1,332.
- H2: `[532, 493, 474, 147]` = 1,646.

Independent checks also covered 5- and 10-minute bins; every source ID belongs
exactly once to its period's partition. No missing data was filled with zero,
no event was dropped and no match metric was computed. Period 5 would remain in
stored data with null chronology, excluded from default match-play views.

## Executed checks and exit codes

With the documented writable uv storage settings, all final commands exited 0:

```bash
uv lock --check
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen pytest -q
uv build
uv run --frozen python -m fil.time --help
fil_code_sha=$(git rev-parse HEAD)
uv run --frozen python -m fil.time build \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --pipeline-revision "$fil_code_sha"
```

The actual SHA used for the recorded artifact is the implementation commit
above, not a later documentation commit. New commits get separate destinations;
old artifacts are never relabeled or overwritten.

All **180 tests passed, 0 skipped**: 97 parent cases plus 83 clock cases. Tests
cover exact fractional parsing and malformed/negative values; H1 44:59.9,
45:00, 45+2; H2 opening, 89:59 and 90+5; both extra-time periods/stoppage;
ordinary penalty retention versus period-5 exclusion; missing start/end,
propagated estimates, duplicate/conflicting markers, events beyond Half End,
time/period regressions, missing periods, zero-duration shootout, timestamp ties,
terminal-point ranges, empty windows, half-open bin partitions, overlapping/
invalid filters, continuous-to-period equivalence, source/schema preservation,
artifact corruption, idempotence, cleanup and immutable input protection.
TEST-ONLY events are clearly labeled and never presented as match observations.
Unit tests use no live source acquisition.

Independent real-data checks used `decimal.Decimal` and raw timestamp strings
rather than the clock parser to recompute every event's milliseconds and each
period's source Half End duration/offset. They checked all 2,978 IDs/timestamps,
source minute/second fields, milliseconds/float views, estimate flags and
source JSON objects; all matched. Selecting the 53 canonical columns restored
the exact parent table, schema and values. Each row binds the actual canonical
manifest digest, preserving source ID/array-offset/raw-manifest traceability.

For real-data filtering, independently computed scalar half-open interval masks
matched converted period-range selections, including shared-boundary instants
and explicit final endpoints. Whole-period 5/10/15-minute partitions covered
all IDs exactly once. No default shootout or extra-time data was invented.

A repeated build verified and reused every output byte/mtime. A separate output
root produced byte-identical clock Parquet and quality JSON; manifests may have
different creation times. Snapshot hashes and mtimes of every raw/canonical input
file before/after the entire build/verify process matched. These independent
scripts and artifact verification each exited 0.

## Fresh checkout and CI-equivalent verification

A new clone at `/tmp/fil-004-verify.t2noAR/checkout` was created from the tested
implementation using `git clone --no-local --branch feat/fil-004-period-aware-clock
/workspace/football-intelligence-lab <new-path>` (exit 0), with no environment and
an empty dependency cache. The existing pinned interpreter was reused; this
was not a fresh OS image. All commands below exited 0:

```bash
uv lock --check
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen pytest -q
UV_PROJECT_ENVIRONMENT=.venv-wheel uv sync --frozen --no-editable
UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable ruff check .
UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable pytest -q
UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable python -m fil.ingestion.normalize --help
UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable python -m fil.time --help
uv build
```

Both installations passed lint and 180 tests. Existing verified raw/canonical
bundles were copied locally into ignored directories without changing their
bytes/manifests; no data was transmitted to third parties. The regular-installed
clock reverified the entire source chain and reproduced all 2,978 enriched rows,
clock Parquet bytes and quality JSON bytes exactly. Git status remained clean.
This proves repeatability for identical inputs/provenance on the tested platform,
not bit-identical output on untested systems or newly acquired manifests.

## Self-review and corrections

Initial Ruff findings (exit 1) were line length, test semicolons and import
ordering; formatting/fixes preserved the configured rules. All first 172 tests
passed. Eight additional self-review cases raised the final count to 180;
none were skipped, disabled or bypassed. No behavioral test failures remain.

Self-review added explicit boolean argument validation, ambiguous end-marker
failure, mixed-source/match rejection, canonical mutation detection and failed
publication cleanup. Clock construction now parses the exact canonical byte
buffer whose digest was checked, avoiding a separate unbound file reread.
Source/canonical schemas, event IDs and timestamps were not changed to make
clock tests pass. Every original provider and canonical artifact stays intact.

## Limitations and gates

Missing ends yield explicitly qualified observational estimates, never precise
physical durations; downstream offsets inherit uncertainty. Inconsistent markers
and absent intermediate periods fail closed. Stored scalar times are not unique
event keys. No real extra-time/shootout fixture, physical-break duration,
video synchronization or other platform has been verified.

DATA-TIME technical checks pass for this source. **DEL-TIME-SCORE and all later
analytics gates remain unpassed**. FIL-004 is implemented/locally verified, not
human accepted. Hosted child CI and independent/human review must be recorded
separately. Source rights remain local noncommercial research only, with no
redistribution, commercial-use, deployment or merge authorization.


## Hosted validation and PR delivery

`git push -u origin feat/fil-004-period-aware-clock` succeeded (exit 0).
`gh pr create --repo Qiao527/football-intelligence-lab --base feat/fil-003-event-normalization --head feat/fil-004-period-aware-clock --title "feat: implement period-aware match clocks and filters (FIL-004)" --body-file docs/FIL-004_PR.md`
failed (exit 1): `Post "https://api.github.com/graphql": Forbidden`.
`gh run list --repo Qiao527/football-intelligence-lab --branch feat/fil-004-period-aware-clock --limit 5 --json databaseId,headSha,status,conclusion,url`
also failed (exit 1), API Forbidden. No FIL-004 hosted PASS or PR creation is
claimed. This is a delivery limitation, not a reason to discard verified work.
The parent's hosted PASS is explicitly attributed to the owner.

Prepared description: [FIL-004_PR.md](FIL-004_PR.md).
Exact [stacked PR creation link](https://github.com/Qiao527/football-intelligence-lab/compare/feat/fil-003-event-normalization...feat/fil-004-period-aware-clock?expand=1)
selects base FIL-003 and head FIL-004. A maintainer can create the PR/inspect
Actions there, or provide working API access for those operations. No broader
permissions or credentials were requested/changed.

The final main/parent fetch still showed main `cde6c66` and unchanged parent
heads, so no rebase/history rewrite was needed. Conditional squash-safe
reconciliation is documented for when both parents merge. No acceptance,
merge, deployment or rights expansion is claimed.

Final package inspection (exit 0) confirmed both wheel and source distribution
contain clock implementation but no raw/interim provider records/Parquet files.
Snapshot checks again confirmed all raw/canonical bytes and mtimes unchanged.
`git diff --exit-code <FIL-003-parent> -- pyproject.toml uv.lock LICENSE src/fil/schema.py src/fil/ingestion docs/SOURCE_POLICY.md <both-original-reference-documents>`
passed (exit 0); `git diff --check` passed. Subsequent commits finalize only
workflow/status/report/PR documentation; the tested clock implementation is
unchanged. No behavioral assertions or checks were weakened.
