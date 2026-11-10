# Off-ball space: exploratory technical core

**Question.** Can a movement be used to find a defensible candidate for a support option? The current implementation measures changes in observed geometry; it does not prove tactical usefulness, player intent, passing feasibility, or causality.

**Prior work.** [Martens et al. (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8322620/) model spatial control and distinguish different meanings of space generation. [Fernández et al.](https://www.barcainnovationhub.fcbarcelona.com/wp-content/uploads/2024/03/The-right-place-at-the-right-time.pdf) study off-ball advantages with tracking and observed on-ball events. These works motivate contextual spatial analysis, not a claim that our simple segment geometry measures their models or produces the same results.

**Current method.** For an unreviewed candidate, `movement_candidate` checks five detected focus-player samples over two seconds, consistent source timestamps and provider possession, and one provider in-play phase. If displacement is at least 3 m, `support_change` compares the ball-to-player distance and the shortest distance from each detected opposing player to the ball-to-player segment at the two endpoints. Both endpoints must have a detected ball, carrier, focus player and every active opponent, with the same active opponent identities. Source IDs, period, frame IDs and timestamps must match the movement record. Missing coverage abstains; positions are never interpolated. The thresholds are illustrative and not calibrated.

**Interpretation.** An increase in segment clearance only describes a geometric change between two snapshots. The ball, defenders and teammates may all have moved; the measured player cannot be credited with causing the change. Static line clearance does not account for defender reach, ball speed, passing angle, interception, off-screen observations, or whether an option is tactically sensible. Endpoint comparisons miss intermediate changes.

**Actual feasibility result.** Using the pinned SkillCorner data and the existing ten preselected frames in match `1874553`, the 18 player-frame pairs yielded four movement candidates and 14 pairs for which geometry was not evaluated. All four candidate pairs abstained because opponent positions were incomplete. Thus **zero complete two-endpoint comparisons were available in this small selected sample**. Full results and raw frame references are in ignored local `data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/1874553/support-change-feasibility.json`; this is not a representative coverage estimate.

Reproduce locally with:

```sh
.venv/bin/python scripts/evaluate_support_change.py \
  data/raw/skillcorner/4340d274572876239c154c90bc507a9b3250a656/1874553 \
  data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/1874553/source-manifest.json \
  data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/1874553/video-review-queue.json \
  --output data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/1874553/support-change-feasibility.json
```

**Validation needed.** Sample both rule hits and misses across separate matches and roles; record exact eligible and abstained denominators, reasons and overlapping-window dependence. Independently blinded football reviewers should label whether the player offers a usable option and provide counter-evidence, with `not visible` permitted. Compare against a movement-only baseline and report precision, recall, abstention and reviewer disagreement on held-out matches. Provider passing-option labels are model outputs and may be used only as a secondary, imperfect comparison—not independent ground truth. Without independently labeled observations, tactical value and ML improvement remain unproven.

**Important label-leakage correction.** The provider's [dynamic event specification](https://26560301.fs1.hubspotusercontent-eu1.net/hubfs/26560301/Guides/Dynamic%20Events/20250216%20-%20Dynamic%20Events%20CSV%20Specifications.pdf) says a passing-option event is created for a pass target even when its receiver-model score is below threshold. Therefore the previous passing-option overlaps are retrospective same-provider agreement only; they are not an independent outcome or validation of a pre-pass prediction. The prospective analysis below does not use `passing_option` event labels as features or as its outcome.

## Fixed-interval coverage survey

`scripts/survey_space_coverage.py` rechecks raw hashes against each match manifest and includes only matches with a matching WARN source-quality report. Match `1953632` remains excluded. Every source frame divisible by 600 (at the provider's stated 10 Hz) is sampled; the focus population is detected teammates of the provider's identified carrier at that frame, excluding the carrier. This is a fixed, nonrandom sample conditioned on center-frame detection and possession. It includes pauses and unavailable possession; it does not estimate accuracy, player ability, or the distribution of all off-ball movements.

Actual result across **19 matches**: 1,986 sampled frames; 1,667 did not have both usable provider possession and period, and 319 supplied an eligible center-frame target list. These 319 frames yielded 2,003 target-player observations: 150 movement candidates, 143 not meeting the rule, and 1,710 insufficient-data results. Of the 150 movement candidates, **zero** permitted a strict before/after comparison: 83 lacked complete detected opponent positions and 67 lacked the provider `playing_time.sequences` information required by our current lineup gate. Inspection found those latter matches provide `by_period` intervals, but their equivalence to uninterrupted active-player sequences has not been established; this survey does not infer it. These are counts for the selected sample, not a tactical success rate.

Full match-level counts, per-observation outcomes and source hashes stay local in ignored `data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/space-coverage-survey.json`. Reproduce with:

```sh
.venv/bin/python scripts/survey_space_coverage.py \
  data/raw/skillcorner/4340d274572876239c154c90bc507a9b3250a656 \
  data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656 \
  --output data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/space-coverage-survey.json
```

## Interval cross-check and weak-label review

`scripts/audit_skillcorner_intervals.py` compares original `sequences` and `by_period` boundaries in the 19 WARN matches, after rechecking the match metadata hashes. Among 359 player records with both fields, all 529 sequence rows matched a period row and all 529 period rows matched a sequence row; all 359 player-level sets matched. Another 324 player records did not provide `sequences`. This sample agreement does not establish whether a `by_period` interval can safely represent uninterrupted presence, substitutions, or temporary absences. No automatic fallback was added. Full audit: ignored `data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/interval-audit.json`.

`scripts/compare_provider_labels.py` joins the fixed-time survey to original provider `off_ball_run` and `passing_option` IDs by match, player, period and inclusive overlap with the sampled two-second interval. Inclusive overlap is a working assumption, not a verified provider boundary specification. Among 150 rule candidates, 61 overlap one or both provider label types; among 143 rule non-candidates, 49 overlap one or both; among 1,710 abstentions, 474 overlap one or both. These are pair counts for the sampled, possession- and detection-conditioned population. No overlap is not a confirmed negative; provider model output is not independent ground truth; no precision, recall, tactical value or generalization is established.

The script reproducibly selects 16 review pairs (four each from rule candidate/non-candidate crossed with provider overlap/no overlap; 12 matches, random seed 2401, at least 600 source frames between selected windows from the same match). It creates local, ignored per-match `blind-review-queue.json` files and keeps individual model outputs in the separate ignored `provider-comparison-private.json`. In Space Replay choose **Unlabelled review** to view them without the rule verdict or provider labels, then locally save Yes / No / Not observable, a pseudonym and supporting or contradictory notes. The review app hides the geometric candidate line in this mode. Reviewers know the selection process and view the same provider tracking that generated the labels, so this is limited masking—not independent video validation or a blind generalization study. No human assessments were generated by the script.

Reproduce interval and provider checks with:

```sh
.venv/bin/python scripts/audit_skillcorner_intervals.py data/raw/skillcorner/4340d274572876239c154c90bc507a9b3250a656 data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656 --output data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/interval-audit.json
.venv/bin/python scripts/compare_provider_labels.py data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/space-coverage-survey.json data/raw/skillcorner/4340d274572876239c154c90bc507a9b3250a656 data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656 --output data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/provider-comparison-private.json
```

## Automated passing-line observations

`scripts/inspect_review_lanes.py` examines the 16 masked-review pairs without reading their hidden rule or provider labels. For each pair it checks five original tracking samples at 0.5-second intervals, ending at the selected frame. It uses detected ball, carrier and target positions and detected opponent positions only; it requires the ball to be within an illustrative 3.5 m of the provider-identified carrier. For each frame it measures ball-to-target distance and the nearest detected opponent's distance to the finite segment; a 2 m proximity threshold is illustrative, not a calibrated interception model. Absent or extrapolated players are not treated as observed. Source hashes, player IDs, period, frame IDs and original timestamps are retained locally.

Result: at the selected frame, 7 of 16 pairs had a detected opponent within 2 m of the segment, 8 had none detected within 2 m, and one had insufficient data. Across all 80 sampled frames, 63 were measurable by this partial-observation definition and 17 abstained. Eleven pairs had five measurable samples, while five had at least one missing sample. These are deliberately selected cases, not a population, model-accuracy or tactical-value estimate. No opponent detected near the line is not proof that a pass is open.

For a concrete source-traceable counterexample, match `1996435`, player ID `42513`, frame `46800`: over source timestamps `01:16:15.00`–`01:16:17.00`, ball-to-player distance changed from 12.4 m to 10.5 m, while the nearest *detected* opponent to the ball-to-player segment changed from 3.6 m to 1.1 m. Eleven opponent positions were detected at each of those sampled frames, but this does not independently establish complete coverage or an interception. The example illustrates why a short pass distance or player movement alone does not establish a usable option.

These measurements are not a player's field of view. Player facing direction, gaze, defender reach, passing height, ball velocity and out-of-frame positions are unavailable or uncertified here. They cannot establish whether the carrier saw the teammate, whether the pass was possible, or whether the run helped the team. Full outputs stay in ignored `data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/review-lane-observations.json`.

## Temporal ordering and response research

The temporal screen requires five consecutive 2 Hz observations, consistent timestamps, the same provider-identified carrier and target, the same detected-opponent identity set, and one matching provider in-play phase. It reports the change in nearest *detected* opponent distance to the ball-to-target segment. A stable detected set does not mean that all opponents were observed, and changing ball or defender positions can produce a clearance change independently of the target's movement.

As an exploratory cue, if the measured nearest-detected-opponent distance crosses from above 2 m to at most 2 m, the screen records the first later sampled time at which the target is at least 1 m from its position at that cue. Thresholds are illustrative; ball, target and defenders all affect the cue. If no later sample exists, the result explicitly says so. If no threshold is reached during available follow-up, this is censored observation, not proof of no response. Sampling is every 0.5 seconds, so the method cannot resolve movement onset between samples. This timing is **not reaction time** and does not prove perception, decision-making, intention or causation.

In the selected 16 pairs, seven met this temporal screen and nine abstained (five missing measurable observations, four changing detected-opponent sets). Of those seven, five had no threshold crossing, one had a crossing followed by an observed 1 m displacement in the sampled remainder, and one crossed at the last sample with no follow-up available. This tiny, selected set does not establish a football pattern or player quality.

## Match-separated exploratory baseline comparison

`scripts/evaluate_space_baselines.py` rechecks source hashes and samples every 100 source frames (nominally 10 seconds at 10 Hz) in the 19 WARN matches. It considers detected teammates at center frames with provider-identified possession, using the preceding five 2 Hz samples. There are 11,866 sampled frames; 9,902 lacked usable provider possession or period, and 1,964 supplied a usable center. Those centers yielded 12,098 player-window pairs. The fixed sample is not representative of all play, and repeated players, possessions and matches are dependent.

The split was assigned by sorted match ID before this run: first 14 matches for development and last five for comparison. These matches were previously inspected, so the comparison is not a blind generalization test. The development split had 9,579 pairs, of which 544 were comparable for both rules; the comparison split had 2,519 pairs, of which 135 were comparable. The remaining 11,419 pairs abstained from at least one rule, mostly due to missing/inconsistent provider possession, unclear phase, changing detected opponents, or missing measurements. Exact reasons and raw rows are retained in the local report.

Both rules are measured on the **same comparable pairs**: (A) the existing ≥3 m movement rule; (B) rule A plus a ≥1 m increase in nearest *detected* defender distance to the ball-to-player segment. The second rule is a subset of the first and cannot discover a movement that rule A missed. Unlike the earlier strict full-opponent experiment, this screen uses the same observed opponent set in all five samples and does **not** establish complete opponent coverage; an unobserved opponent may be closer. The same-provider `off_ball_run` and `passing_option` overlaps are derived labels, joined by same match, player, period and inclusive interval overlap; neither a match nor a non-match is independent ground truth.

| Split | Comparable pairs | Movement candidates | Spatial subset | Movement candidates with run / option overlap | Spatial subset with run / option overlap |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development, 14 matches | 544 | 325 | 67 | 34 / 113 | 14 / 26 |
| Comparison, 5 matches | 135 | 77 | 18 | 5 / 22 | 0 / 5 |

Run and option overlaps can apply to the same pair and must not be summed. At thresholds 0.5 / 1 / 2 m, the spatial subset changed from 91 / 67 / 31 pairs in development and 29 / 18 / 6 in comparison. At 1 m, spatial pairs appeared in all 19 matches, but counts by provider's metadata role group varied, including zero wide-attacker pairs in the five-match comparison set. Provider metadata role is not a validated in-game role. These counts show threshold and sample sensitivity; they do not establish accuracy, improvement, causality or lack of value. There is no independently labeled outcome, no confidence interval, and no statistical independence. **The experiment does not demonstrate that the spatial rule improves scouting.**

Reproduce; the per-pair IDs, original timestamps, source event references, abstention reasons, per-match and provider-role breakdowns stay in ignored local data:

```sh
.venv/bin/python scripts/evaluate_space_baselines.py data/raw/skillcorner/4340d274572876239c154c90bc507a9b3250a656 data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656 --output data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/space-baselines-exploratory.json
```

## Independent position hypothesis

The position rule no longer requires ≥3 m player displacement. Within the same five detected, same-carrier and same-phase samples described above, at least three must place the player 8–25 m from the detected ball and at least 2 m from every **detected** opponent to the finite ball-to-player segment. These cutoffs are illustrative, not calibrated. Stable detection is not complete coverage; this is not a confirmed passing option or an assessment of football intelligence. The rule is evaluated only on the same 679 movement-and-space-comparable pairs, so it does not recover pairs where the movement data itself was insufficient.

In the 544 comparable development pairs, the position rule selected 230, including **110** that did not reach the movement-only ≥3 m threshold. Of these 110, 54 overlapped a same-provider passing-option label. In the 135 comparable five-match comparison pairs, the position rule selected 55, including **19** below the movement threshold; 12 of those 19 overlapped a provider passing-option label. These are player-window pairs, not distinct players; the reference is model-generated, shares source data, and has no independently validated negatives. Counts do not establish recall, tactical accuracy, ability or improvement.

Post-hoc sensitivity to requiring 2 / 3 / 4 / 5 qualifying samples: the below-movement-threshold counts were 118 / 110 / 101 / 92 in development and 20 / 19 / 16 / 15 in the comparison split. This checks threshold fragility rather than choosing an optimal value; the previously inspected comparison matches are not blind holdout evidence.

One source-traceable example from match `2011166`, player ID `157294`, period 1, frame `9200` (`00:11:30.00`): the observed two-second start-to-end player displacement was 0.87 m. All five samples met the position rule; ball-to-player distances were 14.9, 12.5, 11.0, 10.2 and 9.7 m, and nearest detected opponent-to-segment distances were 3.0, 3.1, 2.6, 2.6 and 2.6 m. A provider passing-option event overlaps the window. This does not prove that the actual pass was possible, that the player caused the changing space, or that the player was underrated.

The below-threshold cases can be inspected locally: select **Low-movement positions** in Space Replay. The app rechecks source hashes and the rule before showing the case; it shows a hypothesis, not a validated assessment. For browsing, the queue contains the first qualifying case and, if different, the first provider-passing-option-overlap case per match; it is deliberately selected and cannot be used to estimate model performance. Reproduce the report and replay queue with:

```sh
.venv/bin/python scripts/evaluate_space_baselines.py data/raw/skillcorner/4340d274572876239c154c90bc507a9b3250a656 data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656 --output data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/independent-position-exploratory.json
.venv/bin/python scripts/prepare_position_cases.py data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/independent-position-exploratory.json data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656
```

## Subsequent carrier pass and receiver action: exploratory association

`scripts/evaluate_future_actions.py` uses the pre-existing position and movement rules on the same match-separated, 10-second-grid cohort. It recomputes each included feature from hash-verified source tracking before reading the later outcome. For a fixed snapshot it groups comparable teammates by the position rule, then retains snapshots with both groups and a unique provider-recorded current carrier possession that ends **after** the snapshot and within 30 source frames (nominally three seconds). The possession-end match flag, same-period original frame/timestamp consistency, known pass target and known provider pass outcome are required. The target must be in the comparable teammate cohort. Missing, ambiguous, other-action, outside-horizon and outside-cohort cases remain separate, not negatives.

The later pass is a same-provider tracking/event-derived record, not independent video truth. The provider's first subsequent possession within 50 frames corroborates a reception only when it identifies the targeted player, same team, `pass_reception`, and a matched previous pass; source frame and clock must agree. The receiver's subsequent action is separately recorded only if its possession end is matched, known and within 50 frames of reception. This ordering does not prove why the pass happened, that the option caused it, or that the action improved winning chances. Provider phase and possession classifications can themselves use retrospective context.

Of 115 unique snapshots with at least one comparable teammate, **48** met all pass-and-cohort conditions: 40 from 13 development matches and eight from three comparison matches. These are selected snapshots with an identified subsequent target, not all possessions. In development, the target was in the position group in 32 of 40 snapshots; those snapshots contained 122 position-group and 144 comparison-group player exposures. In the comparison subset the target was in the position group in six of eight snapshots, with 16 and 28 exposures. All 48 provider passes were labelled successful and all 48 had a same-provider corroborating reception. Among the 38 receptions to position-group targets, 33 subsequent possessions ended with a provider-recorded successful pass within the specified window, one with an unsuccessful pass, and four were unconfirmed. Among the 10 control-group receptions, eight ended with a successful pass, one with an unsuccessful pass and one with a possession loss. These follow-up counts are conditional on reception and cannot establish a quality or causal difference.

For a same-snapshot comparison, assign the target group `1 / number of players in that group` and the other group zero, then subtract control-group rate from position-group rate and average over snapshots. The observed difference was +0.246 in the 40 development snapshots and +0.375 in the eight comparison snapshots. On the smaller subset where both the position and movement-only rules have both groups in the **same snapshot**, the position-vs-movement differences were +0.145 in development (30 snapshots, match-cluster bootstrap 95% percentile interval approximately +0.001 to +0.303 over 2,000 draws) and +0.360 in comparison (eight snapshots, only three matches; interval withheld). These are exploratory association summaries, not model accuracy or causal effects; the comparison matches were previously inspected and are not a blind holdout. The bootstrap reflects match resampling only, not selection bias, measurement error, model-label dependence or multiple experimentation.

Post-hoc sensitivity checks changing required qualifying samples from 3/5 to 2/5, 4/5 and 5/5 preserved a positive observed position-group difference in the small selected subsets, but sample membership changes. Restricting both groups to 8–25 m at the center produced 28 development and five comparison snapshots; the paired position-vs-movement difference was +0.224 in 18 development snapshots (match-cluster interval approximately −0.103 to +0.580) and +1.167 in three comparison snapshots (no interval). The latter is extremely sparse, and this restriction does not adjust for player role, angle, pressure, pass intent or all other confounders. These checks do not validate the rule.

Independent raw-file reverse lookup checked all 48 selected pass event IDs and all 48 reception event IDs; 44 receiver-ending actions were also checked against original provider rows, with zero mismatches in IDs, player identity, match, period and frame ordering. This establishes reproducible provenance and consistency, not independent real-world event accuracy.

Example: match `2015213`, period 1, frame `7600` at `00:08:59.00`, had two position-group and five control-group comparable teammates. Provider event `8_117` ended at frame `7614` (`00:09:00.40`) with a successful pass targeted to player `159946`, who was in the position group. The first subsequent provider possession `8_118` began at frame `7627` (`00:09:01.70`) for the same player, with `pass_reception` and matching flags. This demonstrates a traceable recorded sequence, not proof of contribution or intent.

Reproduce the main result and distance sensitivity; all per-snapshot identities, raw event IDs, source hashes, outcome flags and unresolved cases remain in ignored local data:

```sh
.venv/bin/python scripts/evaluate_future_actions.py data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/independent-position-exploratory.json data/raw/skillcorner/4340d274572876239c154c90bc507a9b3250a656 data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656 --output data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/future-action-exploratory.json
.venv/bin/python scripts/evaluate_future_actions.py data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/independent-position-exploratory.json data/raw/skillcorner/4340d274572876239c154c90bc507a9b3250a656 data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656 --restrict-distance --output data/interim/skillcorner/4340d274572876239c154c90bc507a9b3250a656/future-action-distance-sensitivity.json
```
