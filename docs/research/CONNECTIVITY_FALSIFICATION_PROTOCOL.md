# Connectivity falsification protocol v1

Parent PR #19: `d5a0e833f3eafdf2c3cf45a1b85702d9c59515a1`.
All 64 matches are development-exposed. This protocol is recorded before the new
calculations; it does not restore independent confirmation. No new model fitting,
source acquisition, player rating, dashboard or runtime agent is authorized here.
Original metric, registry, protocol and every earlier result remain unchanged.

## Exact decomposition, no fitted model

Use all original eligible chains, including returns in the opportunity denominator.
For each roster player-match retain completed/received counts, all eligible chains,
known-geometry chains N, nonreturn opportunities M and primary count K. Preserve
K = N × (M/N) × (K/M), with undefined factors null. Conditional fractions are sample
properties, not ability or per90. Whole-team completed passes and native possessions
are context, not certified player availability. Include zero/sparse player-match rows.
Report correlations of counts and fractions with all baselines, with support and
undefined correlations; no p-values or iid event bootstrap.

On binary per-chain original outcomes, report direct within-stratum Bernoulli sums
of squares sum(n*p*(1-p)), relative to the unstratified total. These are exact
retrospective tabulations, not fitted/predictive/context-adjustment models or causal
explained variance. Partitions: team-match; team-match/period/pre-first-pass score;
start zone; endpoint-zone pair; endpoint-zone pair/nonreturn; team-match/possession;
team-match/period/score/start; and the latter plus latest available native position
annotation for B. Store all stratum denominators, player counts and event IDs.
Endpoint pairs plus return status determine the original metric by definition;
zero residual there is a tautology, not model validation.

Compare within-team-match baseline ties and within-context multi-player support.
Report opportunities in multi-player strata and those with >=5 eligible chains
per player. The >=5 threshold is a sparsity diagnostic, not certified adequacy.
Record denominators 0, 1–4, 5–9, 10–19 and >=20; report fraction range only where
supported. Latest Starting XI/Tactical Shift assignment at/before the first pass
is a last-observed annotation, not an inferred continuous/stable role. Retain its
original ID/index and missingness; do not use uncertified minutes or impute a role.

## Intermediary definitions on identical records

Let p0 be A's first-pass start; p1 its annotated end (a recipient-location proxy);
p2 B's second-pass start; p3 its annotated end (assigned recipient C). These are
provider-native action annotations, not tracking positions or decisions by C.
Compare original p0→p3 with: incoming p0→p1; receive-proxy-to-release p1→p2; and
B outgoing p2→p3. Apply the same nonreturn condition to all descriptors; unknown
coordinates stay null. Additionally compare exactly one successful B Ball Receipt*
location with p2. Without exactly one such record, actual annotated receipt-to-release
is unidentifiable, not zero. Report proxy/receipt discrepancy without repairing either.
Use cross-tabs, exact disagreement IDs and missingness, not attributed credit.
The vector identity p3-p0=(p1-p0)+(p2-p1)+(p3-p2) is geometry, not causal contribution.

## Sensitivity parameters fixed before execution

Native 120×80 coordinates only, never flipped or interpreted in metres. Grids:
6×4 and nested 3×2, plus 6×4 with interior boundaries shifted by (+5,+5),
(+10,+10), and (-5,-5) native units. Keep outer bounds fixed, without wrapping.
Record clipping/edge-width interpretation. Count same-fine/different-coarse
violations (must be zero); quantify fine-different/same-coarse reclassification
on the identical event set. All reduction from nested coarsening is mechanical
recoding; it cannot itself establish different behavior.

Report continuous Euclidean native separation for each leg and net endpoints:
count, missingness, min, median, quartiles, max. Predeclared net separation >=20 and
>=40 native-unit counts are descriptive sensitivities, not optimized football value
thresholds. Retrieve tiny (<1 unit) original grid crossings and noncrossings with
>=20-unit net separation where observed, without assuming they exist.

Eligibility variants: original; exactly-one-successful-receipt required; no Carry
between passes; no intervening records; and relaxed only to additionally permit
B's source-annotated Complete Dribble. Never skip an opponent, unsuccessful/unknown
pass, failed receipt/dribble or other action. Keep original membership/identity gates.
Relaxed chains are separate observations, not retroactive repairs of the old metric.
Retain every candidate pair and rejection reason, not only favorable chains.

## Deterministic evidence retrieval and recommendation

Use earliest match-ID/provider-order examples in each category: original true but
B outgoing false, converse, original true but relocation false, relocation true but
original false, missing receipt, grid/continuous disagreements and relaxed-only chain.
Retain both original pass IDs, intervening records, native coordinates, source hashes,
context and all definition outcomes. Do not choose individuals by fame or rankings.

KEEP the descriptor only as a precisely named, auditable sequence observation if it
provides an explicit ordering/retrieval use not recoverable from unsequenced counts;
this is not proof of analyst utility or player ability. REVISE its presentation/use
if endpoint geometry, opportunity dominance or unstable definitions make intermediary
interpretation misleading; retain original artifacts and expose components instead
of replacing them with a stronger-looking score. RETIRE it as a distinct player
attribute if its proposed construct cannot be distinguished from volume/location/team
context with adequate independent support, or if independent useful retrieval tests
fail. Source-integrity failure blocks affected analysis immediately. No current
favorable statistic can promote the construct to independently validated.

New independent evidence must include untouched authorized cross-league/season data,
comparable recorded opportunities/roles or certified exposure, predefined clustered
reliability/context analyses, independently annotated sequence relevance and blinded
ledger-baseline analyst evaluation. Specific predictive/hierarchical/latent model
uses need separate rights/authorization review; none is fitted in this audit.

All provider-derived evidence stays local and Git-ignored. Commit only code,
methodology and non-provider integration governance notes; numerical findings and
original-event positive/counterexamples belong in a local audit report. Do not
publish protected tables, reports or screenshots. No merges, retargets or deployments.
