# First real multi-match corpus — pilot delivered, expansion blocked

Development parent: draft PR #14 at
`90ba21dd22e30f842aee11891d6fb3069c435696`. All existing PRs remain unmerged.
The owner's conditional approval is recorded in [SOURCE_POLICY.md](../SOURCE_POLICY.md).
This delivery acquires exactly 12 of the 126 newly authorized payloads: six pilot
matches, 18,477,846 bytes. The remaining 114 payloads for 57 matches were **not
acquired**, because the complete pilot gate did not pass.

## Actual corpus and quality outcome

| Match | Original events | Temporal analysis status |
| --- | ---: | --- |
| 8649 Uruguay–France | 3,375 | PASS |
| 8650 Brazil–Belgium | 3,589 | PASS |
| 8651 Sweden–England | 3,303 | PASS |
| 8652 Russia–Croatia | 4,041 | PASS; period-5 shootout separate |
| 8655 France–Belgium | 3,354 | PASS |
| 8656 Croatia–England | 4,165 | BLOCKED: conflicting Half End evidence |
| 8658 France–Croatia | 2,978 | Existing verified development fixture; never in predictive splits |

The complete canonical audit table retains **24,805 original records across seven
matches**. The separately labelled validated score/process table has **20,640
records across six matches**, 179 source player identities and eight teams. No
blocked records are deleted or reclassified as valid. This is a men's World Cup
knockout pilot with strong repeated-team/selection effects, not an adequate or
general football research corpus.

Source bytes are immutable, checked against pinned upstream Git blob identities,
size and recorded SHA-256. Manifests record original URL, fetch time, revision,
implementation SHA, exact approval enumeration hash and scope. Original match
metadata, README and agreement are separately hash-verified; later quality/corpus
rights assessments bind their exact hashes, URLs, owner authorization,
registration attestation, attribution/branding and exclusions. Raw manifests are
not rewritten to add later assessment fields. No unrestricted training licence is
claimed; local empirical baselines only, no xT/VAEP or model publication.

Independent reconciliation reads raw JSON directly. It checks every original ID,
record and projected identity/coordinate/xG field, source hashes, all supported
score states, shootout separation, lineup/exposure integration, future-window
labels/features, training-only probabilities, test Brier/log loss and calibration.
`independent-verification: PASS` means the audit and reported failures agree with
source; it **does not** mean the complete six-match acquisition gate passed.
`pilot_gate: BLOCKED` is the controlling expansion decision.

All five newly validated matches have consistent recorded XI/substitution/off/on/
card census evidence under the current contract. Official minutes and per90
eligibility remain null/false; unused-roster exposure stays unknown. Source
positions are event samples, not tracking or inferred tactical roles. No missing
shot xG was found in the six new raw files; non-shot xG remains null. Per-column
null counts, unrostered/unknown records and exact source evidence are in the local
quality reports. `Bad Behaviour` and `50/50` are retained and reported as outside
the original normalizer's recognized-type list; no events are dropped. The fixed
forecast owner-record taxonomy excludes unmapped context events and never claims
to count every independent ball touch.

Native possession IDs crossing period boundaries remain intact, with their
continuous-time/order windows excluded. Native 120×80 coordinates, original IDs,
provider index and timestamp are preserved; no flips, physical attacking direction,
off-ball positions or intentions are inferred.

## Material failure and stop decision

8656 has opposing-team Half End timestamps differing by 107, 160, 280 and 40 ms
in periods 1–4 respectively. Existing clock validation rejects conflicting end
markers. The held original provider specification describes a period ending but
does not certify which conflicting timestamp to use. No max/mean replacement,
source edit or gate relaxation was introduced. Raw goal reconciliation can still
be checked independently, but temporal score states, continuous exposure and
process analysis for this match remain blocked.

The owner's all-pilot-pass condition therefore prevents acquisition of the other
57 matches. The next dependency is a source-supported resolution/versioned
boundary-uncertainty contract and its independent review, not permission to ignore
the discrepancy. No owner rights reapproval is requested for the unchanged scope.

## Real predictive diagnostic, not model validation

The [pilot-only protocol](WORLDCUP_PILOT_PROTOCOL.md) was committed before fitting.
The planned full-corpus June cutoffs remain unexecuted. In this separate technical
diagnostic, train uses 8649/8650 (2,150 eligible windows), validation uses
8651/8652 (2,292), and test uses 8655 (1,236). All partitions comprise complete
matches, same-day fixtures stay together, and 8658 is excluded entirely.

There are 5,678 eligible five-owner-record windows and 1,701 censored/unresolved
windows across the five newly validated matches. Forecasting occurs after the
complete cutoff source record is observed, not before the action or at a
certified live physical time. Features use that record only; labels use exactly
five later owner records in the same native possession/period. The complete-window
cohort favors longer sequences and overlaps within possessions.

All comparisons below were predefined and evaluated without selecting/tuning on
test results. Lower Brier is better; these are **one-match test diagnostics**.

| Training-only baseline | Test Brier | Material failure |
| --- | ---: | --- |
| Equal-match constant frequency | 0.013566882 | Single test match; cannot estimate between-match uncertainty |
| Period × owner score state | 0.013806637 | 104 unsupported-context test windows fall back to training prior |
| Fixed native endpoint location grid | 0.013746672 | Three zero-probability errors: infinite test log loss |
| Native forwardness bins | 0.013586707 | Worse Brier than constant |
| Native gain ≥5 | 0.013548284 | Tiny difference; no inferential support |
| Native gain ≥10 | 0.013557165 | Tiny difference; no inferential support |
| Native gain ≥15 | 0.013571878 | Worse Brier than constant |

Context and location also each have one impossible prediction in validation.
Infinite log loss remains explicit (JSON null plus nonzero infinite count),
without clipping or post-result smoothing. Calibration-bin support/mean forecast/
observed frequency and all validation/test failures are reported locally.
Training/test share both teams and 44 roster player IDs. There is no disjoint-team
claim, independent-cluster confidence interval or scientific validation. The
single-test-match interval is null. No ranking, player importance, practical
analyst usefulness or general progression-value claim follows from these numbers.
The blinded analyst study remains a design awaiting independent reviewers.

## Reproduction and evidence

From the repository root with the existing authorized config:

```sh
uv sync --frozen
uv run --frozen python scripts/build_worldcup_pilot.py \
  --config /absolute/local-config.json --pipeline-revision FULL_BRANCH_SHA \
  --acquire-pilot
```

`--acquire-pilot` verifies existing bundles on reuse and downloads only absent
approved pilot files. Omitting it performs offline reproduction from existing
raw files. There is no allow-unreviewed/ignore-quality/force-repair flag. The
command prints the actual corpus path, independent report path and blocked gate.
It retains canonical, scored, process eligibility, forecast and prediction files
with output hashes. Reusing a completed implementation run compares exact bytes;
corruption fails rather than being repaired. All artifacts remain under ignored
`data/raw/statsbomb-corpus/` and `data/interim/worldcup-delivery/`.

`/tmp/fil-worldcup-delivery.json` records the latest local delivery pointer.
`canonical_all_matches.parquet` includes blocked source rows;
`validated_score_events.parquet` has only validated matches. `process_audits.json`
retains censored/unresolved windows and original-ID chains, `forecast_rows.json`
contains eligible inputs, and baseline JSONs contain full local diagnostics/fit
state. They are not uploaded or committed. Original 8658 raw/derived/config inputs
retain all 23 previously recorded SHA-256 values and mtimes, verified after this run.

Validation completed: **406 tests pass** editable (9.50 s) and fresh regular
installation (13.55 s), no skips; `ruff check .`, `uv lock --check`, wheel and
source distribution builds pass. CI includes both installation modes and the new
module's installed CLI help. Source reconciliation and byte-identical rebuild
checks are additional real-data checks, not tests substituting for real evidence.
No UI changes were made and no new browser/performance claim is made; existing
startup and interaction limitations remain in the product review documentation.

Wyscout primary metadata/rights remain unverified and acquisition unapproved.
Current enforced environment policy still omits `api.figshare.com`; no destination
bypass/repeated denied request was attempted. No configuration-write tool is
available here. Owner environment action: add that exact host to resume the
original Figshare metadata audit, retaining all other restrictions.


## Later temporal and predictive-method review

See [forensic and evaluation review](TEMPORAL_REVIEW_DELIVERY.md). It preserves
this historical experiment and blocked acquisition gate, evaluates separate
conditional source-marker envelopes, and diagnoses the original rare-event and
censoring failures. No new matches or passing-gate claim follow from that review.
