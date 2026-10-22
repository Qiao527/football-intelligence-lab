# Temporal uncertainty and baseline audit protocol — proposed, not accepted

Parent PR #15: `6b159be796cce26745a7611a0604ac84dba6aaa3`.
No acquisition, gate reclassification, v1 clock replacement or original experiment
change is authorized by this research review. The expansion gate stays BLOCKED.

## Proposed contract: fil-period-envelope-proposal-1

Retain every source timestamp, ID and index. Identify exactly two reciprocal,
opposing-team Half Start records at native zero and two reciprocal Half End
records per supported period. Reject incomplete/video-truncated/suspended,
nonconsecutive/reversing or unlinked evidence. The observed earliest/latest end
markers define a **conditional sensitivity scenario**, not a confidence interval
or a provider-certified enclosure of the physical whistle. The match's metadata
version (8656: 1.0.2) must not be conflated with the available documentation
versions (2019 specification 1.1 and Open Events 4.0.0).

Under the explicit hypothesis that each end lies within its marker envelope:

- Keep raw record identity/order, native-period membership, goals, xG, starts,
  substitutions and provider-defined possession IDs as source facts. No physical
  off-ball or causal inference is licensed by this model.
- Test all nonmarker starts and known-duration completions against the earliest
  boundary. Report any events on/inside/after the envelope; do not silently move
  them. Unknown event durations never become certified completion times.
- Integrate source census exposure as lower/upper milliseconds, with complete
  source transition evidence. Official minutes/per90 remain null/false. Pair
  temporary Off/On; validate substitutions/cards against original rosters.
- Propagate native event-phase offsets by summing period envelopes; these exclude
  half-time breaks and are not wall/video clocks. Shared prefix uncertainty is
  correlated: it cancels for same-period differences, and must not be counted
  twice when comparing two records.
- Enumerate all endpoint scenarios independently. For affine census duration,
  endpoint extrema bound every interior scenario. This statement is conditional
  on the envelope hypothesis, not evidence that the physical end lies inside it.

No automatic promotion to a production clock or a passing corpus gate. A future
metric-specific gate would require explicit acceptance of this contract, original
version support/provider clarification, independent validation, and separate
handling of exact-time/exposure claims. The current unqualified gate stays blocked.

## Frozen original experiment audit

Read/hash PR15 artifacts; do not regenerate or change its labels, bins, split,
probabilities, smoothing, calibration or reported test match. Audit match-level
prevalence, raw and inverse-match training support per location/score-state bin,
every zero-probability error with cutoff and shot evidence, calibration support,
missingness, overlapping labels, censoring and train/test roster dependence.
A censored short chain containing an observed shot is not a labelled negative;
its omission may select against terminal actions. Counts are not independent
Bernoulli trials, and one test match has no between-match confidence interval.

## Optional new shrinkage proposal: development-only freeze

Before fitting, fix development matches to 8649/8650/8651/8652 (original train +
validation); reject 8655 and 8658. For each context/location family, perform four
complete-match leave-one-out development folds. Inner training weights are
1 / eligible rows in that training match. Let s_b and n_b be weighted positive
and total mass in bin b and pi the inner-training equal-match prior.

`p_b = (s_b + alpha*pi) / (n_b + alpha)`.

Choose alpha from `{0.25, 0.5, 1, 2, 4}` **match-equivalent mass units**, minimizing
mean held-development-match Brier. Break exact ties in favor of larger alpha.
Unseen/missing bins fall back to inner-training prior. Refit hyperparameters only
on those four development matches after selection; do not evaluate new proposals
on 8655 or describe it as untouched again. Do not claim four development folds
establish adequacy or calibration. Freeze chosen parameters/input hashes locally;
new confirmation requires genuinely new independent matches, presently unavailable
under the blocked expansion gate. No xT/VAEP, ratings or model-weight publication.
