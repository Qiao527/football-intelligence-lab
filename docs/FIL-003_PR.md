# FIL-003 — Canonical event normalization and source traceability

## Stack and workflow

**Base:** `feat/fil-002-data-acquisition` at
`5a18a4e1a417cfbf33941796552b25c9c8ab0c36`, dependency PR #3.
The owner authorized stacked development and reports parent CI passed. Native
Git confirms the PR #3 head and parent SHA; local parent lint/41 tests/source
verification pass. Parent was fetched again unchanged; no reconciliation needed.
Review this diff against the parent, not main. Reconcile/retarget when upstream
changes or merges; do not reintroduce parent commits after a squash merge.

Update AGENTS.md, CODEX_WORKFLOW.md, GATES.md and the PR template for autonomous
stacked work, parent evidence/assumptions, affected-check reruns, delivery API
limitations and explicit human acceptance. No merge/deployment permission added.

## Implementation and files

- `src/fil/schema.py`: provider-neutral versioned Arrow schema (53 typed columns).
- `src/fil/ingestion/statsbomb_adapter.py`: isolated source projection, nullable
  semantics, source order/UUID preservation and unknown-type retention.
- `src/fil/ingestion/normalize.py`: atomic Parquet build, full offline verification,
  manifests/QC and exact event-ID reverse lookup.
- Add 56 normalization test cases; update the foundation dependency contract to
  exactly the one required runtime dependency, PyArrow 21.0.0. uv.lock pins it.
- Document schema/projections/migration, CLI, source rights and current status;
  add regular-installed CLI validation to the existing CI. Ignore derived data.

Original source acquisition code/pins, raw files/manifest, source policy, LICENSE
and both original reference documents are unchanged.

## Reproduction

Use the README's Python 3.11.14 / uv 0.12.23 setup (including writable cloud uv
storage), acquire or retain the verified FIL-002 raw bundle, then:

```bash
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen pytest -q
uv build
raw_bundle=data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb
uv run --frozen python -m fil.ingestion.normalize build \
  --raw-bundle "$raw_bundle" --pipeline-revision "$(git rev-parse HEAD)"
```

Use the returned dataset path with the documented `verify` and `lookup`
subcommands. Existing valid outputs are reused without writes. Different source
manifest/code revisions get distinct destinations. Full source/row provenance
is verified before publication and on every reuse; corrupt outputs fail closed.

## Actual evidence

- 2,978 raw → 2,978 canonical rows; 2,978 unique IDs; zero exclusions;
  zero unrecognized types in this fixture. Unknown future types are tested and retained.
- Independent per-row source JSON and typed-field comparisons passed for every
  record. Three exact-ID lookups returned original source records.
- Cached rebuild preserved all bytes/mtimes. A separate output root produced
  identical Parquet/QC bytes. Raw bytes/mtimes never changed.
- Frozen install, Ruff and all **97 tests passed (0 skipped)**; source/wheel builds pass.
- Fresh checkout/empty dependency cache: editable and regular installs each
  pass lint and 97 tests. Regular-install normalization with the identical
  verified raw manifest reproduces all Parquet and quality-report bytes.
- Parquet SHA-256: `81154e82b1108231a1a96da9fa071a6880bddbf4b6a02d826a384fcef6b4eaf5`.
- Full null distributions, source and artifact hashes, code SHA, actual commands,
  initial failures/fixes and limitations: `docs/FIL-003_VERIFICATION.md`.
- Strict Parquet list-child schema mismatch was fixed explicitly; assertions
  were retained. No failing tests were skipped or bypassed.

## Rights, boundaries and acceptance

Provider raw and canonical datasets remain local/ignored and are excluded from
Git and package artifacts. Rights remain limited to the owner's confirmed local
noncommercial research; no redistribution/commercial permission is inferred.

Only provider shot xG is copied as a nullable source field; no xG/xT aggregation,
model, score, reconstructed clock, dashboard or AI feature is implemented.
The schema preserves complete nested records as semantic JSON while raw bytes
remain immutable. Linux x86_64 / Python 3.11.14 / PyArrow 21.0.0 is verified;
byte identity across different versions/platforms is not promised.

DATA-SCHEMA/DEL-SCHEMA have local technical verification. FIL-003 is implemented
and ready for independent review, **not human accepted**. Hosted child CI results
must be reported separately; the parent's reported CI does not prove child CI.
No merge, deployment or next milestone is authorized by this PR.


## Delivery limitation

The CLI's parent-targeted PR creation and hosted child Actions query returned
API Forbidden. No child PR was created by that command or child hosted PASS
observed. The branch and this body are preserved; use the parent-specific
creation link in FIL-003_VERIFICATION.md. This does not block the completed
local engineering work or imply milestone acceptance.
