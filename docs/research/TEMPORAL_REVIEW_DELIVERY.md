# Temporal integrity and frozen predictive evaluation review

Parent: draft PR #15 at `6b159be796cce26745a7611a0604ac84dba6aaa3`.
**Recommendation: retain the BLOCKED expansion gate.** No additional matches were
acquired; no v1 clocks, original labels/probabilities, parent corpus or gate files
were changed. This is a proposed sensitivity contract and a scientific review,
not a new dashboard or a passing pilot declaration.

## 8656: observed evidence and limits

Every playing period has two consecutive opposing-team Half End records with
reciprocal `related_events`. Across the seven held matches, all 18 playing periods
have this paired representation: 14 pairs share timestamps, and the four unequal
pairs belong to 8656. This is evidence of multi-team representation in the held
records, not a provider-issued explanation of their timestamp differences.

| Period | Original indices / teams | Recorded end times | Spread | Last nonmarker record |
| --- | --- | --- | ---: | --- |
| 1 | 1470 England; 1471 Croatia | 46:10.433; 46:10.540 | 107 ms | 1469 Pressure at 46:09.073 |
| 2 | 3094 England; 3095 Croatia | 48:05.573; 48:05.733 | 160 ms | 3093 Pass at 48:02.493 |
| 3 | 3658 Croatia; 3659 England | 18:35.188; 18:35.468 | 280 ms | 3657 Pass at 18:34.015 |
| 4 | 4164 Croatia; 4165 England | 19:23.283; 19:23.323 | 40 ms | 4163 Player On at 19:22.723 |

The complete table of **exact original UUIDs**, native timestamps/teams/indices,
reciprocal links, raw neighboring events, all Half Starts, source goals and all
substitution/Off/On records is generated locally as `REVIEW.md` and `forensic.json`.
Those provider-derived evidence files remain Git-ignored, not attached to the PR.
`/tmp/fil-temporal-review.json` points to the latest local review bundle.

Half Starts are paired at native zero: indices 3/4, 1472/1473, 3096/3097 and
3660/3661. Provider order and within-period timestamp order are consistent.
Every nonmarker start and every supplied duration completion precedes the
respective earliest end marker. No goal, substitution or census transition sits
between the conflicting end markers. The final Player On record precedes the
conditional fourth-period end by 560–600 ms; this is source-clock sensitivity,
not certified physical return-to-play timing.

Source-order score after each period is Croatia–England 0–1, 1–1, 1–1, 2–1.
Eight substitutions and two paired temporary Off/On episodes are preserved.
The extra-time substitution at native period-3 zero follows the Half Start records
in provider order; no positive elapsed time or physical half-time ordering is
inferred. Original roster joins/census transitions are consistent in the review.
The source's 4,165 records, 33 shots and known match-play xG 2.6879835335 do not
require choosing an end marker. The raw score reconciles with match metadata.

### Authoritative source/version review

Both held PDFs are verified against their pinned upstream file identities:

- [StatsBomb specification v1.1](https://github.com/hudl/open-data/blob/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/doc/StatsBomb%20Open%20Data%20Specification%20v1.1.pdf),
  SHA-256 `d5a8267939c5db35a9501b1a272cc9861a2bb3bef2f53c723d4a43ec1f5ef477`.
  Pages 8/23/44/45 distinguish collection method, Half End, new flags and version history.
- [Open Events v4.0.0](https://github.com/hudl/open-data/blob/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/doc/Open%20Data%20Events%20v4.0.0.pdf),
  SHA-256 `05de42cc76b0c9cd26213d8e5c72610cac7d4d92c9c2ac878073a565dbb6c44a`.
  Its timestamp definition specifies storage to the millisecond; Half End signals
  a period-ending whistle. It provides no rule certifying the later marker.

8656 metadata says collection-method version **1.0.2**, not JSON-format version
4.0.0. The specification's 1.0.2 changelog says only “Bug fixes and QA improvements”.
Video-truncation/suspension flags are listed as additions in 1.1. Their absence
here cannot establish complete video. Carry records are present despite the older
collection label; no undocumented conversion or enrichment history is inferred.

An upstream issue search for the exact phrase Half End found no matching issues;
a broader timestamp search found unrelated reports. No applicable maintainer
explanation was established. This limited search is not proof no explanation exists.
The 40–280 ms differences cannot be accounted for by ordinary rounding of one
instant to 1 ms. Annotation offsets, video alignment and the physical whistle's
location relative to the markers remain unestablished; none is asserted as cause.

## Proposed uncertainty contract and verification

[Method contract](TEMPORAL_REVIEW_METHOD.md), version
`fil-period-envelope-proposal-1`, is implemented independently of CLOCK_SCHEMA/v1.
It never selects max/min as the true end, rewrites timestamps, or rounds conflicts.

| Result class | What is established | Limitation |
| --- | --- | --- |
| Boundary-independent source facts | Original identity/order, native periods, goals/score, shot xG, recorded substitutions and Off/On evidence | Source facts, not physical-time certification |
| Invariant under every declared scenario | All nonmarker records and supplied duration completions precede the earliest marker; recorded transition ordering and score are unchanged | Applies to the reviewed scenario set and source clock |
| Conditional sensitivity results | Per-player recorded-census exposure ranges; event-phase offsets excluding breaks | Assumes each end is inside its marker envelope; not provider-certified bounds |
| Still unresolved | Exact physical end, official minutes, physical availability/exposure, wall/video alignment | Remain null; no per90 or exact-time claim |

Summed scenario endpoints are **7,934,477–7,935,064 ms**, a 587 ms spread.
This is not a confidence interval or an asserted enclosure of the true match
length. Independent code enumerates all 16 endpoint combinations and integrates
player intervals using a different algorithm. It reproduces every lower/upper
exposure result. The affine dependence on period ends establishes interior
scenario extrema at the endpoints; it does not establish the physical assumption.
Official minutes stay null and per90 eligibility stays false. Shared-prefix
uncertainty in event-phase offsets is correlated, not independent clock noise.

### Can the gate safely change?

An unqualified PASS is **not justified** by the evidence or by small spreads.
The sensitivity calculation is reproducible, but physical containment and old
collection-version boundary accuracy have not been established. Do not substitute
an arbitrary tolerance or the later marker for this missing evidence.

A future, explicitly accepted **metric-specific** gate could distinguish native
source/order facts from conditional interval outputs and unavailable exact-time
outputs. The proposed contract is concrete for review, but no gate implementation
or acceptance flag is changed here. Under the current owner condition, all six
pilot gates must pass; 8656 remains blocked and the remaining 57 stay unacquired.
Provider clarification or another authorized independent temporal reference could
support a future revision. No unlicensed video acquisition/contact is performed.

## Frozen experiment diagnosis

The original predeclared experiment, bins, splits and probabilities are unchanged.
The local audit lists every bin's raw/positive counts, match support, weighted
training probability, validation/test counts and signed Brier excess; every zero
error retains cutoff/shot UUIDs and source-manifest lineage.

| Match | Original partition | Eligible windows | Positive windows | Prevalence | Distinct linked shots |
| --- | --- | ---: | ---: | ---: | ---: |
| 8649 | train | 1,019 | 12 | 1.1776% | 10 |
| 8650 | train | 1,131 | 21 | 1.8568% | 16 |
| 8651 | validation | 1,073 | 17 | 1.5843% | 10 |
| 8652 | validation | 1,219 | 14 | 1.1485% | 11 |
| 8655 | test | 1,236 | 17 | 1.3754% | 13 |

These windows overlap and reuse shot labels. They are not thousands of independent
football trials. Training/test share both teams and 44 roster IDs. The fixed
constant prior is about 1.5172%; its test rate is 1.3754%. There is one test match,
so between-match test uncertainty remains unestimable, not a narrow iid interval.
Calibration arrays retain support counts and both constant/candidate diagnostics.

**Context:** first-half leading has 197 training windows and zero positives,
causing one zero-probability error in validation. It has no test-window errors
because that context is absent from test. Second-half level is unsupported in
training; 104 test windows (one positive) fall back to the prior. The worse test
Brier instead comes mainly from second-half trailing (forecast 3.0517%, observed
3/361) and leading (forecast 0.2098%, observed 5/119): two-match conditional
frequencies transfer poorly on this one test match. That is observed failure,
not a statistically established universal failure of score-state features.

**Location:** bins `1:1`, `2:1` and `4:0` have 95, 178 and 145 training windows
respectively, with zero positives; each receives one positive test label.
`4:0` also causes one validation error. These empirical zeros produce three test
and one validation infinite-log-loss errors, preserved without clipping.
Brier degradation also comes from overprediction in sparse endpoint bins:
`5:2` forecasts 17.9271% on seven negative test windows, and `5:0` forecasts
10.1351% on 19 negative windows. Signed bin contributions reconcile to the full
reported Brier difference; improvements in other bins offset part of these losses.
Bin codes refer to the fixed native 6×4 grid, not certified physical directions.

### Selection, missingness and football usefulness

The audit retains all 5,678 eligible and 1,701 censored/unresolved windows. Among
censored cutoffs, **189** have an observed shot within the remaining fewer-than-five
owner records. These are cutoffs, not 189 distinct shots. They remain unlabelled
in the original experiment; they are not negative labels. Their exclusion selects
against some terminal shot-producing actions, even when source records are complete.
Full selection strata and endpoint missingness are reported by match and reason.

The five-record horizon spans **0.639–39.760 native-clock seconds** across eligible
records, with per-match medians around 4.9–5.8 seconds. The taxonomy counts passes,
receipts and carries separately and excludes some context types. It is sensitive
to provider annotation density and is not five independent touches, five seconds,
shot quality or possession value. Native clocks may include stoppages.

This target is useful as a precisely reproducible engineering/ledger diagnostic;
its coaching or analyst value is **unvalidated**. A future primary question should
be chosen with analysts before evaluation, for example source-supported shot-ending
possession retrieval from a declared cutoff, with explicit terminal/period rules,
all-cutoff eligibility and comparison with a simple event ledger. A fixed-time
forecast would additionally require source availability and boundary/censoring
contracts. None replaces the historical target or is evaluated on the consumed test.

### Separate development-only shrinkage freeze

The grid, weighting, objective and tie rule were committed before fitting, in the
method document. Four complete-match leave-one-out folds use only 8649/8650/8651/
8652. Alpha is measured in match-equivalent weighted mass. The selected values are
**context: 4; location: 0.25**. All grid losses and the exact development-input hash
are frozen locally. Selection scores are not independent validation estimates.
No new model is scored on 8655 or 8658; 8655 is not untouched confirmation again.
Fresh confirmation requires genuinely new independent matches, currently unavailable
under the blocked gate. No xT/VAEP, player ratings or discovery claims are made.

## Reproduction, tests and decisions

```sh
uv run --frozen python -m fil.research.integrity_review \
  --delivery /absolute/pr15-delivery-pointer.json --pipeline-revision FULL_BRANCH_SHA
uv run --frozen python scripts/verify_temporal_review.py \
  /absolute/new-review-bundle /absolute/original-local-config.json
```

The latest local pointer is `/tmp/fil-temporal-review.json`. Full forensic Markdown,
source neighborhoods, bin support, zero-error evidence, calibration, censoring and
separate development freeze remain under ignored `data/interim/temporal-review/`.
Parent corpus/run/source/quality files are hash-protected before/after review;
reusing a run compares exact output bytes. Independent verification repeats PR15's
complete source reconciliation in addition to 16-scenario and baseline-audit checks.

417 tests pass editable (7.88 s) and fresh regular installation (9.77 s); lint,
frozen lock validation, wheel and source-distribution builds pass. Tests cover
linked/unlinked/missing boundaries, truncated video, regressing periods/clocks,
boundary-zone events, sub-millisecond duration overlap, census contradictions,
native canonical timestamps and strict development/test isolation. No UI or new
performance claim is made. All data-rights/merge/deployment restrictions remain.

The proposed contract remains unaccepted; there is no request to override the
existing expansion block. The only immediate environment action needed is adding
**`api.figshare.com`** to the managed environment's outbound allowlist, keeping
all other restrictions. Current observations show the policy enforced and that
host absent; no bypass/repeated denied request was attempted. No configuration
write tool is available here. Wyscout metadata/licensing and acquisition remain
unverified/unapproved; additional hosts are not requested speculatively.
