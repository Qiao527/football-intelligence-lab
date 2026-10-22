# Approved pilot execution and frozen diagnostic protocol

Parent PR #14: `90ba21dd22e30f842aee11891d6fb3069c435696`.
Source/rights scope is exactly the later owner authorization in SOURCE_POLICY.md.
Acquisition code uses the immutable proposal hash, verifies Git blob identity and
SHA-256, and permits expansion only with all six pilot quality reports passing.
No arbitrary URL/allow-unreviewed option is supported.

## Quality failure policy declared before predictive evaluation

Material failures: byte/identity/count mismatch; unknown match/team/player joins;
ambiguous/missing/short period boundaries, nonmonotone clocks; unreconciled
match-play score; out-of-domain on-ball geometry; unresolved lineup census;
or unsupported possession/source contracts. Preserve every source and canonical
record, retain null uncertainty, block affected downstream outputs. Unknown event
types are retained/reported; they are not automatically dropped or assimilated.
Physical attacking directions and official minutes remain unverified for all
matches, so physical-direction, per90 and role/importance analyses are excluded.

Pilot observations before prediction: 8656 has two distinct Half End timestamps
in each of periods 1–4. Existing clock validation rejects this, starting in period
1. Original StatsBomb specification v1.1 describes Half End as the referee whistle
ending a period (held local `data/interim/spatial-docs/spec.txt`, p23); it does not
supply a rule that certifies which of these disagreeing timestamps is correct.
Do not choose max, average, overwrite source times or relax the clock gate to
claim a complete pilot. The other five pilot matches pass current quality checks.
Expansion to the other 57 is blocked by the owner's explicit all-pilot-pass gate.
Keep 8656's raw/canonical events in the audit corpus, not clock/score/process models.
The final source report must list all boundary disagreements, not just first error.

## Pilot-only diagnostic forecasting experiment, frozen before fitting

The full-corpus date protocol (train through 2018-06-26, validation through
2018-07-01) remains unexecuted because expansion is blocked. This separate,
versioned pilot diagnostic is not a substitute for that study or an adequacy claim.
Its purpose is to demonstrate genuine real-match fit/test separation and expose
baseline failure cases on the validated pilot subset.

- Training: eligible new pilot matches dated through 2018-07-06 (8649, 8650).
- Validation: eligible new pilot matches dated 2018-07-07 (8651, 8652).
- Test: eligible new pilot matches after 2018-07-07 (8655; 8656 is quality-blocked).
- Match 8658 is excluded from all partitions, fitting and model selection because
  it is development-exposed. Same-day fixtures remain together. Complete matches
  stay disjoint. Quality-screened pilot records are not claimed to be an untouched
  external confirmation corpus. Do not change the split after predictive results.
- Target/cutoff/eligibility: PR14's unchanged
  `fil-next-five-owner-actions-shot-1`. Forecast after observing the complete
  source record of a completed pass/observed carry. Exactly five strictly later
  owner records in the same possession/period; short/unresolved windows are null.
  Retrospective record-order forecast, not certified live availability time.
- Baselines: training-only inverse-within-match weighted constant frequency;
  period × pre-event score-state frequencies; native endpoint fixed 6×4 location
  grid; native forwardness bins ≤0/(0,5]/(5,10]/>10; binary native gain thresholds
  5/10/15. Missing geometry has no invented value and falls back to training prior.
  These native +x alternatives do not certify physical attacking direction.
- No tuning/selection of thresholds, bins, feature set, probability smoothing or
  calibration from validation/test. All predeclared comparisons are reported,
  including negative improvements, zero-support fallbacks and infinite log loss.
- Feature lineage uses cutoff-record fields only, including original start/end
  coordinates and score before the action. Labels are in a separate strict future
  evidence list. Do not use future possession totals, terminal score/xG or IDs as
  predictors. Expose test-team/player overlap with training.
- Equal-match Brier/log loss; fixed-bin reliability with explicitly reported
  weighting/support; paired match-cluster uncertainty. One test match has **no
  between-match interval**. Treat every result as a technical pilot diagnostic,
  not calibrated scientific validation or football usefulness.
- No xT/VAEP, external AI, player rating, causal claim or trained-weight release.
  Model fit-state and labels remain ignored locally. Analyst study remains pending.
