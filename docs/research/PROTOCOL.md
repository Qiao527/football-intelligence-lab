# Research foundation contracts and flagship investigation

Current branch parent is PR #12 at `1ec94984a76ac4db95ecc3d4ea73d1a800671fec`.
All existing PRs stay intact/unmerged. This is one scoped research foundation,
not a new dashboard, rating or validated discovery engine.

## Implemented corpus and identity contracts

`python -m fil.research --config CONFIG [--config CONFIG ...] --pipeline-revision FULL_SHA`
builds an offline content-addressed local corpus. Each config enters the complete
existing source→canonical→clock→score verification chain. The production CLI first
checks the raw manifest against the exact reviewed allowlist; there is no flag to
grant rights, download more data or skip integrity. `SOURCE_POLICY.md` currently
covers only match 8658. More configs are supported by the API/contracts but real
multi-match data is blocked until scope/rights/adapters are reviewed.

Source IDs/records remain unchanged. Compound event identity is
`(source, match_id, event_id)`; provider player identity is `(source, player_id)`.
Names are retained as aliases, never used to merge people. Match/team memberships
stay separate, and conflicting opposing-team memberships are reported explicitly.
Cross-provider identity linkage is unsupported. Duplicate match inclusion is an
error, not additional evidence. Mixed schemas, unsupported provider semantics or
metadata/source disagreement fail. TEST_ONLY fixtures exercise two-match contracts;
only one real match is currently verified. No cross-match replication is claimed.

Corpus reports retain every column's null count, unknown semantic records,
actorless/unrostered records and exposure uncertainty. No missing feature is
imputed as zero. Derived artifacts are staged atomically, compared on reuse and
never silently overwritten; they must be outside immutable inputs. Version/code/
input hashes and output file digests are recorded. Existing raw/derived products
remain untouched and are not repackaged for redistribution.

## Recorded census exposure and roles

`fil-recorded-exposure-1` uses source Starting XI, native Substitution replacements,
Player Off/On and explicit red/second-yellow dismissal records, bounded by verified
period starts/ends. It retains source transition IDs and per-player/period interval
boundary IDs. Temporary absences count as recorded gaps, not substitutions; no
actor min/max timestamps substitute for missing lineup evidence. Duplicate IDs,
missing boundaries, unknown replacements, contradictory re-entry, >11-player
census or on-field actions outside the census withhold provisional exposures.
Half breaks and shootouts do not enter elapsed durations.

Values are **provisional recorded elapsed census seconds**, including stoppages,
not official appearance minutes, live-ball time or physical availability. Unused/
unsupported roster records remain null, not inferred non-participation or zero.
Existing Player Evidence `minutes_played` stays null and no per-90 is enabled.
Native XI/Tactical Shift position snapshots are evidence metadata, not continuous
role certification or inferred tactical assignments. Independent source integration
checks these intervals before any future denominator certification.

## Evaluation infrastructure actually implemented

- Predeclared date cutoffs keep every action of a source/match together in
  train/validation/test; empty splits and duplicate identities fail. Validation
  selects/tunes methods; the untouched test set is evaluated once after freezing.
- Feature evidence IDs and provider indices must precede the strict future label
  boundary in the same source/match/period. This helper checks explicit lineage;
  it cannot detect a feature secretly computed from future information. Independent
  feature-generation/code audit and fit-state lineage remain required.
- Training-only equal-match constant/context-frequency baselines,
  with explicit unsupported-context fallback, reject train/test match overlap.
  Training weights invert within-match record counts to match the evaluation target;
  pooled-row priors would be a mismatched baseline.
  The two-training-match software guard is not an evidence-based sample threshold.
- Equal-match weighted Brier/log-loss comparison, fixed-bin reliability summaries
  (event weighted, counts exposed), and paired match-cluster percentile bootstrap.
  Impossible 0/1 forecasts produce reported infinite log loss, not silent clipping.
  A single match gets no bootstrap interval. Empty/unknown probabilities fail.
- Repeat-team/player overlap is measured separately for partitions; missing identity
  coverage is unknown, not zero overlap. Match bootstrap alone does not handle all
  repeated-team/player dependence. Claims about unseen teams need additional
  group/time blocking or justified multiway/hierarchical sensitivity analysis.
- Reproducible within-match/team/period label permutation is a negative-control
  diagnostic. It preserves outcomes within those strata but does not guarantee
  exchangeability with respect to other state/role effects; it is not a certified
  p-value or a replacement for source labels.
- A candidate can lose to a baseline: negative Brier improvement is reported as
  such. Even excellent numeric scores always remain `exploratory`, with
  `scientifically_validated=false` and practical usefulness insufficient evidence.
  Blinded football review and prospective decision/task utility are separate gates.

The baselines/evaluation machinery has TEST_ONLY regression coverage. It has not
been empirically validated on an authorised multi-match corpus. No synthetic
forecast score is presented as a football research finding.

## Sample size: no arbitrary ten-match or 900-minute rule

The earlier research-design planning floors are withdrawn as scientific sample
requirements. Sample size depends on outcome rarity, meaningful effect, variance,
roles/strata, dependence, missingness, candidate multiplicity and the intended use.
For a paired independent-cluster mean difference, the implemented planning
approximation is:

`n ≈ ceil(((z(1−α/2) + z(power)) × pilot_cluster_SD / meaningful_effect)²)`.

The effect must be justified by a football/decision task, not chosen after seeing
results. Variance needs independent pilot clusters; one fixture cannot estimate
between-match variance. Zero pilot variance is also insufficient. The function
returns null instead of inventing a target sample size in these cases.

This normal approximation is a planning aid, not proof of training adequacy.
Use simulation/cluster resampling, learning/calibration curves, effective sample
size under repeat-team/player dependence and rare-outcome/stratum support before
freezing a corpus target. Keep a held-out confirmation set outside exploratory
sample-size selection. No empirically justified match target can yet be reported.

## Flagship question and competing explanations

Question: **which players contribute unusually important attacking connections or
progression beyond conventional summaries?** Current answer: **inconclusive**.
A one-match illustration nominates Paul Pogba (provider ID 20004) for source-action
review. Selection is disclosed as illustrative, not a preregistered population
screen or a data-selected winner.

The local case asks whether the custom progression rule supplies useful recorded
buildup evidence beyond completed-move volume and positive native Δx. It compares
all supported completed owner passes/carries, forward moves, and 5/10/15-unit gain
thresholds. Outcome context is a later same-team/period Shot in the same native
possession ID, strictly later by provider index. The source records are unchanged;
this is neither a probability forecast nor causal shot credit. Original action/
shot IDs, team baselines, first/second half and pre-event score strata are retained.
Conventional shot goals/xG, completed passes and reciprocal shot links are shown
separately. These contextual subsets overlap and are not independent samples.

Competing hypotheses:

1. Progression provides additional reviewable buildup examples beyond volume or
   final-pass links; it may enrich an analyst's event-review queue.
2. Any apparent enrichment is explained by forwardness/starting location, phase,
   role, score/opponent response, unequal opportunities or source segmentation.
3. Threshold changes or omitted actions reverse the impression; backward/lateral
   routes and alternative players' actions provide counterevidence.
4. Even stable prediction adds no practical information beyond a simpler baseline.

Required investigations include role/state/opponent/exposure adjustment with
support/overlap checks, alternative pathways without interpreting static node
removal as substitution, independently reviewed positive/negative examples,
authorised cross-match replication, missingness/selection analysis and frozen
multiplicity control for any eventual population screen. Off-ball value remains
unobserved. No "unusually important", underrated or low-contribution label passes.

## Local reproduction and independent verification

```bash
uv sync --frozen
uv run --frozen python -m fil.research --config "$FIL_DEMO_CONFIG" \
  --pipeline-revision FULL_IMPLEMENTATION_SHA --output data/interim/research
uv run --frozen python scripts/verify_research_source.py "$FIL_DEMO_CONFIG" BUNDLE
```

The output includes unchanged corpus events, corpus/identity/missingness/exposure
JSON, local case Markdown/JSON and a hash manifest. The independent checker uses
original provider JSON for move eligibility, geometry, source order, score state,
shot follow-up, roster identity and a separate census integration algorithm.
That is independent arithmetic/source reconciliation, **not independent football
judgement or scientific validation**. Provider-derived case data/IDs/text and
reference downloads stay local/ignored; publication requires rights review.

Existing startup and interaction limitations remain documented in
`STABILIZATION_REPORT.md`; no new performance improvement is claimed by this work.


## Later approved pilot execution

The owner conditionally approved PR #14’s exact StatsBomb file scope on
22 October 2026. See [real pilot delivery](WORLDCUP_PILOT_DELIVERY.md) and
[SOURCE_POLICY.md](../SOURCE_POLICY.md) for the subsequent acquisition and
blocked expansion gate. Earlier pending-authorization/one-match descriptions
remain historical records. The original config-based CLI retains its 8658-only
registry; the new approved pilot command verifies the exact enumerated scope.
