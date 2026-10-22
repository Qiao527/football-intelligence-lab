# Real multi-match corpus readiness — authorization pending

Parent: draft PR #13, `research/fil-evidence-foundation` at
`1a761c17ee26c93b502aca7abb0738f1500aab6d`. No existing PR is merged or retargeted.
This delivery corrects measurement semantics and prepares ingestion/evaluation;
it does **not** deliver a new real multi-match corpus or held-out results.

## Primary-source audit, 22 October 2026

| Source | Verified evidence | Remaining restriction |
| --- | --- | --- |
| Original Pappalardo/Wyscout Figshare | Original collection locator DOI `10.6084/m9.figshare.c.4415000`, version-2 URL, paper DOI `10.1038/s41597-019-0247-7` are recorded leads from the previously read mirror | Primary metadata retrieval blocked by environment policy; original release version, constituent articles, file identities/hashes, terms, attribution and training permission **unverified** |
| Hudl/StatsBomb | Original provider repository at immutable `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`; locally held README, agreement, competition/match metadata and 8658 bundle hash-verified | Existing owner authorization covers only 8658; no expansion approved |

Figshare request: `GET https://api.figshare.com/v2/collections/4415000/articles`.
Proxy response: `CONNECT tunnel failed, response 403`, server `envoy`.
Current runtime policy is enforced/restricted and omits `api.figshare.com`.
One attempt was made; no alternate proxy or processed mirror was used to evade
it. Smallest environment action: allow `api.figshare.com` for the primary metadata
audit, then review any original terms hosts actually referenced by the response.
This is separate from dataset-use approval. No Figshare event/archive was acquired.
Do not classify the mirror's CC BY 4.0 assertion as original licensing evidence.
Candidate mirror file IDs 14464622/14464685/15073721/15073697 remain unverified
leads, not an acquisition manifest. Wyscout remains outside the approval proposal.

StatsBomb primary terms, read from the held original PDF using `pdftotext`:

- `README.md`: SHA-256 `98a757466c4d931dba4b6c4290c55c2fe74e4550d7455bbe05fd884dc831aff3`.
- `LICENSE.pdf`: SHA-256 `a5462e69aeb71a39268b760b110c5c2190a2e0cee3015ba976f66bd71f6c2bb4`;
  agreement dated 8 September 2023. [Original pinned PDF](https://raw.githubusercontent.com/hudl/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/LICENSE.pdf).
- `data/matches/43/3.json`: SHA-256 `f89dbd4aedcaf9c9e4ec9d8e745d5d54596500ec357d7489c914a2f126805adf`;
  64 World Cup 2018 match identities, including 8658. Existing source manifest
  remains immutable; [source policy](../SOURCE_POLICY.md) records registration attestation.
- §1.1 permits analysis/research/shared understanding. §§1.2.1, 7 restrict
  modification, reproduction and third-party data provision; §1.2.2 forbids
  commercial exploitation, including derived analysis. §1.4 requires provider
  brand logo on publications; README additionally requests credit. Registration
  is requested in the preamble/§2.2, attested previously by the owner.
- The agreement does **not expressly license machine-learning training or model
  distribution**. Local empirical frequency/context/location baseline estimation
  is proposed as noncommercial research under §1.1, a scoped interpretation,
  not an express general model-training licence. xT/VAEP training, released model
  weights, external AI uploads and commercial training remain outside this proposal.
  Owner approval cannot override provider terms; unresolved rights must remain gated.

The original GitHub recursive-tree API was read at that immutable revision
(metadata only). [Exact proposed files](statsbomb_corpus_proposal.json) contain
126 new event/lineup paths, byte sizes and upstream **Git blob SHA-1** identities.
These are not SHA-256 file hashes. Payload SHA-256 remains explicitly null until
authorized acquisition and verification; no claim of byte verification for unseen
files. Existing pinned metadata/terms hashes are in `statsbomb_source.json`.

## One owner approval request — concrete bounded scope

Approve acquiring the 126 enumerated event/lineup JSON files for the remaining
63 matches of **StatsBomb World Cup 2018**, at the exact revision above, for
local noncommercial source reconciliation, possession/process research and
transparent empirical baseline fitting/evaluation only, under the reviewed
StatsBomb agreement and existing registration attestation?

Execution stages under that single scope:

1. Six-match quality pilot: 8649 Uruguay–France, 8650 Brazil–Belgium,
   8651 Sweden–England, 8652 Russia–Croatia, 8655 France–Belgium,
   8656 Croatia–England; reuse 8658 solely for development checks.
2. Expand to the other 57 enumerated matches only after reviewing pilot defects
   and passing identity, provenance, event preservation and quality gates.
   Stop for ambiguous source semantics or rights; never silently waive failures.

Restrictions: ignored local raw/derived data only, immutable manifests and
SHA-256 per fetched payload, no dataset/screenshot/model redistribution,
publication, deployment, commercial use, external AI upload or provider pooling.
No new provider, competition, revision or xT/VAEP training is covered. No rights
change or production allowlist expansion has occurred in this delivery.
This request comes from the mission's Stage A, which requires owner authorization
before new data acquisition. The proposal JSON is documentation, not an allowlist.

The six knockout fixtures are a biased quality pilot, **not** a statistically
adequate validation sample. Even 64 matches are one men's competition with
repeated teams/players, correlated knockout selection and limited period/season
coverage. Corpus size does not itself establish scientific adequacy.

## Provider adapters and quality contracts

Existing production StatsBomb ingestion retains its reviewed 8658-only gate.
The new `fil.ingestion.wyscout_testonly` adapter accepts explicit TEST_ONLY inputs
only. It preserves numeric native IDs, original array order, original JSON,
native period/eventSec and all native percent coordinates/tags. It joins original
match/team/player metadata, rejects duplicate/foreign IDs and opposing rosters,
records unknown actors, missing positions, clock reversals, lineup/substitution
records and unresolved exposure. It never invents recipients, native possession
IDs, xG, minutes or orientation. Accurate/inaccurate tag mappings are provisional,
separate from StatsBomb's absent-outcome convention; conflicting/missing tags are
explicit. This is a contract scaffold, **not primary-schema certification**.
No provider bytes were acquired to test it. Production use remains disabled.

Pilot acceptance must compare each original JSON event and count to normalized
records, validate provider IDs and match metadata, reconcile scores and source
xG where present, and independently audit roster/substitution/exposure evidence.
Retain anomalous records and null metrics; fail closed on identity corruption.
Report missingness per field, match and provider. Never convert elapsed source
clock exposure into official minutes. Any production Wyscout adapter requires
original documentation and real authorized-file reconciliation first.

## Measurement migration and fixed forecasting contract

Historical possession v1/v2 and corpus v1 artifacts remain intact. New possession
v3 summaries (`fil-process-cooccurrence-2`) replace misleading `*_after_*` keys
with explicit `*_and_*` keys and declare same-native-ID co-occurrence.
The UI now labels this co-occurrence, retaining existing denominators.
`p_shot_given_final_third` and `p_box_given_final_third` remain descriptive
conditional co-occurrence fractions, not event-order transition probabilities.

Corpus v2 includes separate `process.json`, version `fil-process-order-1`:

- Unit: full `(match_id, native possession_id)` membership, before UI filtering.
- Reach: observed owner action start in native ATT/BOX, or completed-pass/
  observed-carry endpoint there. Existing native +x zones; physical orientation
  remains unknown. Missing positions may hide earlier reaches, so the estimand is
  **after the first observed reach**, not after a certified physical entry.
- Shot/box order: original provider index strictly greater than the first
  observed reach's index. A shot at that same record, or a box endpoint on the
  same final-third-reaching action, does not establish a later event.
- Eligibility: observed final-third reach, consistent owner, supported single
  period, no missing/reversing clocks or unassigned/noncontiguous membership.
  Excluded order results are null, with reasons; no observed reach is separate
  from unresolved ordering. Counts and original evidence IDs are retained.
- Equal timestamps retain source sequence but imply no positive elapsed duration.
  Unknown geometry counts are reported; no off-ball or tactical-intent claim.

Predefined outcome window: `fil-next-five-owner-actions-shot-1`. Forecasting time
is **after observing the complete source record** of a completed pass or observed
carry, not before the action. Source timestamps mark the provider event clock,
not a certified time at which endpoint/outcome information was available live.
This is retrospective record-order forecasting, not a live physical-time claim.
The export records the cutoff index, period clock and availability assumption.
Features may use that cutoff
record only in this version; labels inspect exactly the next five owner actions
within the same native possession/period, strictly excluding the cutoff action.
Owner records use the existing explicit action taxonomy (including Ball Receipt*);
a pass and receipt are distinct records, not certified independent ball touches.
Target: any owner Shot in those five actions, excluding shootouts. Fewer than
five future actions, inconsistent order or cross-period membership => censored/
unresolved, null label, even if a shot is already observed in the short chain.
This conservative complete-window cohort is selectively biased toward longer
sequences. Report excluded fractions and do not generalize to all possessions.
It does not estimate an at-any-time possession outcome or on-ball action value.
No outcome definition was selected using held-out performance.

## Real evaluation protocol — pending actual authorized matches

No trained model or held-out score is delivered. TEST_ONLY tests verify contracts;
the 8658 source check verifies source semantics, not predictive generalization.

Freeze a run manifest **before fitting**: source hashes/provider/frame, definitions
and cutoff version, dated whole-match train/validation/test boundaries, development
exclusions, baseline parameters, seeds, missingness/eligibility rules and intended
effect. Split complete matches by source date. Same-day fixtures stay in one
partition. 8658 is development-exposed and programmatically forbidden in validation
or test. Check team/player overlap across partitions and report residual dependence;
chronology alone does not prove independence. No cross-provider pooling.

Compare training-only equal-match constant frequency and predeclared context
(period and score state observed by cutoff), then native location (fixed 6×4 bins
of cutoff endpoint, missing bin separate) and forwardness (endpoint minus origin
+x with fixed bins ≤0, (0,5], (5,10], >10 native units). Include transparent
progression definitions at 5/10/15 units; physical direction uncertainty applies
to all native +x alternatives. No last-action, future possession total, terminal
score or future xG feature. Do not select bins/thresholds using test labels.
Unknown training contexts fall back to training prior and report support.
The baseline fitting/scoring engine already uses inverse-within-match weights;
new geometry features remain evaluation design until authorized validation.

Primary scoring: equal-match Brier/log loss and paired match-cluster differences,
calibration bins with explicit weighting and support; exact impossible predictions
remain infinite-log-loss failures. Use team/competition sensitivity analyses,
learning curves and prospective effect/uncertainty estimates to decide adequacy;
never an arbitrary match threshold. Keep repeated teams' dependence visible.
Small-sample intervals or underpowered comparisons are inconclusive. Freeze test
once; retain negative/unsupported cases and every historical run. xT/VAEP stays
gated on sample adequacy, native action/coordinate support and leakage audits.

## Blinded football usefulness task — design, not completed study

Ask analysts to retrieve the original buildup actions relevant to a nominated
shot and describe observable differences between two fixed match periods. Sample
queries and candidate sets before system comparison; include no-shot/failed
buildup and missing-position counterexamples, and match time budgets.

Compare anonymized randomized/counterbalanced packets: FIL evidence retrieval
versus a simple chronological event ledger plus pass/shot/progression counts.
Keep a separate key concealed from assessors; remove player reputation cues
where feasible and record failed blinding. Both conditions receive identical
source scope; no invented video/tracking ground truth. Independent football
reviewers annotate relevant **source IDs**, factual error/unsupported intention or
causality claims, uncertainty omissions and decision relevance using a fixed
rubric. Adjudicate disagreements blind to condition; report inter-rater agreement.
If independent reviewers are unavailable, mark study pending rather than treating
engineering self-review as analyst validation.

Outcomes: precision/recall of source-event retrieval and evidence completeness,
time to defensible answer, unsupported claims per claim, uncertainty disclosure,
and prespecified ordinal decision relevance. Analyze paired query/analyst results
with match-dependent uncertainty and sensitivity to relevance adjudication.
No player rating, importance ranking or underrated claim is an endpoint. Pogba's
8658 example remains development-exposed exploratory evidence only.
