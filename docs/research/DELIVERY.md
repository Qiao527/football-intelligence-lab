# Research foundation delivery and remaining evidence

This work changes the research standard, not the dashboard feature count. Its
primary empirical deliverable is a **local, source-backed and inconclusive football
case**, with supporting/counterexamples and original action IDs. No player-quality
or hidden-connector finding has passed scientific validation.

## 1. What current metrics usefully answer

Source xG/shot timelines describe recorded shot production. Directed pass evidence
retrieves observed passer–recipient connections. Native sequence/zone representations
and player participation retrieve recorded buildup actions and contextual shots.
Their immediate defensible use is source inspection and an analyst review queue.
That potential utility is separate from independently demonstrated decision value.
[The audit](ANALYTICS_AUDIT.md) covers twenty metric families, each with its question,
measurement, assumptions, prohibited inferences, class, baseline and usefulness test.

## 2. Descriptive or potentially misleading indicators

No current indicator is independently validated for player quality or tactical
effectiveness. Source verification does not supply that validation. Native
progression is a geometric proxy, network weights are pass volumes, and pre-shot
involvement is association rather than allocated credit. Process `*_after_final_third`
fields currently count co-occurrence, not ordered transitions; this is now clarified
in the possession dictionary. Conditional time-to-shot has shot-producing-chain
selection bias. Event means are not formations and per-100 records are not per-90.

## 3. Data and rights missing

The production allowlist remains the exact approved StatsBomb match 8658 manifest.
No new match was acquired. The multi-match contracts are tested with labelled
TEST_ONLY data; the actual corpus has **one** match. Provider IDs and original
records are preserved, native names/aliases retained, unrostered actors surfaced,
and inconsistent opposite-team identity memberships reported. Cross-provider name
matching is not implemented or silently assumed.

Recorded XI/substitution/off/on/card chronology is now audited, including temporary
absence and period boundaries. Elapsed census intervals are provisional; official
minutes, continuous roles, tracking, opportunity and independent multi-match
support are still missing. Existing UI minutes remain null. Repeated team/player
dependence and selection bias cannot be solved by copying one match into folds.

Rights/source evidence for StatsBomb, a Wyscout processed mirror and Metrica sample
data is in [data and method review](DATA_AND_METHODS.md). Unknown licensing remains
unknown; socceraction's MIT code licence does not grant provider-data rights.
The original xT blog request returned 403; no full original-text review is claimed.
Original VAEP authors' method docs/reference code and documented xT implementation
were inspected, not installed/executed. Complex model implementation stays deferred.

## 4. Scientific evaluation methods implemented

[Protocol](PROTOCOL.md): whole-match dated train/validation/test splits; explicit
future-label feature-lineage checks; training-only constant/context baselines;
Brier/log-loss and reliability counts; equal-match paired bootstrap; repeat-team/
player overlap audits; missingness/null rules; within-match/team/period label-shuffle
diagnostic; threshold/state/period sensitivity and independent source verification.
Numerically good and bad models are both exercised in TEST_ONLY tests. Evaluator
status remains exploratory even with excellent scores, and practical usefulness
remains insufficient evidence. A single match produces no match-bootstrap interval.

Sample planning now requires an externally meaningful effect and independent pilot
variance. A documented normal approximation is implemented with explicit assumptions;
zero/insufficient variance yields null. Prior ten-match/900-minute planning floors
were withdrawn as scientific requirements. Model-training adequacy, learning curves,
rare outcomes, multiplicity and higher-level dependence still need investigation.

## 5. Baselines actually compared versus only implemented

The real local case compares completed owner-move volume, native positive Δx,
and progression gains of 5/10/15 units, with team, period and pre-event state context.
All exact action sets and later shot IDs are independently recomputed from original
JSON. These are descriptive subset comparisons, not held-out probability forecasts.

Constant training priors/context-frequency forecasting and evaluation machinery are
implemented and tested with TEST_ONLY data. They have **not** been empirically
compared on real held-out matches. No xT/VAEP model was trained; no claim that a
complex model beat or lost to a baseline is manufactured.

## 6. Football case: supported, contradicted, inconclusive

The nominated Pogba illustration asks whether the custom progression proxy supplies
buildup evidence beyond conventional shot/pass/final-link summaries. Source-backed
omitted actions and progressive actions without subsequent recorded shots provide
counterexamples to interpreting progression as a complete buildup/importance measure.
The source-action queue gives a football analyst concrete additional records to
review rather than an arbitrary importance ranking.

This does **not** contradict the geometric metric's stated definition, establish a
bad decision when no shot follows, prove missed off-ball value, or demonstrate
incremental predictive/decision value. Subsets overlap within a single match and
same native chain. Role, score/opponent response, starting location, event opportunity,
restarts and segmentation remain plausible explanations. Importance/unusualness,
underrating and general tactical effectiveness remain **inconclusive**.

The complete local case Markdown/JSON, phase/state tables, source IDs and hash
manifest are generated by `python -m fil.research`; `/tmp/fil-research-bundle.json`
records the exact local bundle for this session. Do not publish these provider-derived
outputs without the existing rights/branding review. No independent football expert
review occurred; independent arithmetic verification is not such a review.

## 7. Evidence needed next

A concrete bounded *pilot proposal*, **not acquired or an adequate sample-size
claim**, is the seven 2018 World Cup quarter-final/semifinal/final matches listed in
the already-held source match metadata: 8649, 8650, 8651, 8652, 8655, 8656, 8658.
It is a complete late-knockout-stage ingestion/missingness pilot, selected by stage,
not metric performance. It is male elite tournament data with strong repeated-team
and finalist-selection bias. Fixture 8658 has already been explored extensively and
must remain development-only; it cannot later be relabelled an untouched test set.

Before that pilot, the owner must explicitly extend the recorded match-specific
project scope to the six additional IDs under the pinned terms/local noncommercial
restrictions, followed by appropriate source/adaptor verification. No broader data
rights, raw redistribution, commercial use or publication is requested/inferred.
An actual confirmation corpus and sample target must then be justified separately,
with validated action/direction semantics, exposure/role support, context overlap,
independent football review, counterevidence, leakage/calibration/dependence analysis,
and prospective decision utility. No automatic discovery label passes meanwhile.

## Verification and engineering boundaries

- Full editable tests: **376 passed**; all existing 360 tests retained.
- Frozen regular installation tests: **376 passed**; wheel and sdist build succeed.
- `ruff check .`, frozen lock agreement and research CLI help succeed.
- Independent new research checker: original corpus IDs/JSON/aliases, geometry,
  baseline/contrast sets, score context, shot follow-up and separately integrated
  census all reconcile against raw records. Existing Explorer, player, possession,
  tactical and score source checks also pass.
- Same-input artifact reuse recomputes facts and preserves existing output bytes;
  tests reject corruption, output-under-input paths and unreviewed source manifests.
- All 23 snapshotted raw/canonical/clock/score/metric/config inputs retain original
  SHA-256 and modification nanoseconds. Original 2,978 events, official France 4–2
  Croatia and source xG remain unchanged.
- Initial tests exposed duplicate-ID collapse and contradictory test identities;
  guards/diagnostics and corrected explicit TEST_ONLY fixtures were added. A score
  checker initially ran outside the frozen environment and lacked PyArrow; it was
  rerun successfully in the pinned environment. No failure was ignored.
- No UI/performance improvement claim: the previous measured startup/interaction
  limits remain. No dashboard changes, deployment, protection bypass, data-rights
  expansion or existing PR merge/retarget occurred. One research draft is stacked
  on unchanged PR #12; hosted CI/head status is reported at delivery.
