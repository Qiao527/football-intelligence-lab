# Scouting decision task — fil-scouting-decision-task-1

Frozen design **before** any candidate-set construction or outcome inspection. Parent
`fb1b4a9`; branch `research/fil-013-scouting-decision-protocol`. This is not a
ranking, not a player-ability label, not analyst acceptance, not a data-acquisition
approval and not a `DEL-*` gate. No result in this document is empirical.

## Scientific choice and rivals

Question: on the existing 64-match corpus, does a pre-declared information set let a
decision-maker shortlist attackers with better *recorded later* chance evidence than a
conventional goals/shots table, and can any observed difference be attributed to that
information rather than to presentation, noise or selection?

This replaces "find undervalued forwards" with a measurable decision analogue. A
budget-constrained recruitment task requires club, contract, market-value and
multi-season data that this corpus does not contain; the transfer framing is out of
scope and must not be reintroduced by wording.

Rivals, all retained until evidence separates them:

1. The conventional table is already sufficient; source xG adds no usable increment.
2. Any apparent gain is sampling noise: per-player opportunity counts in one
   tournament are too small for the ranking to be stable.
3. Gains come from presentation or persuasion (order, vivid evidence, volume) rather
   than from information content.
4. Differences are produced by role, team strength or opponent context that neither
   condition supplies, so the comparison does not isolate the metric.
5. The shortlist task is not decision-relevant: success on it need not transfer to a
   real scouting decision.

No novelty claim against scouting or sports-analytics literature is made, and no
latent ability, causal effect, market inefficiency or transfer recommendation is
identified by this design.

## Units and the decision task

Corpus: the 64 accepted StatsBomb 2018 World Cup matches, **all development-exposed**
(see `ACCEPTED_CORPUS_DELIVERY.md`, `REENTRY_PROTOCOL.md`). Only existing authorized
local sources; no new match, provider or video material.

- Identity unit: `(player_id, team_id)` from provider records. Provider identity only;
  no cross-provider or external identity linkage is claimed.
- Recorded appearance: a match in which at least one original record names the player
  as actor. A roster member with no records is *unobserved*, never zero exposure. An
  unused substitute is therefore indistinguishable from a non-selection; this is
  reported, not repaired.
- Exposure denominators: recorded appearances and owner-action counts only.
  `minutes_played` is null and `per90_eligible` is false throughout the corpus, so no
  per-90, per-minute or availability quantity may be computed, implied or displayed.
- Position: original lineup position metadata and its intervals, reported verbatim.
  No role or attacker status is inferred from event averages, shot volume or heat
  positions. Players with several recorded positions keep all of them.
- Penalties and shootouts: shootout records excluded; penalty shots reported as a
  declared inclusion/exclusion pair, never silently merged.
- Own goals are not shots and add no shot xG.

Decision task: given a candidate list, an information condition and a fixed review
budget, produce an ordered top-*k* shortlist with, for each selected player, the
original event IDs relied on. *k* and the budget are fixed in the analysis manifest
before outputs are generated.

## Windows, candidate universe and criterion

Windows are per team, by that team's chronological group-stage matchday, never by a
global calendar bucket.

- Primary observation window: each team's group matchdays 1–2.
- Primary criterion window: that team's group matchday 3.
- Secondary criterion window: knockout matches, reported separately and labelled as
  survivor-selected, because only 16 teams supply criterion records there.

Primary criterion variables, fixed and few: recorded shot count, source xG, source
non-penalty xG in the criterion window, each per recorded appearance, plus the binary
"at least one recorded shot". Criterion values are source facts; no generated xG, xT
or chance-quality model is introduced.

Candidate universe: players with at least one recorded appearance in the observation
window and a provider position label recorded in the observation window. Primary
inclusion is one appearance; a two-appearance sensitivity is declared in advance.
Candidate counts are reported as observed facts and are not used to retune inclusion.

Exclusions retained with reasons: no observation-window appearance, no provider
position label, identity conflicts, malformed or missing xG on an otherwise included
shot (a hard failure for that player, not a zero), and cross-period or duplicate
identity anomalies. Unresolved criterion values stay null with a reason and are
excluded from scoring, never treated as zero.

## Information conditions

Arms differ only in pre-specified numeric and evidence fields. An identical
limitations panel — no minutes, no tracking, no injury or availability data, provider
xG only, one tournament, survivor selection in the knockout window — appears in every
condition so that the comparison is not confounded with disclosure.

- C0 conventional: appearances, goals, shots, position label, team.
- C1 source xG: C0 plus source xG, non-penalty xG, xG per shot and xG per appearance.
- C2 source xG with context: C1 plus native shot locations, shot body part, play
  pattern and pre-shot score state, each with original event IDs.

C2 is a package condition. Any claim about which element supplies the increment
requires a further factorised arm and is not available from C2 alone.

## Reliability audit — executes before any shortlist is scored

Purpose: decide whether an attack-shortlist study on this corpus is measurable at all.
No player ranking is published from this stage.

- Test–retest correlation between each player's first and second observation-window
  appearance, for shots, xG and non-penalty xG per appearance. Under parallel
  measurements this estimates the reliability of a **single** appearance; it is
  reported as `r_single` and is the value later applied to the one-appearance
  criterion window.
- Only players with two observation-window appearances contribute a pair, so `r_single`
  is estimated on a regular-starter subgroup while the gate is applied to the whole
  candidate universe. That subgroup plausibly has more stable opportunity, so the
  estimate is expected to be optimistic. The subgroup size and its composition are
  reported, and the direction of this bias is stated wherever the gate result is used.
- Spearman–Brown correction of the same split gives the reliability of the
  two-appearance composite, reported as `r_obs`. This is the reliability of the
  ranking input and is the value the gate below tests. The uncorrected value is never
  reported alone.
- Within/between-player variance summary for the same quantities from raw moments, no
  fitted latent or hierarchical model.
- Cluster bootstrap resampling players (10,000 draws, fixed seed declared in the
  manifest) for `r_single`, `r_obs` and for the difference in reliability between xG
  and goals.

Declared decision rule, frozen here and not adjustable after outputs are seen:

- Proceed only if `r_obs` for xG per appearance has a point estimate of at least 0.50
  and a bootstrap lower bound of at least 0.30, and if xG reliability is not lower than
  goals reliability by more than 0.10.
- Otherwise the conclusion is that this corpus cannot support a stable attack
  shortlist; the deliverable becomes the data requirement specification below, and no
  suitability, undervaluation or scouting claim is issued.
- Wide intervals with a point estimate near the threshold are reported as
  inconclusive, not as passing.

Reliability is a property of the observation window, not evidence of ability.

## Criterion-window reliability and the measurement ceiling

The criterion window supplies one appearance per player, so it has no internal split.
Its reliability is therefore estimated, not measured:

- `r_crit := r_single`. The single-appearance estimate from the observation window is
  carried over, which assumes the two windows are exchangeable in measurement quality.
  This assumption is stated, not verified, and is expected to be optimistic: MD3
  rotation, dead rubbers and differing stakes plausibly lower it.
- Report MD3 recorded-appearance rate, shot count and xG summaries grouped by each
  team's qualification status known before MD3 (points from MD1–2, a factual
  classification, not an outcome). A large between-group difference is reported as
  evidence against the exchangeability assumption.
- Criterion availability: a player with no MD3 recorded appearance has a null
  criterion, never zero. The scored population is the intersection of the fixed
  candidate universe and criterion availability, reported with its size before any
  scoring. No arm may be scored on a different population, and no redefinition of the
  universe after availability is known is permitted.
- Measurement ceiling, from classical test theory: the maximum observable correlation
  between the two-appearance ranking input and the one-appearance criterion is
  `C = sqrt(r_obs * r_crit)` for an underlying true-score correlation at most one.
  `C` is reported on its own, before any arm is scored, and accompanies every reported
  rank correlation. An observed association materially above `C` is evidence that the
  reliability model is wrong; it is reported as a model failure, not as a strong result.
- Ceiling gate, frozen here: if `C < 0.45`, the increment test is declared
  **uninformative in advance**. The study reports the reliability estimates, the
  ceiling, and stops. Results are not later reinterpreted as absence of an effect,
  because the design cannot distinguish absence from attenuation.

## Increment test, conditional on passing both gates

- Rank construction is deterministic and pre-declared, identically in every arm:
  per-appearance rates shrunk toward the positional-group mean with a fixed
  appearances-equivalent prior of 10. Arm sensitivity at 0, 5 and 20 is reported;
  the prior is never selected on criterion performance.
- Primary endpoint: difference in Spearman rank correlation with the criterion
  quantity between C2 and C0, over the fixed candidate universe.
- Secondary: top-*k* precision, and Brier score for the binary criterion under each
  arm's implied ordering, reported with calibration in fixed bins.
- Uncertainty: player-cluster bootstrap; connected components of players sharing a
  team reported; leave-one-team-out sensitivity reported as sensitivity, not as an
  unseen-team test.
- Reporting: every Δ is reported with `C`, the interval and the scored population size.
  A small positive point estimate with a wide interval is not usefulness, and multiple
  secondary endpoints are all reported with no endpoint selection after the fact.
- Pre-declared classification of a zero-spanning interval, fixed before outputs:
  1. `C < 0.45` → **uninformative**: attenuation dominates, and the result is not
     evidence of absence.
  2. `C >= 0.45` and the bootstrap half-width is at most the pre-declared minimum
     worthwhile difference → **no detectable increment** at that difference.
  3. otherwise → **inconclusive**, with the achieved half-width reported so the reader
     can see what the design could have detected.
  These three labels are exhaustive and are not interchangeable in later write-ups.

No model is fitted, no hyperparameter is tuned on the criterion window, and the
criterion is never used to choose bins, priors, *k* or the candidate universe.

## Human analyst task — designed, not run

No analyst has been recruited, contacted or observed. No human result is claimed,
estimated or simulated.

- Participants: at least two analysts who did not write FIL or this protocol,
  qualifications and conflicts disclosed. The project owner may not be the sole
  analyst; a single-analyst run is an instrument pilot and cannot support a success
  claim.
- Design: within-subject crossover over conditions with randomized, counterbalanced
  order; no analyst sees the same candidate set twice; tool and condition names
  hidden where practical; incomplete blinding reported.
- Materials: the same searchable original event ledger in every arm, plus the
  condition-specific evidence view and the shared limitations panel. Analysts see
  evidence and limitations, never a FIL score, label or rank.
- Gold evidence: independent adjudicators construct relevant and counterevidence event
  ID sets from raw source records before seeing FIL output. Disagreements are
  documented and adjudicated; no majority vote is called truth, and no gold set is
  derived from FIL output.
- Primary endpoint: evidence identification accuracy (precision and recall at a fixed
  10-event review budget) against the adjudicated sets. Scored endpoints are evidence
  quality, time to a defensible answer, unsupported claims per claim, and stated
  confidence calibration. Choice agreement with an adjudicated "correct shortlist" is
  **not** a primary endpoint: no such ground truth exists, and treating one as truth
  converts a judgment into a score.
- Secondary: shortlist stability across re-presentation, change-of-opinion log with
  stated reasons, and decision-relevance ratings.
- Power and the minimum worthwhile effect must be ratified with external analyst input
  and a separate pilot before any confirmatory run. Until then every human result is
  exploratory.

## Decision criteria and stop rules

1. Reliability gate fails → stop the ranking task; publish the data requirement
   specification and the negative measurement result.
2. Reliability passes but `C < 0.45` → stop as **uninformative before scoring**;
   report `r_single`, `r_obs`, `r_crit` and `C`. No absence-of-increment claim is
   permitted.
3. Both gates pass and the increment interval spans zero with half-width at most the
   minimum worthwhile difference → report **no detectable increment**; do not ship a
   ranking product.
4. Both gates pass and the interval spans zero with a wider half-width → report
   **inconclusive**, with the achieved half-width, and do not describe the result as
   absence of an effect.
5. Increment positive and robust to prior, *k*, candidate threshold and
   leave-one-team-out → prepare the analyst pilot packet with pre-registered
   endpoints. No product label, no ability claim.
6. Any stage where the only support comes from a single team, a single player or a
   famous fixture is reported as unsupported.

Every outcome above is a valid deliverable. A negative result is measurement evidence
and is not to be reframed as a partial success.

## Required data for a confirmatory version

Specified in [SCOUTING_DATA_REQUIREMENTS.md](SCOUTING_DATA_REQUIREMENTS.md): eight
requirements, their blocking status, the five-appearance arithmetic behind the
reliability ceiling, and the acceptance checks any future corpus must pass. That
document is a requirements specification, not an acquisition request.

## Non-claims, exposure and rights

No ability, potential, value, injury risk, causal effect or transfer recommendation is
produced. No physical direction, tracking, pressure, available options or intent is
inferred. All provider-derived records, candidate lists and outputs stay local and
Git-ignored. Every stage logs which hashes, candidate lists, criterion values and
plots were inspected, in order, so that a later reader can tell exploratory from
confirmatory work. No provider material is published or redistributed.

## Owner decisions

Ratified by the project owner on 2026-11-11 in the FIL conversation:

- reliability thresholds 0.50 point, 0.30 lower bound, 0.10 comparative margin —
  accepted unchanged;
- measurement-ceiling threshold 0.45 and minimum worthwhile difference 0.10 —
  accepted unchanged;
- `r_crit := r_single` exchangeability — accepted, together with its stated
  optimistic direction and the required matchday-3 heterogeneity check.

Still open, and blocking execution rather than design:

- *k*, the review budget and the primary criterion quantity;
- whether minute certification is in scope, since its absence blocks every
  per-90 framing;
- whether an untouched corpus will be requested at all; without it this remains
  exploratory.

## Implementation status

Stage A (candidate universe, test–retest reliability, ceiling and both gates) is
implemented in `src/fil/research/scouting_task.py` with 23 tests in
`tests/test_scouting_decision.py`. It emits a decision only: no player is ranked, no
criterion is scored and no ability label is produced.

The appearance exporter is implemented in `src/fil/research/scouting_appearances.py`
with 15 tests in `tests/test_scouting_appearances.py`. It converts canonical events,
lineup position metadata and match metadata into the row contract, excludes
shootouts, splits penalty and non-penalty xG, refuses missing source xG and blocks
unattributed shots unless the caller explicitly reports and excludes them.

Neither module had been executed on the corpus at design time. The corpus was then
re-fetched from the pinned public revision under owner authorization (126 files,
191,244,134 bytes, verified by size and upstream git blob SHA-1), and stage A was run
once: `r_single(xG) = 0.360 [0.255, 0.486]`, `r_obs = 0.529`, ceiling `0.436 < 0.45`,
so the study **stops at the ceiling gate** before any increment test. Full record,
including the thin margin: [SCOUTING_STAGE_A_RESULT.md](SCOUTING_STAGE_A_RESULT.md).
The matchday-3 heterogeneity check that tests the borrowed criterion assumption is
reported in [SCOUTING_MD3_CHECK.md](SCOUTING_MD3_CHECK.md); it does not change the
decision.

The re-fetch is a byte-level re-fetch, not a renewed acceptance: the original pilot
reports, gate and batch proofs are lost, and no such claim is made.

