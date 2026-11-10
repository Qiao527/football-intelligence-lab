# FIL-005 verification — 2026-10-19 UTC

## Dependency, scope and implementation

Branch `feat/fil-005-score-reconstruction`, parent FIL-004 PR #5 at
`48d566a2664a21b84b4ba8777de39116eff5480f`. Transitive dependencies: FIL-003
PR #4 / FIL-002 PR #3. Stack heads and conditional squash-safe transplants are
in [STACK_RECONCILIATION.md](STACK_RECONCILIATION.md). At inspection, main is
`cde6c66` (FIL-001), all parent heads unchanged; no merge/rebase was performed.
Owner reports parent hosted CI passed; GitHub API inspection is Forbidden.

Tested implementation: `f380ef3b10c5524317fed071c51c9d6bde1436d6`. Later evidence/documentation commits do not
change implementation. No new dependencies or original reference edits.
Python 3.11.14, uv 0.12.23, PyArrow 21.0.0, pytest 8.4.2, Ruff 0.14.0;
build backend uv_build 0.9.5 (unchanged pin). Linux x86_64 validated only.

Provider-isolated source signals + pure score reconstruction; fixed-schema
per-event states and decision ledger; offline atomic build/verify CLI; independent
source verification script; 71 new offline tests; score contract/task brief;
README/status/workflow and CI CLI smoke updates. Original raw/canonical/clock
files, LICENSE, pyproject/lock and both original references are unchanged.

## Actual source and local result

StatsBomb/Hudl upstream `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`:
`data/events/8658.json` SHA-256
`a9aa72c042153fa351c3591ee11e7fba95b0c8841c4489da4aa6809de1edbdf5`;
original `data/matches/43/3.json` SHA-256
`f89dbd4aedcaf9c9e4ec9d8e745d5d54596500ec357d7489c914a2f126805adf`.
Official record: match 8658, 2018-07-15, FIFA World Cup / season 2018 / Final,
France (771) home, Croatia (785) away; **4–2**.

- 2,978 raw → 2,978 canonical → 2,978 clock → 2,978 score states; zero excluded
  state rows, every original ID/record/clock field preserved.
- 23 shots (five Goal outcomes), plus two own-goal source records = 25 scoring
  source representations → 24 decisions. Exactly one explicitly linked pair
  merges into one goal. Eighteen non-goal shot decisions award no goals.
- Six match-play goals: five Shot goals including one scored penalty, plus one
  own goal. Reconstructed and official final states both **France 4–2 Croatia**.
- The own-goal beneficiary is France, defender/actor Mario Mandžukić (5472),
  actor team Croatia. The For record's missing player is preserved in its state;
  attribution comes only from the linked Against record, never possession team.
- No extra time or shootout in this real fixture; report `shootout_score=null`.
  Extra time, stoppage, regular/extra penalties, missed penalties and shootout
  separation are TEST-ONLY cases. Official shootout result certification is not
  implemented. Warnings, unknown types, actor-player null decisions and estimated
  clock-event counts are all zero for this verified fixture.

Actual progression (original timestamp, period/index retained):

| Original goal source ID(s) | Period / index | Score after |
| --- | --- | --- |
| `548ccef9-f39f-4e4e-b2fe-9e98fb0d7ab7` + `b9009a7a-314a-42c5-8c74-ed2d4e8e0ef0` | 1 / 677–678 | 1–0 (one own goal) |
| `d3dd1458-33f9-4810-aaf5-3bca48c7897d` | 1 / 911 | 1–1 |
| `864ce121-d6ff-4c6e-b1f9-73f51c8c48bc` | 1 / 1053 | 2–1 (penalty) |
| `8b8479e0-b82d-47d4-bc24-f80ff589dbe6` | 2 / 1863 | 3–1 |
| `8b3b883a-7cca-4677-bfde-e4f9c3ce8aac` | 2 / 2060 | 4–1 |
| `7906899a-fd84-4697-af0d-dc9903b4f5e0` | 2 / 2171 | 4–2 |

The independent script reads verified original JSON and metadata, applies a
separate direct own-goal partner rule (without importing reconstruction), then
checks **every** before/after score, goal IDs/beneficiaries/actors, raw record,
canonical values and clock values. This is independent recomputation by the
implementer, not a substitute for the mandatory separate reviewer.

## Exact inputs and output

```bash
raw_bundle=data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb
dataset=data/interim/events/match_id=8658/f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c/fil-statsbomb-adapter-1/55f636179da639760de1865f57c4430fdd5c9a4d
clock_dataset=data/interim/clocks/match_id=8658/3a6120111756130ce1db76b3e320e67768ddd688d036c22e2cb1718cbd79d003/fil-period-clock-1/a377b77d0c672582210d915adca700062ba78b10
score_dataset=data/interim/scores/match_id=8658/cf1ffbb424bda478107665abddf152bc66fb242ab4166657dc3abfc1daacc798/fil-score-1/f380ef3b10c5524317fed071c51c9d6bde1436d6
implementation_sha=f380ef3b10c5524317fed071c51c9d6bde1436d6
```

Source manifest: `f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c`.
Canonical manifest: `3a6120111756130ce1db76b3e320e67768ddd688d036c22e2cb1718cbd79d003`.
Clock manifest: `cf1ffbb424bda478107665abddf152bc66fb242ab4166657dc3abfc1daacc798`.
Score manifest: `2bc4aca2c3b476818e87a655f3854c3a7d1ec9b28de563bdc7154dd4ee79df6e`.
Score artifact created `2026-10-19T18:09:29.476379+00:00`.
Actual manifests/datasets remain local/ignored under the paths above.

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| `decisions.parquet` | 8626 | `01b00c8c655a8582e5b6c90254acd22a122ae6ed9e722a8b8b2e00a285e51976` |
| `quality.json` | 2424 | `8c869fcebfcceaf487d28903d75f185e06de3af292efe23dfc84c8176811d994` |
| `score_events.parquet` | 473809 | `4f746a22605a3291d7705ca588f05b2333a8482c760daa38fcb673d997130b50` |

All 13 input files (raw, canonical and clock bundles) preserve SHA-256 and
modification times after build, verify, reuse, independent-root rebuild and
independent checks. Reuse also preserves all four output files' hashes/mtimes.
A second output root reproduces both Parquet files and QA byte-for-byte;
only newly generated manifest timestamps differ.

## Executed verification and exits

Workspace and fresh-checkout commands below all exit **0**, unless an earlier
failed development attempt is explicitly described afterward. No skipped or
expected-failure tests. Baseline before changes: 180 tests pass. Final: **251**.

| Command | Verified outcome |
| --- | --- |
| `uv sync --frozen` | Workspace and empty-cache fresh editable install pass |
| `uv lock --check` | Manifest/lock agree; no dependency changes |
| `uv run --frozen ruff check .` | Workspace and fresh checkout pass |
| `uv run --frozen pytest -q` | Workspace 251 passed; fresh editable 251 passed |
| `uv build` | Wheel and sdist build successfully |
| `UV_PROJECT_ENVIRONMENT=.venv-wheel uv sync --frozen --no-editable` | Fresh regular install pass |
| `UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable ruff check .` | Fresh regular lint pass |
| `UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable pytest -q` | Fresh regular 251 passed |
| `uv run --frozen --no-editable python -m MODULE --help` | Fresh regular normalize, fil.time, fil.metrics.score_cli all pass |
| `git diff --check` | Whitespace check pass |

Exact real-data commands (with variables above), each exit **0**:

```bash
uv run --frozen python -m fil.metrics.score_cli build \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --clock-dataset "$clock_dataset" --pipeline-revision "$implementation_sha"
uv run --frozen python -m fil.metrics.score_cli verify \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --clock-dataset "$clock_dataset" --score-dataset "$score_dataset"
# Repeat the first build unchanged to verify idempotent reuse.
uv run --frozen python -m fil.metrics.score_cli build \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --clock-dataset "$clock_dataset" --pipeline-revision "$implementation_sha" \
  --output-root data/interim/fil-005-independent-rebuild
uv run --frozen python scripts/verify_score_source.py \
  "$raw_bundle" "$dataset" "$clock_dataset" "$score_dataset"
```

Fresh local clone: `/tmp/fil-005-fresh-pwzje7zv/checkout`, commit `f380ef3b10c5524317fed071c51c9d6bde1436d6`,
empty uv cache `/tmp/fil-005-fresh-pwzje7zv/empty-cache`. Editable tests 251 passed in 2.11s;
regular tests 251 passed in 2.17s. Regular import verified from its site-packages,
not the source checkout. Unchanged local licensed inputs were copied within
this workspace to the fresh clone; no network fetch or external redistribution.
Fresh regular CLI rebuild and independent script pass and reproduce both
Parquet files/QA exactly. Wheel and sdist inspection confirms no provider raw,
interim or Parquet datasets. CI includes all existing checks plus score CLI help;
hosted execution of the new branch is not claimed.

Local logs: `/tmp/fil-005-*.log`, `/tmp/fil-005-evidence.json`,
`/tmp/fil-005-fresh-evidence.json` and fresh-clone logs. These temporary files
are supplementary; retained evidence, commands and hashes are in this document.

Earlier development failures were not bypassed: synthetic fixtures initially
omitted the adapter's millisecond timestamp/entity ID requirements, fixed before
all 251 tests passed; initial Ruff line/import findings were formatted/fixed.
A path-key typo in the exploratory harness failed before dataset generation.
The first packaging-audit harness treated `dist/.gitignore` as a tar archive;
archive selection was corrected and both real archives inspected successfully.
No production checks were weakened or tests skipped.

## Self-review, limits and gate assessment

Reviewed parent-only diff, explicit own-goal graph ambiguity, linked goalkeeper
non-awards, same-time unrelated shots, provider vs possession team, null actors,
missed penalties, extra time/shootout separation, H1 stoppage/H2 opening shared
scalar boundaries, complete periods/final marker, official mismatch rejection,
all-ID reverse lookup, atomic failure cleanup, valid-Parquet tampering and full
source/metadata/clock chain corruption. Final fixes/test additions precede the
recorded implementation commit and all real/fresh evidence.

DATA-SCORE: **local technical PASS** for this pinned 8658 fixture. DATA-TIME:
prior FIL-004 evidence plus unchanged-clock verification. DEL-TIME-SCORE:
**local technical requirements verified**, independent review and human approval
still pending; do not mark the milestone accepted. No DATA-SHOTS, spatial,
filter/UI, research or later analytics gate is passed.

Limits: one reviewed source fixture/schema, strict exact-time own-goal pairing,
no fuzzy or cross-provider deduplication, no separate official shootout metadata,
no rule adjudication/VAR/disallowed-goal recovery beyond source semantics,
no video clock claim or cross-platform bitwise guarantee. Fail closed for
unsupported scoring fields, ambiguous links or final-score differences. No xG
aggregation, ratings, networks, dashboard or AI. Source rights remain local
noncommercial research with owner-confirmed registration, no redistribution;
historical acquisition-time pending attestation is not rewritten.

## Delivery status

The PR must target `feat/fil-004-period-aware-clock`, not main while unmerged.
Push/PR API outcome and final remote-head check are recorded in FIL-005_PR.md.
No merge, deployment, data-rights expansion or main-history rewrite authorized.
