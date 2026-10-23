# Outcome-free player comparison design audit v1

Parent PR #20 at `a6d098a19b613670dae25ec2a3e125446238ff29`.
Freeze before executing new descriptive extraction. All current data is exposed.
This is an outcome-free structural audit, not model fitting, prediction, ability
estimation, causal inference or an independent confirmatory study.

## Question and competing explanations

Can the observed corpus support player contrasts once arbitrary observed team/match
context is allowed? Is apparent lack of common support mainly caused by selecting
completed-pass chains, or does it persist for the broader recorded pass-attempt
sample? Does adding last-observed native position evidence improve comparability
or instead isolate players? Are supported comparisons repeated across matches?

A positive result would be observed within-context overlap and repeated comparison
support, not identified ability. Counterevidence includes disconnected design blocks,
contrasts coupled to team context, concentration in one match, and lost support when
roles/context are specified. More event rows need not repair missing crossed design.
Do not assume which result will occur or dismiss all event-data research from one
additive design diagnostic.

## Units and selection audit

Preserve every original source event ID. Three populations:

1. All original Pass records in periods 1–4 with an actor joining to the original
   team roster. Recipient, pass completion, geometry and receipt are not prerequisites.
   Unknown/missing outcome is retained as an annotation, not treated as success/failure.
   This is recorded action selection, not all physically available passing choices.
2. The existing roster-verified completed passes (exact parent inclusion rules).
3. Existing eligible two-pass chain intermediary releases (exact original chain IDs).

Use B's release pass start for chain context, harmonizing the actor-opportunity unit
with the other populations. This deliberately differs from the previous audit's
first-pass-origin context; do not compare support as if definitions were unchanged.
For every record retain match/team/player/opponent, original index/period/score state,
native start coordinate/cell, and latest Starting XI/Tactical Shift position
annotation at/before that release. Its ID/index is evidence; it is not a continuous
role or certified exposure. Unknown position/coordinate remains null. Never infer
physical direction, off-ball action, decision intent, tracking or minutes/per90.

## Design algebra, no fitted response

For each population audit the two-indicator design X with a player column and one
context column per observation, for these four context partitions:

- Own team.
- Own team × match (opponent is fixed within a team-match).
- Own team × match × period × pre-release score state × native start cell.
- The preceding partition plus last-observed native position ID, restricted to
  known positions. Missing geometry is excluded only from cell-dependent graphs.

Observed columns only; roster players with no relevant records are reported separately.
This is a specified additive mean design, not a fitted statistical/latent model.
Each row has two 1s. Its bipartite graph has V observed columns and C connected
components; exact rank is V−C and nullity C over the reals/rationals. A null vector
sets player columns to +1 and context columns to −1 inside one component. It changes
cross-component player contrasts without changing any row sum. Within-component
contrasts are algebraically estimable only under the stated additive assumptions;
this establishes neither causal effects, measurement validity nor adequate precision.
No response, success rate, player coefficient, prior or rating is fitted or emitted.

Report player/context vertices, unique edges, repeated observations, component
memberships, nullspace witness pattern, exact rank, pairwise contrast counts
within/across components, and dropped/unobserved support. Duplicating every existing
row preserves this rank; it adds no new crossed support. A minimum of C−1 component-
merging links is a connectivity lower bound, not C−1 matches/transfers or a sufficient
sample/causal design. No hypothetical link is inserted into production evidence.
This is distinct from the existing match dependence graph (which links opponents).

## Direct and repeated comparable support

Retain every player-context edge's original IDs and counts. For cell-dependent
partitions, enumerate same-context player pairs and their per-player counts. Report
nominal shared support; support with both players having >=5 observed opportunities
in a shared cell; distinct shared-match counts; and pairs with that >=5 support
in at least two matches. These are predeclared sparsity diagnostics, not adequacy
thresholds or valid inferential sample sizes. Keep unequal opportunities and missing
roles explicit. Summarize all players; do not select a star or rank individuals.

Distinguish direct shared-context support from indirect graph paths. Add whole-match
leave-one-out support diagnostics for the team-match design: retain the originally
observed player universe, identify players losing all observations and within-original-
component contrasts no longer connected. Removing a match can remove its participants;
do not silently drop those players to make stability appear better. No bootstrap,
p-values, iid-event uncertainty or independent confirmation is justified.

## Independent verification and falsification

Re-extract from raw source with a separate implementation; check every record and
selection subset, original identities, pre-event score, coordinates and source
position evidence. Independently derive graph components and audit edge counts,
spanning rank/nullspace, contrast support and leave-one-match effects. On TEST_ONLY
small designs, verify the rank theorem with exact rational Gaussian elimination,
including cycles, disconnected graphs, duplicate rows and a bridge-removal case.
Fail if a parent/source hash or original membership changes. Preserve old artifacts.

Any outcome is informative about this corpus/design, not a proof that abilities do
not exist. It cannot rule out standardized skill tests, stronger substantive
assumptions, other estimands, team/interaction analyses or richer future data. Priors
or regularization may select one solution; they do not manufacture observed bridges
or validate an ability construct. Data/rights and statistical sufficiency remain
separate gates. All derived tables, numerical findings and source evidence remain
local and ignored. No new data, model-training scope, runtime agent, merge, retarget,
force push, deployment or protected-data publication is authorized.
