# Critical analytics audit through PR #12

Scope: `1ec94984a76ac4db95ecc3d4ea73d1a800671fec`. A source/count/lineage test
establishes computational correctness, not football usefulness. **None of the
current indicators has independent evidence of incremental decision usefulness.**
Provider xG is an external model; FIL has not independently calibrated it here.
No new centrality, action-value, player-rating or hidden-connector model exists.

Classes: **descriptive** = an observed source statistic; **exploratory** = a
research definition/sensitivity or association; **validated** = independently
replicated for a specified use/population; **insufficient evidence** = the proposed
claim lacks necessary observations/validation. A metric can be descriptive while
its proposed player-quality interpretation has insufficient evidence. No indicator
below is classified as scientifically validated. Original contracts remain in
METRICS.md, TACTICS.md, POSSESSIONS.md and PLAYER_EVIDENCE.md.

## 1. Official score and shot goals

- Question: what was the recorded outcome and how did score state change?
- Measures: metadata score and period-aware, own-goal-aware source awards; shot goals separately.
- Assumptions/missing: provider scoring chronology, linked own-goal records; no counterfactual score.
- Cannot infer: deserved winner, expected quality of all attacks or individual ability.
- Class: descriptive; independently source-reconciled facts, not a validated quality indicator.
- Baseline: official metadata plus direct goal-event review.
- Usefulness evidence: trustworthy event/video alignment for context; not a new discovery.

## 2. Shot counts, source xG/NPxG, mean shot xG

- Question: how many recorded shots and how much provider-model probability did they accumulate?
- Measures: counts/sums/means of source probabilities; NPxG excludes penalties, own goals add no xG.
- Assumptions/missing: source model inputs/training/version/calibration not fully available; shot coverage selection.
- Cannot infer: true scoring probability of the match sum, deserved score, finishing skill, all attacking value.
- Class: descriptive aggregation of an external model; calibration here insufficient evidence.
- Baseline: shots, non-penalty shots and shot-location/type counts.
- Usefulness evidence: held-out calibration/discrimination by shot type/state and incremental analyst usefulness versus counts; include uncertainty and goalkeeper/defence context.

## 3. Cumulative xG and window threat / xG per minute

- Question: when did recorded shot production occur?
- Measures: source xG sums on event order or 5/10/15-minute period bins; rates divide by observed bin exposure.
- Assumptions/missing: uneven terminal bins, stoppages, rare shots, source-model limits; no tracking/control.
- Cannot infer: possession dominance, momentum, pressing effectiveness or causal tactical switches.
- Class: descriptive; the label "threat" is a shot-output summary, not xT.
- Baseline: shot-count timeline and constant rate per observed minute.
- Usefulness evidence: analyst timing tasks outperform those simpler views; sensitivity to bin width, penalties and stoppage handling; independent event review.

## 4. Completed/failed/unknown passes and completion fraction

- Question: which supported provider-recorded passes were completed?
- Measures: omission-of-outcome plus validated native pass/recipient contract; known completion denominator excludes and reports unknown cases.
- Assumptions/missing: provider-specific taxonomy and coverage; pressure, receiver options and pass difficulty unadjusted.
- Cannot infer: passing ability or risk-adjusted contribution from completion percentage.
- Class: descriptive; source semantics verified, player-quality interpretation insufficient evidence.
- Baseline: attempts and completions with explicit unknown counts, length/location/type mix.
- Usefulness evidence: held-out difficulty/context baseline and independent pass tagging; added value for a specified scouting/coaching decision.

## 5. Directed pair weights, sent/received counts, number of pairs

- Question: which recorded completed-pass connections occurred, and how frequently?
- Measures: unique original pass IDs per directed passer/recipient/team pair; volume-derived node counts.
- Assumptions/missing: unequal minutes/opportunities, substitutions, opponent/state/role, event sampling; sparse networks.
- Cannot infer: player importance, dependency, causal bottlenecks or effect of substituting a player.
- Class: descriptive network representation; connector interpretation exploratory/insufficient evidence.
- Baseline: total completed passes, per-player sent/received volume and degree without network interpretation.
- Usefulness evidence: reproducible out-of-match incremental information after exposure/role/state adjustment, expert review and alternative-route counterevidence. Display thresholds change only the drawing.

## 6. Event-average node positions, samples and ranges

- Question: where were a player's recorded completed-pass origins in this selection?
- Measures: arithmetic mean/range of valid origins, sample IDs/counts; recipients without origins stay unplaced.
- Assumptions/missing: successful-pass selection, provider coordinate frame, sparse/unequal exposure; no continuous location.
- Cannot infer: actual formation, occupation of space, physical ends, defensive coverage or off-ball movement.
- Class: descriptive conditional sample geometry.
- Baseline: actual origin dots, sample size, median and range.
- Usefulness evidence: legal independent tracking/video comparison for a precisely defined task and window; test centroid instability before tactical interpretation.

## 7. Progression v1 and distance gain

- Question: which supported moves advance toward the declared native target by at least ten units?
- Measures: completed passes/observed carries with positive native Δx and ≥10-unit Euclidean gain toward (120,40).
- Assumptions/missing: custom threshold, provider units (not metres), incomplete physical-direction certification, no pressure/options/retention evidence.
- Cannot infer: line breaks, xT, calibrated action value, beneficial decisions or causal contribution.
- Class: exploratory geometric proxy with reproducible descriptive counts.
- Baseline: completed-move volume, positive Δx, raw displacement; threshold 5/10/15 sensitivity is actually compared in the local case.
- Usefulness evidence: independently annotated progression purpose, held-out outcome/context comparison against forwardness/volume and stability across roles/providers; no same-match calibration claim.

## 8. Final-third and conventional box entries

- Question: which eligible endpoints cross declared native zone boundaries?
- Measures: start/end geometric tests, with source IDs and null classifications when geometry is unavailable.
- Assumptions/missing: fixed pitch frame/bounds, only observed endpoints, no defensive shape or continuous trajectory.
- Cannot infer: penetration of a defensive line, retained possession, advantage or expected goals created.
- Class: descriptive geometry; tactical effectiveness insufficient evidence.
- Baseline: starting zone and forward-move counts/lengths.
- Usefulness evidence: blinded source/video tagging, repeatability, endpoint missingness audit and incremental held-out value after starting-location adjustment.

## 9. Native possession IDs, membership and owner/context actions

- Question: what source records share the provider's possession identifier?
- Measures: source labels, ordered IDs and acting-team versus owner/context roles; opposition records retained.
- Assumptions/missing: provider segmentation; native ID 91 spans halves; gaps/restarts need not imply continuous control.
- Cannot infer: independently reconstructed ground-truth possession, uninterrupted control or tactical intent.
- Class: descriptive source grouping; segmentation validity beyond source conformity insufficient evidence.
- Baseline: provider labels and simple ordered action lists.
- Usefulness evidence: independent human boundary annotations, explicit disagreements and sensitivity to alternative defensible segmentations; preserve all records.

## 10. Entry/exit reasons, zones, counts and progression paths

- Question: how do native chains begin/end and traverse observed zones?
- Measures: first/last owner action, source restart tags, compressed observed zone sequence and eligible moving-action IDs.
- Assumptions/missing: recording gaps, native segmentation, no connectors between events/periods, no tracking.
- Cannot infer: a continuous route, run pattern, counterattack intent or defensive response.
- Class: descriptive process representation; pattern interpretation exploratory.
- Baseline: action-type/zone frequencies and original sequence review.
- Usefulness evidence: sequence models improve held-out analyst tasks/outcomes beyond unigram/length/starting-zone baselines, with segmentation and sequence-length sensitivity.

## 11. Conservative turnover and terminal categories

- Question: is a supported observed loss followed by an opposing owner under the declared exclusions?
- Measures: source loss plus same-period next owner, excluding restarts/fouls/out/boundaries/own goals and unresolved gaps; terminal evidence IDs retained.
- Assumptions/missing: native owner/ordering; conservative definition omits some true turnovers; 82 endings remain unresolved in the fixture.
- Cannot infer: all actual turnovers, player fault, defensive skill or transition quality.
- Class: exploratory operational label, source-supported; recall/precision not independently validated.
- Baseline: raw dispossessions, miscontrols and failed passes with next-owner labels.
- Usefulness evidence: independent open-play-turnover annotation, precision/recall including unresolved examples, and counterevidence under alternate loss/restart rules.

## 12. Process reach/shot/box conditional fractions

- Question: how often do the selected eligible native chains contain specified zone/shot features?
- Measures: P(contains shot | reaches final third), P(reaches box | reaches final third), explicit numerators/denominators.
- Assumptions/missing: native segmentation, start location, length/exposure, repeated players, selected chains and shot scarcity.
- Cannot infer: transition probabilities or that the shot/box entry occurred after the first final-third observation. Current `shot_after_final_third_*` keys are potentially misleading: implementation tests co-occurrence, not temporal order.
- Class: descriptive conditional co-occurrence; predictive/process-model interpretation insufficient evidence.
- Baseline: unconditional shot/box frequencies, starting zone and action count.
- Usefulness evidence: temporal event-order audit before any "after" claim, held-out baseline lift/calibration and segmentation sensitivity. Do not reuse these names as ordered labels.

## 13. xG per native possession and elapsed time to shot

- Question: what recorded shot output and conditional timing occur in these native groups?
- Measures: summed shot xG / eligible groups; median first-record-to-first-shot interval among same-period shot-producing chains.
- Assumptions/missing: duration includes stoppages/gaps; shot-only timing is selected on success and excludes unproductive chains/cross-period IDs.
- Cannot infer: live-ball speed, efficiency, latent possession value or population time-to-shot without censoring treatment.
- Class: descriptive; efficiency interpretation insufficient evidence.
- Baseline: shots per group, group length/start zone, unconditional durations with explicit censoring.
- Usefulness evidence: survival/censoring analysis and out-of-match/context comparison; show unsuccessful and missing-duration chains as counterevidence.

## 14. Player event, owner-action and native-possession involvement

- Question: which observed records/chains include this actor?
- Measures: actor records, declared owner-action taxonomy and distinct native IDs; actorless records remain outside player attribution.
- Assumptions/missing: passes/receipts are separate records, taxonomy/coverage differs, minutes and unobserved opportunities unavailable.
- Cannot infer: touches, work rate, off-ball contribution, importance or low effort from low counts.
- Class: descriptive participation.
- Baseline: counts by event type, team opportunity, native roster/census coverage.
- Usefulness evidence: independent exposure/role validation and repeated matches; demonstrate analyst retrieval usefulness beyond raw event counts.

## 15. Owner progression per 100 owner-action records

- Question: what fraction of this actor's selected owner-action records satisfy progression v1?
- Measures: 100 × qualifying owner progressions / owner-action count, including receipts and other taxonomy-dependent records.
- Assumptions/missing: not equal opportunity; denominator composition and successful-move selection vary by role/provider.
- Cannot infer: per-90 performance, risk-adjusted quality or superiority between roles/teams.
- Class: descriptive exposure conditional on recorded action taxonomy; quality interpretation insufficient evidence.
- Baseline: raw numerator/denominator and proportion per eligible completed pass/carry, with event-type mix.
- Usefulness evidence: denominator robustness, certified exposure, role/state/opponent adjustment and held-out incremental utility.

## 16. Pre-shot native-chain participation

- Question: which selected owner actions preceded a same-team/period shot in native index order?
- Measures: original eligible action IDs, contextual shot IDs and distinct chains; multiple participants can share a shot.
- Assumptions/missing: same native ID need not mean continuous control; threshold-free involvement is not allocated credit; context may lie outside filters.
- Cannot infer: causal chance creation, additive xG credit, necessity or unusual importance.
- Class: descriptive context association, connector interpretation exploratory.
- Baseline: all owner-action/complete-move volume and direct native shot links.
- Usefulness evidence: a reviewer gains relevant buildup clips not captured by final-pass lists; independent replication and adjusted holdout analysis needed before player claims.

## 17. Reciprocal native pass-to-shot links and linked source xG

- Question: which passes and shots are directly linked by reciprocal provider keys?
- Measures: same-team/period/index-consistent references, plus sum of source shot xG; unverified references remain audited.
- Assumptions/missing: provider tagging completeness and shot xG limits; shot may lie outside selected event type/window.
- Cannot infer: causal credit, an independently fitted xA model or all chance-creation participation.
- Class: descriptive source link; causal/ability interpretation insufficient evidence.
- Baseline: key-pass count and direct review of native references; distinguish goal-assist tags.
- Usefulness evidence: independent link annotation/completeness audit and precise retrieval/analyst utility, not merely successful joins.

## 18. H1/H2, windows and pre-event score-state comparisons

- Question: how do observed records differ between these selected contexts?
- Measures: the same descriptive metrics under period/time/acting-team score filters.
- Assumptions/missing: unequal elapsed exposure, substitutions, score state endogenous to play, role/opponent differences and selection bias.
- Cannot infer: tactical intervention effects, repeatable player skill or changes caused by score state.
- Class: descriptive stratification; explanations exploratory.
- Baseline: stratum counts/coverage and simple event-mix/exposure summaries.
- Usefulness evidence: repeated matches with support/overlap, adjusted context models, dependence-aware uncertainty and independent counterevidence.

## 19. Missingness, position metadata and recorded elapsed census

- Question: what source support is available for each denominator/interpretation?
- Measures: null/type/identity coverage, native role snapshots, source XI/substitution/off/on/card transitions and provisional interval durations.
- Assumptions/missing: recorded chronology differs from official minutes/live-ball time; snapshot roles are not continuously observed assignments.
- Cannot infer: missing means zero contribution, certified per-90 exposure, physical availability or inferred roles.
- Class: descriptive quality/exposure audit; official minutes and role-adjusted quality insufficient evidence.
- Baseline: roster, original boundary records and direct source review.
- Usefulness evidence: independent minute/role certification, complete transitions and endpoint reconciliation before denominators support comparisons. Current UI minutes remain null.

## 20. Proposed centrality, bottlenecks, xT/VAEP and hidden-player labels

- Question: can a method add decision-relevant information beyond volume/context?
- Measures: not implemented as validated indicators. Current pair counts/process summaries are not such models.
- Assumptions/missing: authorised multi-match corpus, action/direction contracts, suitable outcomes, pilot variance, independent review and holdout evidence.
- Cannot infer: player substitution effects from static node deletion, off-ball value or underrated/low-contribution rankings.
- Class: insufficient evidence; future hypotheses remain exploratory.
- Baseline: volume/forwardness, training-only frequency/context forecasts; any complex method must beat these on untouched matches and add practical utility.
- Usefulness evidence: the research protocol's leakage, calibration, dependence, negative-control, missingness, sensitivity, multiplicity and analyst-review gates. Strong arithmetic/predictive scores alone never pass.

## Actions from this audit

Use source maps/sequence evidence for retrieval and hypothesis formulation now.
Rename or explicitly qualify co-occurrence fields before claiming ordered process
transitions. Do not combine these statistics into an arbitrary rating. Compare
progression against volume/forwardness rather than its own implementation. Treat
the named-player case as an illustrative, potentially inconclusive analysis; no
population screen or independent football acceptance has occurred.
