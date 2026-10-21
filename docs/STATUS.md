# FIL project status — FIL-005 stacked development

- FIL-005 implemented on `feat/fil-005-score-reconstruction`, parent FIL-004
  `feat/fil-004-period-aware-clock` at `48d566a2664a21b84b4ba8777de39116eff5480f`
  (PR #5), transitively dependent on FIL-003 #4 and FIL-002 #3.
- Owner reports PRs #3/#4/#5 exist and hosted CI passed. Native Git verifies
  their heads/ancestry; current fetched main is still FIL-001 `cde6c66`.
  GitHub API is Forbidden, so parent CI/approval state cannot be independently
  inspected. No merge performed; sequential squash-safe plan is documented in
  STACK_RECONCILIATION.md and CODEX_WORKFLOW.md.
- Typed, provider-isolated score attribution, explicit own-goal pair deduplication,
  regular/extra penalties, separate shootout counters, chronological per-event
  before/after states, immutable Parquet/QA/manifests and offline CLI implemented.
  No dependencies, canonical schema, raw data or clock semantics changed.
- Pinned real match 8658: 2,978 states retained, zero exclusions; 23 shots + two
  own-goal representations → 24 audit decisions, six goal awards including
  one own goal and one scored penalty. Independently reconstructed **France 4–2
  Croatia**, identical to official original match metadata. No real extra time
  or shootout; those semantics have TEST-ONLY coverage.
- All 13 raw/canonical/clock input files preserve hashes and modification times.
  Reuse preserves output bytes/mtimes; independent-root and fresh regular-install
  rebuilds reproduce exact Parquet/QA bytes. No provider datasets in Git/packages.
- Ruff, all **251 tests** (71 new; 0 skipped), frozen install/lock check, package
  builds, fresh empty-cache editable/regular installations and CLI checks pass.
  Implementation/evidence: FIL-005_VERIFICATION.md. New branch hosted CI is
  unobserved; local reproduction is not a hosted success claim.
- DATA-SCORE has local technical validation for this pinned fixture. DATA-TIME
  remains verified with unchanged clocks; DEL-TIME-SCORE technical requirements
  are locally verified. Independent review and human approval remain pending;
  milestone acceptance and all later analytics gates are **not declared**.
- No xG/xT aggregation, player ratings, networks, dashboard, AI, rights expansion,
  merge or deployment. Registration/noncommercial research confirmation persists;
  raw and derived provider datasets remain local/ignored, not redistributed.
- Branch is pushed. PR creation and hosted-CI queries both exit 1, GitHub API
  Forbidden. Prepared review body and exact FIL-004-targeted creation link are
  in FIL-005_PR.md; no new PR or hosted success is claimed. Final parent/main
  fetch confirms unchanged heads; no reconciliation is needed yet.
