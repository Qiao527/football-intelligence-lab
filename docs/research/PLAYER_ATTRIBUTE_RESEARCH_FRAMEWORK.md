# Player Attribute Research Framework v1

FIL distinguishes four objects: an observed action; an observed match descriptor;
a repeatable context-dependent tendency; and a latent ability. Computability
establishes none of the transitions between them. This framework extends the
Master Reference and Engineering Handbook with explicit measurement contracts.
The owner request authorizes a descriptive local study, not general model training.

## Research registry and status

The packaged [ATTRIBUTE_REGISTRY](../../src/fil/research/attribute_registry.json)
is versioned `fil-attribute-registry-1`; `fil.research.attribute_registry.load()`
validates every required field in editable and regular installations. Each entry
contains identity/version, interpretation, construct, observable evidence, features,
opportunity denominator, eligibility, confounders, baselines, estimation, reliability,
construct/incremental tests, independent validation, counterexamples and status.
Only Attacking Connectivity, Risk-Adjusted Progression and Possession Continuity
are registered. The latter two remain proposed and are not calculated here.
Attacking Connectivity's construct also remains proposed; its implemented descriptor
is exploratory. A registry hypothesis and a study's empirical status are separate.

Allowed statuses: proposed, descriptive, exploratory, independently_validated,
insufficient_evidence. A status change requires a new version, evidence manifest
and reviewer rationale. Independent validation is always bounded to a population,
provider semantics and use; it never automatically means causal ability. No player
ability scores or rankings are produced. A failure to identify an attribute is a
valid scientific result; do not replace it with a flattering narrative.

## Measurement specification

Start with a football question and a falsifiable construct, then determine which
behaviors are actually observable. Native event locations describe annotated action
sites; recipients indicate recorded passing connections. They do not establish
continuous position, intent, physical direction, vision, leadership, pressing
resistance or off-ball support. A shot followed by a connection is retrospective
co-occurrence/order evidence, not credit for creating the shot.

A specification must state its unit, scope, provider revision, analytical version,
feature cutoff (for prediction), original event lineage, null/exclusion rules and
context dependencies. Aggregate graph paths can concatenate events that never
formed a sequence. This study instead requires ordered original records and never
uses node deletion as a simulated player removal.

## Opportunities and fair comparison

Use a denominator only when the numerator is demonstrably a subset. Conditional
chain fractions use geometrically observed eligible chains through the intermediary.
They answer a narrow question about recorded chains, with selection into those
chains still uncontrolled. Team completed-pass counts and native possessions are
team context, including intervals when a player may be absent; they are not player
availability. No player share per team opportunity is interpreted as efficiency.
Uncertified official minutes and per90 stay null. Do not substitute source-clock
arithmetic or conditional census envelopes for physical exposure.

Store unnormalized counts, denominators and missingness together. Zero observed
chains is not zero ability. Unknown geometry is not within-zone behavior; uncertain
segment membership is not a turnover. Roster-only appearances do not prove playing
exposure. Starting XI/Tactical Shift annotations and substitutions retain original
IDs; they do not certify an invariant role between observations. Role-conditioned
comparisons must be withheld when stable comparable roles cannot be established.

## Reliability and uncertainty

Report match/team/player support and repeated opponents before a reliability
number. Within-player ranges and chronological split differences are descriptive
sensitivity diagnostics. They mix context, role, opportunity and measurement noise.
They are not test–retest reliability coefficients or evidence of stable ability.
Split halves must state inclusion thresholds, order, zero/null denominators and
all supported observations. No iid resampling of overlapping chains, shared shots
or repeated player events. A connected team/player dependence component can span
an entire tournament; counts of actions do not increase independent population
support. Conditional match uncertainty cannot establish cross-league generality.

Future hierarchical models may decompose player, team, opponent, role and season
variation with partial pooling, but require authorized fitting, adequate crossed
support and identifiability checks. Fixed team–player nesting and sparse repeated
roles may prevent separating those effects. Examine shrinkage sensitivity, variance
components, posterior/predictive calibration and within/between-player variation.
Do not fit such models merely because a library provides them.

## Construct and incremental validity

Require independent operational annotation and counterevidence. Does a chain measure
connecting observed passes, or just frequent passing in particular zones? Compare
completed/received volume, directed degree, original actor counts, zone/context
frequencies and possession participation. Different counts at equal volume can
establish descriptive non-equivalence; they do not establish football usefulness.
A correlation or low p-value cannot establish construct validity. Context overlap,
missingness and within-player changes can falsify a stable-ability interpretation.

Future incremental evaluation must predeclare a football decision, baseline inputs,
cutoffs, outcome windows, dependence treatment and minimum useful effect. Fit only
on training data, choose parameters on development data and report all baselines,
calibration and uncertainty on genuinely untouched matches. For player tendencies,
also hold out teams/seasons and test role/population invariance. Freeze all decisions
before access. PR #18's five test matches are consumed; this study uses no untouched
confirmation data. Never reuse their favorable location Brier as validation of
connectivity or compare losses across different targets.

## Falsification and analyst utility

Find high-volume players without cross-zone chains; return chains; cross-zone
chains without later recorded shots; different observed intermediaries connecting
the same endpoints; and apparent differences that vanish with context conditioning.
Retain evidence against the hypothesis and unsupported strata. Do not choose a
famous player or favorable episode as the validation population.

A future blinded, counterbalanced analyst task compares source-evidence retrieval
with a searchable event ledger, using independently adjudicated relevant actions,
precision/recall, unsupported-claim rate, time-to-supported-answer and stated
uncertainty. Predefine the minimum useful improvement and power analysis before
recruitment. Human football judgment is not replaced with AI-generated ground truth.
No analyst experiment or practical utility result is claimed by this implementation.

## Architecture and governance

Pure deterministic extraction lives in `fil.research.connectivity`; packaged
registry validation is separate. Immutable ignored bundles retain inputs, code and
protocol identities, original passes, chains, contextual support, exclusions and
summary. An independent raw-JSON state machine verifies the extraction. Historical
sources, quality gates, clocks, frozen models and previous results remain intact.
No dashboard, runtime LLM, agent orchestration or advanced player model is added.

A future Evidence-Grounded Research Analyst may consume a read-only boundary:
request source/definition versions, query verified observations, retrieve original
IDs, retrieve uncertainty/counterexamples and return `not_available` for unsupported
claims. It may not fit models, alter facts, elevate registry status, acquire data,
infer missing values or issue player ratings. This is an architectural boundary,
not an implemented agent. Provider data must never be uploaded to external AI.
