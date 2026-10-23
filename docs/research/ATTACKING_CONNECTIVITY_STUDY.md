# Attacking Connectivity — exploratory real-data study v1

**Verdict: INCONCLUSIVE as a player ability.** The implemented descriptor captures
source-ordered passing connections, but distinct latent ability, incremental
football usefulness and independent replication are not established. No player
rating, ranking, importance or discovery-success claim follows.

## Question, hypotheses and population

Question: do players exhibit repeatable observable attacking connections beyond
what conventional passing statistics describe? A narrow descriptive hypothesis is
that counts of cross-zone non-return chains need not be a deterministic function
of passing volume. The stronger construct hypothesis requires repeatability,
context comparability, independent annotation and practical utility. Counterevidence
includes redundancy with passing volume, grid sensitivity and poor contextual
support. Definitions and outcome-blind selection were recorded in
[CONNECTIVITY_PROTOCOL.md](CONNECTIVITY_PROTOCOL.md), commit
`ec4af15a53deedda42f420360d740434dc3302cb`, before this extraction executed.
This is not an untouched prospective experiment: all current matches were already
available/inspected. No PR #18 test match is reused as independent confirmation.

The local authorized corpus has 64 matches, 32 teams, 736 rostered provider player
IDs and 227,825 unchanged original events from the 2018 men's World Cup, pinned to
StatsBomb revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. Source identity,
original event order, score reconstruction and native spatial gates must all pass
before extraction. Exact-time and physical-orientation gates remain blocked.
Provider files, derived player tables, event examples and source IDs remain local
and Git-ignored. No additional source acquisition or modeling rights are inferred.

## Operational definition and baselines

A→B then B→C must be adjacent completed passes within a contiguous single-owner,
single-period native membership. Only B's Carry or successful Ball Receipt* records
may intervene. No failed/unknown pass, opponent event, other action or membership
change may be skipped. A completed pass requires an absent outcome key; explicit
null is unknown. Actor/recipient identities must join to the same original roster.
The primary descriptor counts A≠C chains where the first pass start and second pass
end occupy different 6×4 cells in the original 120×80 frame. This does not certify
physical forwardness or attacking value. A receiving link is source recipient
evidence, not an assertion of an observed physical touch or off-ball position.

The conditional fraction uses all eligible through-player chains with known
geometry, including returns. It is not a player efficiency score. Team completed
passes/possessions are context, not playing availability. No per90 or normalized
ability comparison is calculated. Baselines retain exact completed/received IDs,
in/out degree, original player-actor counts, native possession participation and
zone × period × strictly pre-pass score frequencies. Actor counts include provider
annotations such as Ball Receipt* and are not independently observed touches.
Original position annotations/substitutions remain evidence, not stable-role labels.

## Actual observations and counterevidence

| Observation | Result | Interpretation |
| --- | ---: | --- |
| Roster-valid completed passes | 50,167 | Same pass counted once as sent and once as received |
| Eligible ordered two-pass chains | 25,252 | Overlap is allowed; not independent trials |
| Primary cross-zone non-return chains | 18,967 | Descriptive source-native connections |
| Coarser 3×2-grid subset | 14,138 | 25.46% fewer; definition materially matters |
| Geometrically unresolved eligible chains | 0 | Does not certify physical direction |
| Excluded native memberships | 125 | Unsupported/cross-period membership; all preserved |
| Active player-match records | 1,787 | At least one actor record or completed-pass receipt |
| Active records with zero eligible chain | 95 | Zero evidence under this definition, not zero ability |
| Diagnostic-eligible players | 178 | ≥3 matches, each with ≥20 completed passes |
| Equal sent/received-volume within-team-match pairs with differing descriptor | 14 | Non-equivalence to these two counts only |
| Connected match dependence components | 1 | No independent population interval certified |

Pass exclusion reasons include 12,714 noncompleted and 3,909 missing-identity flags;
these counts can overlap and must not be summed as unique excluded events.
Additionally, 12,481 candidate adjacent completed-pass pairs have intervening
nonpermitted records; 2,206 have a recipient who is not the next passer. Those
sequences are rejected rather than repaired. Full event-level reasons remain local.

Across active player-match records, descriptive Pearson correlations with the
primary count are: completed passes **0.905130**, received passes **0.857450**,
actor records **0.776513**, outgoing degree **0.600124**, incoming degree **0.507207**
and native possession participation **0.601997**. These are pooled redundancy checks,
not independent samples, adjusted effects or significance tests. The strong volume
relationship is evidence against presenting this descriptor as a newly established
ability. The 14 matched-volume pairs only establish some additional observable
sequence structure; roles, locations and opportunities remain unmatched.

Illustrations select six eligible player IDs by ascending SHA256 of their provider
ID, independent of descriptor outcome and fame. Their complete match records,
context denominators and IDs are in local `study.md`/`summary.json`; no favorable
individual is promoted. Across all 178 eligible players the median within-player
match-fraction range is **0.198340** and median absolute chronological split
fraction difference is **0.074721**. These are descriptive variation, not reliability
coefficients. Among the six illustrations, supported-match ranges span approximately
0.138–0.405 and split differences 0.033–0.153. Sparse conditional denominators can
produce large changes. Full support, including below-threshold matches, is retained.

The selected pairs share only 4–18 primary zone × period × score context bins,
against unions of 42–68. Context overlap does not establish role/team equivalence.
There are 203 active player-match records without Starting XI/Tactical Shift
position evidence, and 1,096 roster rows have empty native lineup position lists.
An empty list is not a stable-role certificate. Substitutions and roster evidence
are retained; no missing position or minute is filled from player reputation.

## Exact positive and counterexample retrieval

The local bundle retrieves the earliest qualifying examples by match ID/provider
order, rather than a famous player's highlights:

- A cross-zone non-return chain followed by a later owner Shot in the same verified
  membership. The first retrieved positive is **not cross-zone on the coarser grid**,
  a concrete definition-sensitivity counterexample to a robust spatial claim.
- A return chain A→B→A, even though its endpoints occupy different native cells.
  Spatial movement alone does not meet the distinct-endpoint definition.
- A cross-zone non-return chain with no subsequent recorded Shot in that membership.
  This is counterevidence to equating zone connection with shot creation; absence
  of a Shot here is not proof of physical possession failure or a causal negative.

`summary.json.retrieval` and local `study.md` contain both original pass IDs,
intervening IDs, source manifest identity and all later original Shot IDs. Other
actually observed A→D→C chains in the same membership are retained as alternative
paths. They are not simulated player removal or evidence that D could replace B.
The independent raw-source verifier checks exact membership, ordered lineage,
recipients, native cells, intervening records, later Shots, alternatives, baseline
counts, pre-event score and contextual denominators across every eligible chain.

## What this establishes, and what it does not

Supported: deterministic, auditable source-native chain extraction; real multi-match
descriptive variation; concrete positive/counterexamples; some sequence information
beyond identical completed/received counts. Exploratory: pooled redundancy,
context overlap, grid and split sensitivity. **Not established:** incremental value
beyond all conventional/context baselines, stable role-adjusted player tendencies,
latent ability, causal importance, generalizability or analyst usefulness. No new
predictive or hierarchical player model was fitted. The old frozen study and all
historical BLOCKED/conditional outputs remain unchanged.

Current data cannot certify comparable physical exposure, stable roles, off-ball
support or independent league/season replication. Tournament advancement and player
selection create unequal support; repeated teams connect the entire corpus.
[ATTRIBUTE_VALIDATION_ROADMAP.md](ATTRIBUTE_VALIDATION_ROADMAP.md) specifies the
next independent evidence and failure criteria. The scientifically defensible
conclusion remains INCONCLUSIVE, with a working evidence layer for future research.
