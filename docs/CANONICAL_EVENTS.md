# Canonical event contract v1 (FIL-003)

`fil.schema.EVENT_SCHEMA` is the provider-neutral Arrow contract, version
`fil-canonical-events-1`. `fil.ingestion.statsbomb_adapter` contains the
provider-specific projections, version `fil-statsbomb-adapter-1`.
`fil.ingestion.normalize` handles source verification, artifact publication,
offline verification and lookup. No UI, metric or clock code is involved.

PyArrow 21.0.0 is the only new runtime dependency: Arrow types, Parquet I/O and
Zstandard are sufficient; pandas/DuckDB and analytics libraries are unnecessary
for this slice. Official PyPI metadata identifies Apache licensing and Python
>=3.9 support; the verified environment is Python 3.11.14 on Linux x86_64.
The version and published artifact hashes are committed in uv.lock.

## Grain, identity and source semantics

One row for each provider event, including administrative events and unknown
types. Primary key is `(source, match_id, event_id)`. IDs are validated as UUIDs
and preserved as original strings. Duplicate UUID identities, including alternate
case spellings, fail. No records are dropped or synthesized. `raw_event_row`
is the zero-based source-array offset; `provider_index` is preserved separately
and must be strictly increasing. The adapter never sorts to repair bad order.

Missing or explicit null optional fields stay null. Missing related-events and
an explicitly empty list remain distinguishable. No player/location/pressure
defaults are invented; `team` and `possession_team` remain separate. A missing
pass outcome stays null; no completed-pass classification is inferred.

Unknown event types retain common fields and a complete source record, and get
`unrecognized_event_type` in `quality_flags`. The v1 recognition set comprises
the 32 names reviewed in the pinned FIL-002 fixture, not a universal provider
enum. Type-specific projection for an unrecognized type is deliberately absent;
all its nested attributes remain available in `source_record_json` and raw JSON.

## Schema

The following table is generated from the explicit schema and documented below.
All integer columns are signed int64; numeric coordinates/duration/provider xG
are float64. List child fields are explicitly named `element` so strict schema
metadata equality survives compliant Parquet round trips. No type inference
from a particular match or all-null column is used.

| Column | Arrow type | Nullable |
| --- | --- | --- |
| `source` | `string` | no |
| `source_revision` | `string` | no |
| `upstream_revision` | `string` | no |
| `source_manifest_sha256` | `string` | no |
| `source_manifest_path` | `string` | no |
| `pipeline_git_sha` | `string` | no |
| `raw_event_path` | `string` | no |
| `normalizer_version` | `string` | no |
| `schema_version` | `string` | no |
| `event_id` | `string` | no |
| `period_timestamp` | `string` | no |
| `event_type` | `string` | no |
| `source_record_json` | `string` | no |
| `coordinate_system` | `string` | no |
| `match_id` | `int64` | no |
| `competition_id` | `int64` | no |
| `season_id` | `int64` | no |
| `raw_event_row` | `int64` | no |
| `provider_index` | `int64` | no |
| `period` | `int64` | no |
| `provider_minute` | `int64` | no |
| `provider_second` | `int64` | no |
| `event_type_id` | `int64` | no |
| `team_id` | `int64` | yes |
| `player_id` | `int64` | yes |
| `possession_id` | `int64` | yes |
| `possession_team_id` | `int64` | yes |
| `play_pattern_id` | `int64` | yes |
| `position_id` | `int64` | yes |
| `recipient_player_id` | `int64` | yes |
| `outcome_id` | `int64` | yes |
| `shot_type_id` | `int64` | yes |
| `team_name` | `string` | yes |
| `player_name` | `string` | yes |
| `possession_team_name` | `string` | yes |
| `play_pattern` | `string` | yes |
| `position_name` | `string` | yes |
| `recipient_player_name` | `string` | yes |
| `outcome` | `string` | yes |
| `pass_outcome` | `string` | yes |
| `shot_outcome` | `string` | yes |
| `shot_type` | `string` | yes |
| `x` | `double` | yes |
| `y` | `double` | yes |
| `z` | `double` | yes |
| `end_x` | `double` | yes |
| `end_y` | `double` | yes |
| `end_z` | `double` | yes |
| `duration_s` | `double` | yes |
| `shot_xg` | `double` | yes |
| `under_pressure` | `bool` | yes |
| `related_event_ids` | `list<element: string>` | yes |
| `quality_flags` | `list<element: string>` | no |

## Projection rules

- Common source fields: `id` → event_id; `index` → provider_index;
  `minute`/`second` → provider_minute/provider_second; timestamp unchanged;
  source period unchanged. Timestamp format is checked lexically, never turned
  into elapsed/chronological time. Seconds are 0–59; period is 1–5.
- `team`, `player`, `possession_team`, `position`, `type` and `play_pattern`
  nested ID/name pairs are projected with strict types. Missing optional
  entities are null; malformed present objects fail rather than being repaired.
- `location` → x/y/z. Pass/Shot/Carry/Goal Keeper action `end_location` →
  end_x/end_y/end_z. Two-dimensional inputs leave z null; three-dimensional
  shot endpoints preserve z. Numbers widen to float64; non-finite values,
  booleans and malformed arrays fail. No scaling, flipping or direction claim.
- Pass recipient ID/name is projected only for Pass events. The common outcome
  ID/name comes from known pass, shot, goalkeeper, duel, dribble, interception,
  ball_receipt or 50_50 action objects. Pass/shot outcome columns also retain
  those source names. No outcome is inferred from absence.
- Shot type ID/name and `statsbomb_xg` are copied for Shot events; missing xG
  stays null. No xG aggregation, estimation, model, xT or score is computed.
- Pass/Shot/Carry require an action object. Other optional attributes, including
  tactics, cards, substitutions, body parts, related-event links, flags and future
  nested fields, are preserved in complete `source_record_json`. It encodes the
  original JSON object with sorted keys, no whitespace and Unicode preserved;
  this is semantic JSON preservation, not byte-for-byte serialization. Original
  provider bytes remain untouched. Duplicate JSON keys and NaN/Infinity fail.

`period_elapsed_s` and `chronological_s` from the target handbook schema are
intentionally deferred to FIL-004; the original timestamps are sufficient for
this normalization milestone. Full spatial, score and metric gates are not
claimed. Coordinate bounds/direction semantics are not silently imposed here.

## Provenance, artifacts and verification

Rows bind the event-file SHA-256 (`source_revision`), upstream Git SHA, original
array offset and event ID to the verified acquisition-manifest SHA-256.
`raw_event_path` and `source_manifest_path` are relative to the separately
supplied raw bundle, not the processed directory. Absolute machine paths are
excluded from row values so data can be relocated without semantic changes.
FIL-002 verifies all raw files, source identity and manifest before any mapping.
The event hash is checked again before parsing. Owner-confirmed source policy
remains limited to local noncommercial research; the acquisition manifest's
historical pending rights field is not rewritten or treated as current policy.

Outputs are ignored under:

```text
data/interim/events/match_id=8658/<source-manifest-sha>/fil-statsbomb-adapter-1/<FIL-commit>/
  events.parquet
  quality.json
  manifest.json
```

The processed manifest records adapter/schema/code/source versions, aware UTC
creation time, writer settings, PyArrow version and output hashes/sizes.
The caller must supply the SHA of the matching clean implementation checkout;
it is an audit assertion, not a signature. Creation time is retained on reuse.
The quality report covers all columns' null counts, raw/processed/excluded counts,
unique IDs, type frequencies, unrecognized types, transformations and warnings.

Data is written to a temporary sibling directory, read back and verified, then
atomically renamed. Existing datasets are verified and reused without writes;
corrupt/incomplete ones fail rather than being overwritten. Output inside the
immutable raw bundle is rejected. Partial staging directories are cleaned on
failure. New source-manifest/code revisions get separate destinations.

Parquet writer settings: version 2.6, Zstandard compression, dictionary encoding
off, statistics on, row groups of 65,536. Repeated tables are semantically
identical for fixed source/code. Tests also require byte-identical Parquet on
the verified pinned platform; byte identity across other platforms or PyArrow
versions is not promised. Fresh manifests may differ in creation time.

Offline verify regenerates the canonical table from verified raw bytes, then
checks full schema/metadata, every cell, report bytes, file hashes and manifest.
Lookup verifies first and resolves the canonical event ID/array offset to the
original record, rejecting absent IDs. PyArrow's `ParquetFile.read()` is used to
avoid accidental Hive partition-column inference from `match_id=...` directories.
Plain Arrow tables are queryable by event/column without introducing a DB.

## Migration and acceptance

This is the first actual canonical format; no earlier normalized dataset is
overwritten. Changes to mappings/schema require a version update, new fixtures,
traceability regression checks and documented migration evidence. FIL-003
validation addresses DATA-SCHEMA / DEL-SCHEMA, not later gates. Locally verified
does not mean human accepted; see the FIL-003 report for actual checks, upstream
dependency and acceptance status. Provider-derived artifacts must stay ignored
and must not be redistributed, committed or included in package artifacts.
