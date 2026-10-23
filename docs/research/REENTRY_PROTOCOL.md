# Recorded retreat/re-entry study — fil-recorded-reentry-study-1

Freeze before new extraction. Parent PR #21 at
`68dbdfd81ceda1ccab042b94548525c65455829c`. All 64 current matches are development-
exposed. This is an exploratory source-record process study, not new forecasting
model fitting, an ability measure, a tactical-intent claim or independent replication.
Use only existing authorized local StatsBomb sources and unchanged metric eligibility.

## Scientific choice and rivals

Question: after a recorded entry into the upper native x-band, does an observed
retreat followed by re-entry describe recurring team processes beyond pass volume,
location and sequence opportunity, and is that information worth an analyst's time?
Player/context separation failed under the previous design; team possession processes
are a more defensible immediate unit. An observable sequence can still be trivial,
unstable, dependent on annotation, or unhelpful. A computationally correct pattern
does not establish a new football construct.

Competing explanations: (1) repeatable team process; (2) ordinary possession length
and completed-pass opportunity; (3) native position, score and opponent context;
(4) provider annotation density/geometry and arbitrary boundary placement; (5) an
order-sensitive representation that supplies no useful evidence beyond a ledger.
No claim of novelty versus all football literature. No pressure, intent, defensive
shape, available alternatives or unrecorded movement inferred.

## Units, observations and fixed landmark

One window at most per original native possession membership. Require contiguous
original records with one period (1–4) and one roster-valid owner. Preserve every
original ID/index, provider possession/team distinction, source manifest and score.
Keep all excluded memberships and event IDs with reasons. Penalty shootouts excluded.
No display filtering or grouping across period/native-ID gaps. No live timing claim.

Primary boundary x=80; recorded retreat endpoint <=75 (5 native units below).
Geometry must be finite within the original 120×80 domain. Completed Pass means
absent outcome key; explicit null/unknown is not completed. Carry uses its recorded
endpoint. These are provider units, not metres or physical attacking directions.
Do not flip coordinates. Call the band native upper-x, never certify physical final
third, physical continuity, purposeful recycling or official minutes.

First entry is the first owner completed Pass/Carry with start x<80 and endpoint
x>=80. Unknown geometry or unknown/failed owner Pass/Carry before that entry prevents
certifying the selected first entry and is an exclusion. Require source play_pattern
`Regular Play` or `From Counter` at entry; these are provider labels, not inferred
counterattacking intent. Record nonqualifying patterns rather than pooling restarts.

Landmark is the third subsequent owner Pass/Carry attempt in that membership.
For the primary comparison, each of those three must be a completed Pass or recorded
Carry with known valid geometry, and no owner Shot may occur from entry through
landmark. Short, interrupted, failed or unknown windows remain explicit exclusions,
not negatives. Both motif and comparator have the same three-action observation
opportunity. This deliberately conditions on survival to a landmark and selects a
subset of buildup; report that selection and never extrapolate to all possessions.

Feature uses only entry and these three actions. A retreat is a later recorded move
with start x>=80 and endpoint <=75. Re-entry must be a strictly later recorded move
with start x<80 and endpoint >=80. Different source indices, not positive elapsed
time, establish ordering. Preserve actual action records; gaps do not imply an
observed ball path. Report co-occurrence of retreat and re-entry separately from
retreat-before-re-entry. A failed move is not evidence of arrival. A missing move is
not filled from the next event. No actor is credited with a causal contribution.

## Outcomes and baseline comparisons, no model fitted

Primary description: source motif prevalence at the fixed landmark, all classifiable
windows including those with unresolved later outcomes. Then describe a strictly
later owner Shot in the first three subsequent owner **Pass/Carry/Shot records**
within that membership. Other annotations do not consume this horizon. Positive
requires a Shot in the observed horizon; negative requires three observed records
without a Shot, or verified source closure before that horizon completes. Otherwise
outcome=null. Closure is a next different non-null native ID in the same period, or
reciprocally linked opposing-team Half End markers following the segment; suspension/
early-video-end or unassigned intervening membership prevents a closed negative.
Neither label certifies complete physical/video coverage. Source xG remains original.

Also report any later recorded owner Shot before membership closure as a different,
variable-horizon observation. Do not conflate the two or tune the horizon to improve
an association. Own goals without Shot and shootouts are not Shot positives.

Comparators:

1. A searchable original event ledger with the same source information.
2. Completed-pass volume and landmark location: exact pass-prefix count bins
   0–2, 3–5, 6+; endpoint native 3×2 cell; Pass count among the three landmark actions.
3. The preceding strata plus own team-match, period and pre-landmark score state.

Report raw 2×2 outcome counts, nulls and worst-case missing-outcome bounds. Report
within-stratum motif/nonmotif outcome differences weighted by the smaller observed
arm count, retaining both arm sizes. Give equal eligible team-match summaries and
every match's evidence. This is retrospective descriptive adjustment, not a fitted
predictive/hierarchical/latent model, propensity adjustment or identified causal effect.
Strata with no arm overlap cannot support a conditional comparison; keep exclusions.
All-sample and matched-sample populations differ and must be shown. No iid-event tests,
ratings, p-values or convenient post-hoc matching/pooling.

For repeat support, use team-match motif fractions within period × score state ×
landmark lateral half. Compare absolute cross-match differences on shared strata,
requiring >=5 windows in each arm of the comparison. Separate same-team and different-
team pairs, and report teams/matches with no comparable support. Five is a sparsity
diagnostic, not sufficient sample size. Pair rows share teams/matches; do not count
them as independent observations or declare reliability from a favorable average.
Report the existing team/player dependency components; withhold population confidence
intervals where independence is unsupported. No independent out-of-corpus repeatability
claim can be made from this exposed tournament.

Frozen sensitivity variants: boundary75/drop5, boundary85/drop5, boundary80/drop10,
and boundary80/drop5 with Pass-only entry/landmark moves. Pass-only changes the source
observation unit and is not a universally preferable correction. Report eligibility
changes, paired feature disagreements and all outputs, not the best variant.

## Independent check, human evaluation and decision criteria

Independently re-extract raw memberships, landmark/feature/outcome IDs and geometry;
check score, original hashes and all numerical summaries with a separate implementation.
TEST_ONLY cases: order versus co-occurrence, same-event exclusion, failure/null,
missing geometry, first-entry selection, early Shot, three-record negative, short
closed negative, unclosed censoring, period boundaries and identity/protocol tampering.
Reproduce unchanged outputs without changing historical source/research artifacts.

Prepare source-only adjudication sheets, an empty judgment schema, anonymous task
IDs, ledger and sequence-card conditions, deterministic selection and counterbalanced
assignment. Select up to four motif, four comparable nonmotif and four unresolved/
excluded cases by SHA-256 of match/possession identity, never by later outcome, xG,
famous player or a persuasive example. This is a balanced feasibility set, not a
prevalence sample or independent football confirmation. Do not create labels, recruit
or contact participants automatically, publish provider material, or claim a human
experiment has occurred. No video permission is implied.

Independent adjudicators inspect raw source-only evidence without FIL classifications
to identify relevant/supporting/counterevidence actions and uncertainty. Analysts then
compare the same source information in a searchable ledger and a sequence-card view;
no analyst sees the same task twice. Record fixed-budget retrieval, defensible-answer
time, unsupported claims and decision relevance. Interface blinding is incomplete.
Keep task/analyst/match dependence and unresolved disagreements. The primary endpoint,
minimum worthwhile benefit and sample size must be ratified using independent analyst
input and a separate pilot before confirmatory evaluation; leaving these unresolved
blocks a success claim, not preparation of the packet.

Retain as a descriptive retrieval candidate only if source verification passes and
the ordered definition supplies inspectable evidence beyond aggregate counts.
Downgrade if definition/annotation sensitivity dominates, comparable support is sparse,
or the ledger already retrieves the same useful evidence with equal or lower burden.
Reject an effectiveness/ability interpretation if association disappears under the
predeclared opportunity/context comparison, reverses materially across variants or
cannot be distinguished from selection. No favorable descriptive association alone
promotes the descriptor. Independent human usefulness and untouched longitudinal
replication remain mandatory for a meaningful general football claim.

Provider-derived results and packets remain local/Git-ignored. Code/methodology only
may enter a stacked draft PR. Preserve previous PRs, frozen studies and merge guards.
