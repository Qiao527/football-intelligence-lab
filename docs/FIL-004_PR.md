# FIL-004 — Period-aware event clock and explicit time filters

## Stack and assumptions

Base: `feat/fil-003-event-normalization` at
`3d81faf9ae66f1b2075a1aba5b877baefa42e418` (PR #4, dependent on PR #3).
Owner reports parent hosted CI passed; native Git verifies both PR head refs.
Local parent lint/97 tests pass. Latest fetched main remains `cde6c66` (FIL-001),
so the parents have not reached main and no reconciliation is needed yet.

Review only the diff against FIL-003. Once #3/#4 merge, transplant only FIL-004
commits after the recorded FIL-003 anchor onto updated main, accounting for
squash history, rerun affected/full checks and real-data verification, regenerate
code-bound artifacts and retarget. CODEX_WORKFLOW.md documents this procedure;
no parent/main merge or history rewrite was performed.

## Changes and scope

- `fil.time.clock`: exact ms parsing, nominal/stoppage labels, observed period
  boundaries, explicit fallback/propagated uncertainty, frozen PeriodRange and
  PeriodInfo, half-open ranges, partitioning and chronological conversions.
- `fil.time.artifacts` / `python -m fil.time`: immutable clock Parquet/QA/manifests,
  complete upstream revalidation, offline build/verify and source linkage.
- Add 83 TEST-ONLY clock cases (180 total). Extend regular-install CLI checking
  in existing CI. Update README/STATUS, MATCH_CLOCK.md and verification evidence.
- Preserve all 53 canonical columns and source IDs/timestamps/JSON exactly;
  append 13 typed clock/provenance columns in a separate enriched artifact.
- No dependencies, raw/canonical data, source policy/rights, original reference
  documents or canonical normalization contract changed.

No score/xG/xT/player calculation, network, dashboard, AI or video/wall-clock
inference. Default match-play includes periods 1–4 and excludes shootout period
5; ordinary match-play penalties remain retained. Stored shootout chronology is
null. No derived raw data is committed, redistributed or packaged.

## Reproduction

Using the README's Python 3.11.14 / uv 0.12.23 setup and verified raw/canonical
input directories, run:

```bash
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen pytest -q
uv build
uv run --frozen python -m fil.time build \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --pipeline-revision "$(git rev-parse HEAD)"
```

Use the returned clock_dataset with `python -m fil.time verify` as documented.
Artifacts stay ignored in `data/interim/clocks/`, versioned by canonical manifest,
clock version and actual implementation SHA. Existing outputs are verified and
reused without writes; corrupt outputs fail closed rather than being repaired.

## Actual evidence

- Real match 8658: 2,978 input → 2,978 clock rows, all original IDs/source records.
- Source Half End durations: H1 2,906,080 ms; H2 3,003,760 ms. H2 offset is the
  observed H1 duration, not 45 minutes. No estimated boundaries/offsets on this
  fixture. Final display labels: `45+3:26.080` / `90+5:03.760`.
- Independent Decimal-based recomputation checked every source timestamp,
  period duration/offset/chronology and all canonical columns. Inputs unchanged.
- Real 5/10/15-minute partitions cover every event exactly once. Shared terminal
  instants have explicit period identity; no epsilon time or ID collapsing.
- Ruff and all **180 tests passed, 0 skipped**. Source/wheel builds pass.
- Fresh checkout/empty cache: editable and regular installations pass lint,
  all 180 tests, both CLI checks and builds. Fresh regular install reproduces
  exact clock Parquet/QA bytes from the identical verified inputs.
- Cached rebuild preserves bytes/mtimes; a separate rebuild produces identical
  Parquet/QA. Full commands, hashes, marker IDs/period assumptions, initial style
  findings and limitations: `docs/FIL-004_VERIFICATION.md`.

## Gates and review

DATA-TIME has local technical verification only; FIL-004 is not human accepted.
**DEL-TIME-SCORE and later analytics gates remain unpassed**: score work is
FIL-005, not part of this clock. Parent hosted CI is owner-reported; hosted
FIL-004 CI must be observed separately and cannot be inferred from local passes.

Extra time/shootouts are covered by TEST-ONLY fixtures, absent in the real match.
Missing Half End uses a qualified max-observed fallback, propagating uncertainty;
conflicting markers/regressions/missing intermediate periods fail. Half End and
next Half Start may share a scalar boundary; explicit period ranges distinguish
them. No physical break/video timing or other platform is validated.
Human/independent review is required. No merge, deployment or data-rights change.


## Delivery limitation

Parent-targeted PR creation and FIL-004 Actions queries returned API Forbidden.
No child PR was created by that command and no child hosted CI result is
claimed. The pushed branch and prepared description remain reviewable; the
exact parent-targeted creation link is in FIL-004_VERIFICATION.md. Local checks
are complete, while hosted validation and human acceptance remain outstanding.
