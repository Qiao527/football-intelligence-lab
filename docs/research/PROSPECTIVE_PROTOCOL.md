# Prospective research contract — fil-recorded-possession-study-1

Status: frozen design before new label construction; not acquisition approval,
not analyst acceptance, not empirical validation. Parent is draft PR #16 at
`b204ada492c09ad36e6552f3f7097967bb15e129`. All seven already inspected matches
(8649, 8650, 8651, 8652, 8655, 8656, 8658) are development-exposed for this study.
Preserve every earlier experiment and its labels, scores and artifacts.

## Estimands and observation rules

Primary: **a strictly later recorded owner Shot before observed native possession
segment closure**, after observing a complete owner completed-pass/Carry record.
Use the entire source array before display filtering. Retain all eligible cutoffs;
do not require five future annotations. Provider possession IDs are not certified
physical possessions. Contiguous single-period, single-owner memberships only;
reused/noncontiguous IDs and ambiguous order/ownership are unresolved. Equal
timestamps retain provider index order and imply no positive physical duration.

Closure evidence is the next non-null different provider possession ID in the
same period, or a linked opposing-team Half End pair after the segment. An
unassigned intervening record, period change without those markers, suspension,
early-video-end or malformed markers prevents certified negative labels. A later
owner Shot in an unambiguous ordered segment confirms a **recorded positive**
even if the later boundary is unavailable. A shot on the cutoff is excluded.
Absent a later Shot, only a verified closure confirms a **recorded negative**;
otherwise outcome=null, with unresolved/censored reason and observed evidence.
Neither negative nor positive certifies complete real-world video coverage.

Secondary descriptive evidence: all later owner Shot IDs, their provider xG,
known xG sum and missing-xG count; a total is null if any shot lacks xG. For
unclosed positive segments, these are observed lower-coverage shot evidence, not
complete terminal chance totals. Shot-ending retrieval means *a segment with a
later Shot*, not that Shot is necessarily the last annotation or a goal. Do not
infer assist, tactical intent, causal credit or a provider-independent chance.
Own goals without a Shot are not Shot positives. Shootouts are excluded. A fixed
physical-time target is blocked without clock/availability certification.

Alternative comparison, not a replacement: old next-five-owner-record target
remains frozen. It counts provider annotations, includes overlapping cutoffs,
censors known short positive tails and spans variable source-clock durations.
Primary closure-based retrieval removes that five-record selection but has a
variable horizon and provider-specific segmentation bias. Chance-generation
evidence (Shot IDs/provider xG) distinguishes observed attempts and their modelled
quality; it is not a new trained value model or interchangeable across providers.

## Features, weighting and baselines

Retrospective record-order forecast only: features may use original fields at or
before cutoff index, in its source/match/period. No future possession totals,
terminal flags, future shot/xG, IDs, final score, future roster membership or
test-derived missingness normalization. Fit preprocessing and bins on training
only. Feature-generation code and explicit lineage receive an independent audit.

Primary estimand: choose a match uniformly, then a labelled possession uniformly,
then a cutoff uniformly in that possession. Weight each cutoff
`1/(number of labelled possessions in match * labelled cutoffs in possession)`.
Report equal-match and all-cutoff sensitivity, unresolved fraction by stratum,
distinct Shot and possession counts, effective cluster support and calibration.
Positives and negatives have asymmetric observation requirements: report both
and worst-case missing-label prevalence bounds, never missing-as-zero. No MAR
assumption or inverse-censoring weights without separate justification.

Compare a training-only constant prior; period × cutoff pre-event score state;
fixed native endpoint 6×4 location grid; native positive gain and 5/10/15-unit
progression rules as transparent alternatives. Native +x is not physical direction.
For bin frequencies use `p=(s+alpha*pi)/(n+alpha)`, n/s in match-weighted mass.
Grid alpha={0.25,0.5,1,2,4}; select by complete-match forward validation Brier,
tie toward larger alpha. Use training-only Jeffreys regularization of the prior
in match units `(weighted positives+0.5)/(training matches+1)` to avoid hard
0/1 from rare outcomes; state its small-sample bias. Missing/unseen bins use that
prior. No tuning from final test. This specification does not reuse the previous
target's fitted alpha as a validated parameter for the redesigned target.

## Holdout and uncertainty

No evaluation on newly acquired matches is authorized now. Conditional on a future
accepted acquisition policy, freeze the exact source hashes/IDs and partition
manifest **before opening their event/lineup payloads**. For the presently proposed
57 additional World Cup matches only: date <=2018-06-26 train, 2018-06-27 through
2018-07-01 validation, >=2018-07-02 test. Remove all seven exposed matches from
every confirmatory partition, including fitting. Same-day fixtures stay together;
entire source/match membership and all its possession windows stay together.
Earlier date plans remain historical. Any future scope outside those 57 needs a
new frozen contract; never substitute a convenient split after seeing outcomes.

This is a retrospective temporal holdout within one men's tournament, not a
prospective calendar trial or unseen-team generalization. Log exposure to hashes,
labels, plots and test summaries. No blind-test claim if any candidate was inspected
before freeze. Unsupported or empty partitions stop evaluation, not prompt a split
change. Quality eligibility is outcome-blind, metric-specific and frozen first;
publish exclusion counts without reallocating failures across partitions.

Primary: paired equal-match possession-weighted Brier difference from constant;
also report absolute Brier, reference Brier, relative skill with null for zero
denominator, log loss without concealed clipping, reliability in fixed deciles,
precision/recall and unique-shot retrieval. Do not interpret tiny Brier gains on
rare outcomes as usefulness. No success declaration without independent analyst
utility, adequate support and robustness to dependence/selection.

Keep every match/possession window together for resampling. Report paired match
bootstrap (10,000 draws, seed=1729) as a conditional sensitivity, not an independence
guarantee. Audit repeated team/player IDs; report connected components of matches
sharing either team or player across all partitions. Component-cluster intervals
are withheld if fewer than two components; a tournament may have one. Report
leave-one-team-out match-exclusion sensitivity and per-match effects; it is not
an unseen-team test. One test match has no between-match interval. More generally,
wide/unstable intervals or too few independent positive clusters mean inconclusive.
Do not replace dependency components with artificially independent player rows.
Choose meaningful effects/sample-size planning with analysts and independent pilot
variance before final evaluation; no arbitrary match-count adequacy claim.

## Independent football analyst task — not yet run

Question: does a tool help retrieve relevant recorded buildup evidence beyond a
simple chronological event ledger? Independent football analysts choose tasks and
minimum worthwhile changes in retrieval/time/claim error before the study. No Pogba
case or exposed match supplies confirmatory tasks. Recruit reviewers who did not
write FIL or its labels; qualifications and conflicts disclosed.

Use identical source information and event drilldown in FIL and a simple searchable
event ledger. Randomize tool order in a crossover design, counterbalance tasks,
and keep each analyst from seeing the same match/task twice. Hide tool names and
research hypothesis where practical; interface blinding is incomplete and reported.
Before tool assignment, separate adjudicators create relevant/counterevidence ID
sets and uncertainty rubric from authorized raw records. Do not derive gold labels
from FIL output. Disagreements remain documented/adjudicated, not majority truth.

Tasks: retrieve buildup preceding recorded Shots; compare two declared source-order
phases; provide evidence for/against a proposed connection without attributing
causal importance. Record recall/precision at a fixed 10-event review budget,
unique-shot coverage, time to defensible answer, unsupported claims per claim,
uncertainty disclosure and blinded decision-relevance ratings. Return reasons for
false positives, missing counterexamples and uncertain cases. Analyse paired
analyst/task differences with analyst and match dependence, report all tasks and
failure cases; predeclare primary endpoint/effect and multiple secondary endpoints.
No analyst experiment is claimed complete and no rights to video/publication are
inferred. All provider-derived evidence, results and weights remain local/ignored.
