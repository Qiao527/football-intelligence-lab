# FIL-003 — normalization verification and stacked dependency

## Parent, scope and acceptance

- Branch: `feat/fil-003-event-normalization`.
- Parent: `feat/fil-002-data-acquisition` at
  `5a18a4e1a417cfbf33941796552b25c9c8ab0c36` (PR #3).
- The owner explicitly authorized stacked development and reported PR #3's
  hosted CI passed. This is attributed owner evidence, not an observed API run.
- Native Git confirms PR #3 head and parent branch SHA match. A subsequent fetch
  and merge-base check confirm the parent is unchanged and an ancestor; no
  reconciliation was needed. Main need not contain FIL-002 before this work.
- Parent local baseline: Ruff, 41 tests and real-source offline verification
  each exited 0. Source rights remain bounded by SOURCE_POLICY.md and the
  owner's earlier registration/noncommercial-research confirmation.
- Implementation tested at `55f636179da639760de1865f57c4430fdd5c9a4d`;
  subsequent changes only finalize docs/evidence. Compare against the parent,
  not main, to review FIL-003 independently. Intended PR base is the parent.
- Status: implemented and locally verified. DATA-SCHEMA / DEL-SCHEMA technical
  checks pass for this fixture, but **FIL-003 is not human accepted**. Hosted
  validation and maintainer approval remain distinct requirements. No later
  time/spatial/score/metric/UI gate is claimed. FIL-004 is not implemented.

Workflow updates are in AGENTS.md, CODEX_WORKFLOW.md, GATES.md and the PR template.
They allow continuing validated stacked work, require reconciliation on parent
change, retain failed-test and human approval boundaries, and treat API Forbidden
as a delivery limitation. No merge, deployment or rights expansion is authorized.
Original Master Reference, Engineering Handbook and source acquisition code/pins
are unchanged relative to the parent.

## Schema and implementation

[CANONICAL_EVENTS.md](CANONICAL_EVENTS.md) specifies 53 fixed Arrow columns,
nullability, projections and migration rules. Provider-neutral schema and
validation live in `fil.schema`; StatsBomb projections are isolated in
`fil.ingestion.statsbomb_adapter`. CLI/storage/lineage verification live in
`fil.ingestion.normalize`.

One row per original event; original UUID/order/period/timestamp/IDs/coordinates,
nullable attributes and full source-record JSON are preserved. Unknown types
are retained and flagged. No row exclusions, inferred success/default values,
clock reconstruction, metric calculation, xG aggregation or UI work occurred.
Provider `statsbomb_xg` is copied only. Nullable 2D/3D coordinates widen to float64
without scaling/flipping. Full nested attributes remain in semantic source JSON;
raw bytes remain immutable. Time-derived handbook columns are deferred to FIL-004.

PyArrow **21.0.0** is the sole new runtime dependency (Apache licensing, official
PyPI metadata links Apache Arrow; requirement Python >=3.9). It supplies Arrow,
Parquet and bundled compression; no pandas, DuckDB or analytical stacks added.
The pinned version/artifact hashes are in uv.lock. The prior foundation test
that prohibited all runtime dependencies now permits exactly this scoped pin;
installation metadata is still verified. No tests were skipped/disabled.

Environment: Linux x86_64, Python 3.11.14, uv 0.12.23, PyArrow 21.0.0,
pytest 8.4.2, Ruff 0.14.0, uv_build 0.9.5. Transitives remain iniconfig 2.3.1,
packaging 26.3, pluggy 1.7.0 and pygments 2.21.0; Windows-only colorama 0.4.6
is locked but not executed here. TLS and artifact verification remain enabled.

## Real input and processed artifact

Upstream Hudl/StatsBomb revision: `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`.
Events SHA-256: `a9aa72c042153fa351c3591ee11e7fba95b0c8841c4489da4aa6809de1edbdf5`.
Verified acquisition-manifest SHA-256:
`f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c`.
Source identity is the FIL-002-verified 2018-07-15 FIFA World Cup Final,
France–Croatia, match 8658, competition 43, season 3. Lineups exist; no 360 or
tracking is assumed. The historical pending rights field in the original
manifest is preserved; SOURCE_POLICY.md records the later owner confirmation.

The actual local processed bundle is:

```text
data/interim/events/match_id=8658/f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c/fil-statsbomb-adapter-1/55f636179da639760de1865f57c4430fdd5c9a4d/
  events.parquet
  quality.json
  manifest.json
```

Generated at (UTC): `2026-10-19T17:20:34.174431+00:00`.
Parquet: **426,244 bytes**, SHA-256
`81154e82b1108231a1a96da9fa071a6880bddbf4b6a02d826a384fcef6b4eaf5`.
Quality JSON: **3,191 bytes**, SHA-256
`8f8d99afdfbaacfcdaec66ab7df8f08039e50f9d470c5185b11afa544d41084d`.
Manifest SHA-256: `3a6120111756130ce1db76b3e320e67768ddd688d036c22e2cb1718cbd79d003`.
All provider raw and derived records remain ignored/local, never committed or
included in release artifacts. The report contains QC/provenance evidence only.

Raw count **2,978**; processed count **2,978**; unique IDs **2,978**;
excluded count **0**; exclusions **[]**; unrecognized types observed **0**
(across 32 reviewed types). Unknown-type behavior is independently tested with
TEST-ONLY future events, not inferred from the real fixture having none.

## Actual null distribution

| Column | Null rows |
| --- | --- |
| `competition_id` | 0 |
| `coordinate_system` | 0 |
| `duration_s` | 747 |
| `end_x` | 1478 |
| `end_y` | 1478 |
| `end_z` | 2963 |
| `event_id` | 0 |
| `event_type` | 0 |
| `event_type_id` | 0 |
| `match_id` | 0 |
| `normalizer_version` | 0 |
| `outcome` | 2562 |
| `outcome_id` | 2562 |
| `pass_outcome` | 2782 |
| `period` | 0 |
| `period_timestamp` | 0 |
| `pipeline_git_sha` | 0 |
| `play_pattern` | 0 |
| `play_pattern_id` | 0 |
| `player_id` | 59 |
| `player_name` | 59 |
| `position_id` | 59 |
| `position_name` | 59 |
| `possession_id` | 0 |
| `possession_team_id` | 0 |
| `possession_team_name` | 0 |
| `provider_index` | 0 |
| `provider_minute` | 0 |
| `provider_second` | 0 |
| `quality_flags` | 0 |
| `raw_event_path` | 0 |
| `raw_event_row` | 0 |
| `recipient_player_id` | 2231 |
| `recipient_player_name` | 2231 |
| `related_event_ids` | 184 |
| `schema_version` | 0 |
| `season_id` | 0 |
| `shot_outcome` | 2955 |
| `shot_type` | 2955 |
| `shot_type_id` | 2955 |
| `shot_xg` | 2955 |
| `source` | 0 |
| `source_manifest_path` | 0 |
| `source_manifest_sha256` | 0 |
| `source_record_json` | 0 |
| `source_revision` | 0 |
| `team_id` | 0 |
| `team_name` | 0 |
| `under_pressure` | 2320 |
| `upstream_revision` | 0 |
| `x` | 64 |
| `y` | 64 |
| `z` | 2978 |

These are source-preserving nulls, not missing statistics filled with zeros.
Zero values mean observed null count zero. `z` is entirely null for 2D event
locations; 3D shot endpoints are separately represented by end_z. Every source
type is retained, including administrative and own-goal records. No own-goal
score or shot xG total is computed. The actual quality.json also records all
type frequencies, transformations, warnings and count/traceability status.

## Executed checks (all final commands exit 0)

From the checkout, with writable uv storage as documented in README:

```bash
uv lock --check
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen pytest -q
uv build
raw_bundle=data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb
fil_pipeline_sha=$(git rev-parse HEAD)
uv run --frozen python -m fil.ingestion.normalize build \
  --raw-bundle "$raw_bundle" --pipeline-revision "$fil_pipeline_sha"
```

All **97 tests passed, 0 skipped**: 41 parent cases plus 56 normalization cases.
Tests cover valid/null/nested data, original UUID/sequence identity, missing
fields, type mismatches, unsupported types, malformed JSON, source failure,
raw/processed counts, reverse lookup, strict Parquet schema round trip,
corrupt outputs, idempotence, raw-tree protection and failed-publication cleanup.
Test records are explicitly TEST-ONLY; unit tests do not fetch provider data.

The real-data validation script independently checked every canonical row's
ID, raw-array offset, provider index, period/minute/second/timestamp, source
manifest digest, full JSON object, team/player/position/possession IDs/names,
locations, nullable pressure/duration/related events and copied pass/shot fields
against the original JSON, without invoking the adapter for those assertions.
All 2,978 rows reconciled; no raw file hash or mtime changed.

Offline verification recomputed every cell, schema, report and artifact hash.
Three exact-ID lookups each resolved the full original record:
`4a44199a-3111-4e28-b567-9c1393e68dff` (index 1),
`a8f0457d-52a8-4072-8165-6dc06fe6bddf` (index 1490),
`883aa370-a1b5-4e33-877a-7a4c83abd26e` (index 2978).
Rebuilding the existing destination preserved every output byte and mtime.
A second output root generated identical Parquet and quality JSON bytes;
independent manifest creation times may differ. These checks each exited 0.

The recorded SHA is the code used for these artifacts. Rebuilding from a later
commit intentionally records that new SHA and uses a separate destination;
the old artifact is not overwritten or relabeled as a newer implementation.

## Fresh checkout and regular-install verification

Created a new local clone at `/tmp/fil-003-verify.uZx81R/checkout` from the
implementation commit above, using `git clone --no-local --branch
feat/fil-003-event-normalization /workspace/football-intelligence-lab <new-path>`
(exit 0), with no venv and an empty dependency cache. The pinned interpreter was
reused; this was not a fresh OS image. All commands below exited 0:

```bash
uv lock --check
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen pytest -q
UV_PROJECT_ENVIRONMENT=.venv-wheel uv sync --frozen --no-editable
UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable ruff check .
UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable pytest -q
UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable python -m fil.ingestion.normalize --help
uv build
```

Both installations passed Ruff and all 97 tests. The existing verified input
bundle was copied locally into the fresh checkout's ignored raw directory
without changing its bytes or manifest, not fetched anew. The regular installed
normalizer built and verified all 2,978 rows and reproduced the exact Parquet
and quality JSON bytes above. This demonstrates environment/code repeatability
for identical input provenance. A newly acquired source manifest may have a
different acquisition time/digest, so row provenance would correctly differ.
Git status remained clean. No data was sent to third parties for this check.

## Failures, fixes and self-review

- Initial Ruff runs reported import ordering, explicit zip strictness and
  line-length issues (exit 1). Corrected without reducing configured lint rules.
- First combined normalization suite: 84 passed, 9 failed (exit 1) on strict
  schema equality after Parquet changed list child names from item to element.
  Declared element child fields explicitly; retained strict schema checks.
  After that correction 93 passed. Four self-review cases for raw-tree safety,
  count mismatch, publication cleanup and canonical keys bring the final suite
  to 97 passing cases.
- A transient execution transport failure interrupted one patch attempt;
  inspected the working tree before retrying. No partial test results were used.
- Self-review hardened integer/bool and finite-number handling, required nested
  Pass/Shot/Carry structures, duplicate JSON-key rejection, unsupported-type
  preservation and output/raw separation. No tests bypassed or disabled.
- Parent source bytes/manifest, source acquisition code/pins, source policy,
  original references and LICENSE remain unchanged. Provider data must stay
  outside version control and packages. No metric/time/spatial gate is inferred.

## Limits and remaining review

Only Linux x86_64 / Python 3.11.14 / pinned PyArrow is locally verified.
Parquet byte determinism on other platforms/versions is not promised. Source
record JSON preserves parsed semantics, not original text formatting; original
files retain exact bytes. Caller-supplied implementation SHA is an audit
assertion, not a signature. The implementation verifies the one reviewed
FIL-002 source bundle; there is no new arbitrary source/URL importer.

FIL-003 is ready for independent review, not accepted or merged. Human approval
and applicable hosted validation remain outstanding. No FIL-004 implementation,
merge, deployment, public data redistribution or commercial use is authorized.


## Delivery and hosted validation

`git push -u origin feat/fil-003-event-normalization` succeeded (exit 0).
`gh pr create --repo Qiao527/football-intelligence-lab --base feat/fil-002-data-acquisition --head feat/fil-003-event-normalization --title "feat: normalize canonical events with source traceability (FIL-003)" --body-file docs/FIL-003_PR.md`
failed (exit 1): `Post "https://api.github.com/graphql": Forbidden`.
`gh run list --repo Qiao527/football-intelligence-lab --branch feat/fil-003-event-normalization --limit 5 --json databaseId,headSha,status,conclusion,url`
also failed (exit 1), API Forbidden. No child PR creation or hosted child CI
PASS is claimed. This is a delivery limitation; the verified branch is retained.
The parent's hosted PASS remains explicitly attributed to the owner's report.

Prepared description: [FIL-003_PR.md](FIL-003_PR.md).
Exact [stacked PR creation link](https://github.com/Qiao527/football-intelligence-lab/compare/feat/fil-002-data-acquisition...feat/fil-003-event-normalization?expand=1)
selects base `feat/fil-002-data-acquisition` and head
`feat/fil-003-event-normalization`, preserving an independently reviewable diff.
A maintainer can open that PR and inspect child Actions, or provide working
API access for those operations. No permission expansion, credential changes,
merge or deployment was performed. Another final parent fetch confirmed the
same SHA `5a18a4e1a417cfbf33941796552b25c9c8ab0c36`; no integration was needed.

Final package inspection (exit 0) confirmed wheel/source distributions contain
implementation/source pins but no raw/interim provider data or Parquet files.
`git ls-files data/raw data/interim` returned no tracked data, `git check-ignore`
confirmed the processed directory is ignored, and `git diff --check` passed.
All local CI commands, 97 tests and builds passed on the final implementation;
later commits only finalize documentation and the prepared PR body.
