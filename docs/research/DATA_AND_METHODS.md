# Data rights and action-valuation method review

Reviewed 2026-10-22. Source documents are pinned below; downloaded reference text
stays in ignored `data/interim/research-literature/`. No new match was acquired.
Public availability is not a rights grant; software and data licences differ.

## Dataset audit and actual permitted corpus

| Source | Evidence inspected | Scope and remaining restriction | Decision |
| --- | --- | --- | --- |
| StatsBomb/Hudl Open Data | Pinned `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb` README + 2023-09-08 Public Data User Agreement, hashes in existing `statsbomb_source.json`; SOURCE_POLICY.md records owner registration attestation | Local noncommercial analysis of match 8658 only in current project approval. Restrictions include commercial exploitation and data redistribution; publication additionally needs branding/attribution review. MIT on FIL does not relicense data. | Exact existing manifest is the only production corpus allowlist entry. No additional-match authorisation inferred. |
| Wyscout/Pappalardo public event dataset | [Processed mirror README](https://github.com/koenvo/wyscout-soccer-match-event-dataset/blob/ebc4c54c1093c420a81ce442c69e4186fab33bb4/README.md), SHA `bcbc4483f4b917a266484e31bb20f122a428d401681c4e8ef50745be3a727d3d` | Mirror states CC BY 4.0; points to original figshare collection DOI `10.6084/m9.figshare.c.4415000` and paper DOI `10.1038/s41597-019-0247-7`. CC BY, if confirmed for exact files, requires attribution, licence link and change notices and does not settle other rights. Mirror is processed, not a substitute for primary licence/file review. Original file-specific scope not independently established in this session. | Potential corpus, not acquired/approved. Review primary release/version/attribution and provider transformations before adding. |
| Metrica Sports sample data | [Provider README](https://github.com/metrica-sports/sample-data/blob/e706dd506b360d69d9d123d5b8026e7294b13996/README.md), SHA `fa4b178e62c4d3559e13b6d3a4fdd42e45293461c2ab656e05a13360a6adcbcf` | README permits community exploration and asks public acknowledgement; not a complete explicit redistribution/commercial grant. Describes anonymised, synchronised event/tracking samples and native 0–1 frame, 105×68 pitch. A root `LICENSE` request was 404; this does not prove no other legal document exists. | Useful potential spatial-validation source, but licence scope incomplete and no project acquisition authorisation; no events/tracking fetched. |
| socceraction | [Original maintainers' MIT licence](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/LICENSE.rst), SHA `9d797bf10fa078933563dba791f9d04dcf66b1827744e7242eee71b80d717532` | MIT covers package/code, not StatsBomb/Wyscout/Opta data or provider services. | Method documentation/code read; no new dependency installed, model executed or data loader invoked. |

The source audit is deliberately bounded, not an exhaustive claim that every
available dataset is legally usable. The one unavoidable future decision is the
owner's precise additional-corpus scope plus source-specific rights review. This
work does not request that decision again or block the approved fixture work.

## Original-method sources and access limits

Original VAEP authors: Decroos, Bransen, Van Haaren & Davis (KDD 2019),
*Actions Speak Louder than Goals*, DOI `10.1145/3292500.3330758`.
Original xT: Karun Singh, *Introducing Expected Threat*, 2019,
`https://karun.in/blog/expected-threat.html`.
The original blog request returned HTTP 403; it was not repeatedly retried.
Full original paper/blog reading is not claimed. Original VAEP authors'
maintained method documentation and reference implementations were inspected,
and xT's documented reference implementation was inspected. This supports method
comparison, not pretending that original xT full-text review or empirical model
validation is complete. Those remain prerequisites before model implementation.

All following code/docs pinned at socceraction commit
`93a1242d46c104889205753accaabadb00c45c6d`:

- [xT docs](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/docs/documentation/valuing_actions/xT.rst), SHA `06633ad18fe2f000c49010018309367faeb1803f114e059b10909fc7da1c8f0f`.
- [VAEP docs](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/docs/documentation/valuing_actions/vaep.rst), SHA `dbbfbd29401b8bc002a307227c803912fdcb64ede598fa81890296e18c3748e7`.
- [xT code](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/socceraction/xthreat.py), SHA `35ebec9b3e171eccf1db5c519ca133886f65411e8e3fa6754111a4f45cc96453`.
- [VAEP labels](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/socceraction/vaep/labels.py), SHA `c31dce2b4aaf57903c54a8c852f1e34d33f9a7137c49c363900647eba8b112f8`.
- [VAEP formula](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/socceraction/vaep/formula.py), SHA `aaf4077b1b7a97684087a7ae1fee87f18f8a0e1582b6e56259bb4258cc42dd1b`.

## Comparison and model-readiness cards

| Method | Meaning / assumptions | Baseline and empirical gates | Current status |
| --- | --- | --- | --- |
| Completion/volume/forwardness | Observed supported actions and native Δx; no calibrated value | Coverage, opportunity/context, source lineage, sensitivity | Computed on fixture, descriptive only |
| Progression 5/10/15-unit rules | Project-specific native geometry, successful-pass/carry selection | Compare volume and positive Δx, inspect shot-followed evidence, role/state/starting-zone adjustment on held-out matches | Actual local case comparisons, exploratory; no calibrated value |
| Training-only equal-match prior / context frequency | Probability of a precisely defined outcome; context known by forecast cutoff; unseen context falls back to training prior with flag | Untouched matches, Brier/log loss, fixed-bin calibration, rare-outcome coverage | Implemented and tested on TEST_ONLY contracts; no real multi-match evaluation |
| xT | Location-only grid/Markov possession model; successful ball-retaining moves valued as V(end)−V(start) | Approved multi-match training, orientation/action adapter, transition support, grid/smoothing sensitivity, untouched match comparison to location/volume baselines; not just agreement with training table | Not fitted/implemented as FIL action values; prerequisites absent |
| VAEP | Difference in score/concede state probabilities from the possessing team's perspective; richer recent-action context | Defined action representation, label horizon, model card/registry, match/time holdout, calibration, leakage audit, team-switch handling and simple contextual baselines | Not trained; approved independent corpus/goal support absent |

The reference xT procedure converts provider events to SPADL, declares a common
attacking frame, fits a 16×12 grid and rates eligible successful moves. Do not
blindly apply a second direction flip to already provider-normalised coordinates.
A fixed endpoint-progression gain is not an xT estimate. Unsuccessful moves cannot
be assigned successful-move xT deltas without a separate turnover-value definition.
Grid Markov/location sufficiency assumptions ignore pressure, options, score,
player traits and much off-ball context. Sparse transition zones need uncertainty.

Reference VAEP uses recent action states and score/concede probabilities. Exact
implementation matters: `nr_actions=10` labels include the current action and
nine shifted outcomes; these are not automatically interchangeable with a strict
future-shot target. The formula swaps perspectives when teams change and resets
previous probabilities in particular phases; it includes fixed penalty/corner
priors. These constants must not be silently transferred as calibrated FIL values.
Audit period tails, own goals, restarts and whether post-action results are part
of the declared state/target before deciding what constitutes feature leakage.
Our strict-future feature-lineage checker is not a full VAEP conformance validator.

No model weights, xT grids, VAEP values or player value sums were generated. No
complex model has been claimed to outperform a baseline. The current data cannot
support that experiment honestly.


## Multi-match readiness follow-up

See [primary-source audit and approval proposal](CORPUS_READINESS.md). Figshare
original terms/file hashes remain unverified because its primary API is blocked.
The 126 enumerated new StatsBomb files are proposed only, not acquired or allowed.
No Wyscout licence or unrestricted machine-learning permission is inferred.


## Later approved pilot execution

The owner conditionally approved PR #14’s exact StatsBomb file scope on
22 October 2026. See [real pilot delivery](WORLDCUP_PILOT_DELIVERY.md) and
[SOURCE_POLICY.md](../SOURCE_POLICY.md) for the subsequent acquisition and
blocked expansion gate. Earlier pending-authorization/one-match descriptions
remain historical records. The original config-based CLI retains its 8658-only
registry; the new approved pilot command verifies the exact enumerated scope.
