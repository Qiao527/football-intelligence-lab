# FIL-005: reconstruct scores and goal attribution with source traceability

## Problem and resulting behavior

FIL-004 provides trustworthy period-aware event clocks but no reconciled score.
FIL-005 reconstructs before/after scores for every original event and creates
an auditable goal/shot decision ledger. Explicitly linked own-goal perspectives
count once; match-play penalties count normally; shootout goals stay separate.
Ambiguity, missing scoring semantics or official final-score mismatch blocks
output. Raw, canonical and clock records remain immutable.

## Stack and upstream assumptions

Target **feat/fil-004-period-aware-clock**, PR #5 at
`48d566a2664a21b84b4ba8777de39116eff5480f`; depends on #4/#3.
Owner reports all parent hosted CI passed. Local parent baseline: 180 tests.
Main remains FIL-001 `cde6c66`; API Forbidden prevents independent hosted/status
inspection. No accepted metadata/schema/rights changes are assumed. Parent-only
review: `git diff 48d566a2664a21b84b4ba8777de39116eff5480f...HEAD`.
See STACK_RECONCILIATION.md for sequential squash-safe transplants using latest
incorporated parent anchors, recoverable refs and expected-head leases. Recheck
parents before delivery; reconcile changes and rerun verification. No merge.

## File-change summary

- `src/fil/ingestion/statsbomb_score.py`: original-record scoring/metadata adapter.
- `src/fil/metrics/score.py`: typed pure reconstruction, own-goal linkage and
  official reconciliation; fixed Arrow schemas, version `fil-score-1`.
- `score_artifacts.py`, `score_cli.py`: atomic immutable build/offline verify,
  raw/canonical/clock manifest chain, deterministic Parquet and QA.
- `tests/test_score.py`: 71 offline TEST-ONLY football/integrity cases.
- `scripts/verify_score_source.py`: independent original-record recomputation,
  all-event score-state and raw/canonical/clock preservation checks.
- CI: regular-install score CLI check. README, STATUS, score metric contract,
  task brief, stack/workflow plan and actual verification evidence.
- LICENSE, original references, dependency declarations/lock and parent clock
  implementation unchanged. No provider datasets committed or packaged.

## Setup and verification

Python 3.11.14, uv 0.12.23; sole runtime dependency remains PyArrow 21.0.0.

```bash
uv sync --frozen
uv lock --check
uv run --frozen ruff check .
uv run --frozen pytest -q
uv build
UV_PROJECT_ENVIRONMENT=.venv-wheel uv sync --frozen --no-editable
UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable pytest -q
```

Every command exits 0 locally. All 251 tests pass (0 skipped); fresh empty-cache
editable and regular installs pass lint/tests/build/CLI. Real offline build,
verify, reuse and independent recomputation all exit 0. **France 4–2 Croatia**,
matching original official metadata: 2,978 event states; six goals including
one own goal and one match-play penalty. Twenty-five source representations
become 24 decisions, zero event exclusions. All 13 input files preserve bytes
and mtimes; repeated/fresh builds reproduce both Parquet files/QA exactly.

See FIL-005_VERIFICATION.md for tested implementation SHA, exact fixture/input/
output paths, command/exits, source/output SHA-256, dependency versions, failed
intermediate attempts/corrections and limits. SCORE_RECONSTRUCTION.md documents
the CLI: pass verified raw/canonical/clock directories to
`python -m fil.metrics.score_cli build --pipeline-revision "$(git rev-parse HEAD)"`;
use returned score directory with `verify`. Local ignored provider data only.

## Gates, limits and review

DATA-SCORE and DEL-TIME-SCORE requirements have local technical evidence for
this fixture; independent review and human approval remain pending. New branch
hosted CI is not claimed. Real fixture has no extra time/shootout; their tests
are clearly synthetic. No separate official shootout result certification,
fuzzy pairing, VAR adjudication or cross-provider/general schema guarantees.
No xG aggregation, ratings, networks, UI, AI, new dependencies or rights changes.
Ready for scoped review; no later milestone acceptance, merge or deployment.

## Delivery limitation

Pending final push/API attempt; this section records actual delivery outcome.
Intended creation link (base FIL-004, head FIL-005):
https://github.com/Qiao527/football-intelligence-lab/compare/feat/fil-004-period-aware-clock...feat/fil-005-score-reconstruction?expand=1
