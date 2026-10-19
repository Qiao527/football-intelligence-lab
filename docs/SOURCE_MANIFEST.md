# FIL-002 source manifest v1

The actual manifest is local, next to immutable provider files:

```text
data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/
  README.md
  LICENSE.pdf
  data/competitions.json
  data/matches/43/3.json
  data/events/8658.json
  data/lineups/8658.json
  manifest.json
```

All paths above are ignored. The committed `statsbomb_source.json` is an audited
pin registry containing upstream revision, reviewed match identity, byte sizes
and SHA-256 digests, not a copy of provider event/match/lineup records.

## Fields

| Field | Meaning |
| --- | --- |
| `manifest_version` | Integer schema version, currently 1. |
| `source`, `repository`, `upstream_revision` | StatsBomb Open Data identity and immutable full upstream commit SHA. |
| `pipeline_git_sha` | Full FIL implementation SHA supplied by the caller; record the code used, not an inferred upstream or future commit. |
| `acquisition_adapter_version` | Acquisition validation contract, currently `fil-source-1`. |
| `normalizer_version`, `metric_spec_version` | Null: neither normalization nor metric generation occurred. |
| `acquired_at_utc` | Aware UTC ISO-8601 time after source retrieval. Preserved when a verified cache is reused. |
| `files[]` | Relative path, exact bytes, SHA-256, requested immutable HTTPS URL and final URL for each original file; redirects are rejected. |
| `usage` | Provider, source terms URLs, attribution requirement, registration caveat, policy document and explicit `redistribution_approved: false`. |
| `quality.identity` | Match ID, competition/season ID/name, date, team ID/name and stage read from match metadata and checked against competitions/lineups and the audited registry. |
| `quality.event_count_raw`, `output_record_count` | Number of records in the preserved event file; no normalized output table or row filtering exists. |
| `quality.unique_event_ids`, `duplicate_event_ids` | Parse original UUIDs and reject missing, invalid or duplicate IDs; do not create/replace IDs. |
| `quality.event_type_counts`, `top_level_key_counts`, `period_counts` | Source inspection frequencies; no metric or match-clock calculation. |
| `quality.nullable_counts` | Missing/null player, location and possession_team counts; original missing values stay missing. |
| `quality.unknown_type_count` | Null, because a complete provider enum audit is outside FIL-002. Unknown values are not silently reported as zero. |
| `quality.sample_event_ids`, `warnings` | First/middle/last original IDs for reverse lookup and explicit limitations. |
| `source_integrity_status` | PASS only after all implemented byte/identity/structure checks complete. Not a football gate approval. |
| `rights_gate_status` | PENDING_OWNER_CONFIRMATION. The CLI cannot infer legal approval. |

## Failure and repeatability contract

HTTPS reads use platform/default certificate validation, a 30-second timeout
and the reviewed file size as an upper bound. Non-200/unavailable responses,
redirected results, unexpected sizes/hashes, malformed JSON/top-level records,
missing/duplicate IDs or metadata disagreement fail before bundle publication.
The workflow handles only the reviewed six files; lineups are available and
required for this pin. It neither fetches nor assumes 360/tracking coverage.

Validated bytes are written to a temporary sibling directory, verified on disk,
then renamed into the revision-specific directory. Existing bundles are verified
offline, never refreshed or overwritten. Timestamp and original pipeline SHA
remain stable on cache reuse. An independently acquired bundle may have a new
UTC timestamp or FIL revision, but must have the same pinned source bytes and
QC facts. Idempotence does not mean inventing an identical acquisition time.

Offline verification recalculates digests and source facts and compares the
whole regenerated manifest. Missing/extra files, symlinks, modified manifests
or corrupt cached bytes fail closed. Preserve the corrupt bundle for diagnosis;
use a different ignored root for a new acquisition rather than deleting evidence.
An upstream revision change needs a separately reviewed pin update and new
revision directory; do not change expected hashes merely to suppress a failure.

The manifest is not a digital signature. SHA-256 proves equality to the reviewed
registry, not independent provider authorship. The initial review uses HTTPS
and the pinned official Git revision. A caller-supplied FIL SHA is an audit
assertion: run from the matching clean checkout to make it meaningful.

The offline unit tests use explicitly labeled TEST-ONLY records, never football
observations. They inject source bytes/transport; ordinary pytest runs do not
download the provider dataset. See SOURCE_POLICY.md for unclosed rights gates.
