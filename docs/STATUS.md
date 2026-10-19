# FIL project status — FIL-004 stacked development

- FIL-004: `feat/fil-004-period-aware-clock`, parent FIL-003
  `feat/fil-003-event-normalization` at `3d81faf9ae66f1b2075a1aba5b877baefa42e418`
  (PR #4, dependent on FIL-002 PR #3). Owner reports #4 hosted CI passed.
- Native Git verifies PR/parent heads. Latest fetched main remains `cde6c66`
  (FIL-001); #3/#4 have not reached main. No rebase/reconciliation needed yet.
  Squash-safe downstream-only reconciliation is documented in CODEX_WORKFLOW.md.
- Implemented exact period-aware millisecond clock, observed/estimated durations,
  explicit uncertainty, nominal/stoppage displays, period segments, half-open
  filters/partitions, chronological-range conversion and isolated shootout scope.
- Enriched Parquet retains all 53 canonical columns and original source lineage,
  adding 13 clock/provenance fields. Raw/canonical artifacts and rights are
  unchanged; all provider-derived outputs remain local/ignored.
- Real fixture: all 2,978 events retained. H1/H2 durations from matching source
  end markers are 2,906,080 / 3,003,760 ms; no estimated boundaries or offsets.
  Independent Decimal-based checks, 5/10/15-minute partitions, repeated builds
  and full source/canonical preservation pass. See FIL-004_VERIFICATION.md.
- Ruff, all 180 tests (0 skipped), package builds and fresh editable/regular
  installs pass. Fresh regular-install clock output reproduces exact Parquet
  and QA bytes. No dependencies added.
- DATA-TIME has local technical validation, **not human acceptance**. DEL-TIME-SCORE
  remains unpassed pending score reconciliation; no later analytics gate passes.
- No score/xG/xT/player calculation, network, dashboard, AI agent or video/wall
  clock inference. FIL-005 and later implementation are outside this task.
- Hosted FIL-004 CI/PR delivery is recorded separately when observable. No merge,
  deployment, data-rights expansion or main-history rewrite performed.
