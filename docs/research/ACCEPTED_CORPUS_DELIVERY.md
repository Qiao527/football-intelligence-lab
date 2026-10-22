# First complete local World Cup research corpus

Parent: draft PR #17 at `a6f64008a352689620971de4887cd48a431d43c9`.
The owner explicitly accepted its metric policy and conditionally authorized the
existing remaining 57 matches. No earlier PR is merged/retargeted; no deployment,
provider-data redistribution, rights expansion or model publication is performed.

## Delivered source and quality evidence

**64 real matches, 227,825 original events.** The acquisition contains exactly the
63 originally enumerated additional matches (126 event/lineup files, 191,244,134
payload bytes) at `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`, plus the existing
8658 reference. Expansion itself acquired only the remaining **114 files/57 matches**.
All immutable original JSON, IDs, provider order/times/coordinates, raw manifests,
SHA-256 and upstream blob identities remain local and Git-ignored.

A new `fil-accepted-metric-pilot-gate-1` binds the accepted policy anchor/file hash,
original enumeration/revision, six source manifests, new per-metric reports and
independent verifier/proof hashes. It passed before expansion. Historical BLOCKED
gate/report/clock artifacts remain unchanged. Acquisition checks the new bindings
before each match; regression tests reject missing proof, altered source/report/
policy, inconsistent metric outcomes and attempts to promote an old BLOCKED gate.

All 63 acquired matches pass the named source-record research domains. The
combined inventory also binds the already verified development-only 8658 fixture.

| Domain, among 63 new matches | Result | Meaning |
| --- | --- | --- |
| Source identity/preservation, provider order, native-order score | 63 supported | Raw records/official match-play scores reconcile |
| Native spatial event geometry | 63 supported | Original provider frame only; no flips |
| Within-period source arithmetic / known-duration boundary invariance | 63 supported | Source-clock facts, not physical timing certification |
| Cross-period boundary / recorded-census envelopes | 63 conditional | Source-marker scenarios only; physical containment remains uncertified |
| Physical direction/tracking, official/exact exposure and per90 | 63 blocked | Unavailable, never zero-filled or certified |

Original roster/actor/recipient/replacement identity joins pass; recorded census
checks report no unresolved transition issue. Independent interval integration
reproduces every conditional player exposure range at endpoint scenarios. Unused
roster and official minutes remain null. No cross-match player/team ID conflict
is found. Source match-play xG has no missing/invalid values in the 63 new matches;
the quality inventory retains exact Shot IDs and null counts for every canonical
field. Shootout success remains separate from official match-play scoring.

The original 8658 fixture remains **2,978 events, France 4–2 Croatia, source xG
2.5782512977**. Independent streaming reconciliation checks every combined row's
original JSON/identity against source, not only aggregate totals.

### Failures retained, not overwritten

The fixture-limited recognizer initially quarantined documented `Bad Behaviour`
and `50/50` pilot records. Initial development reports quarantined 16 matches
containing `Offside`. Primary specification review verified type IDs 24/33/8 before
new assessments; the original canonical warnings and first-pass failures remain.
[Context semantics review](CORPUS_CONTEXT_SEMANTICS.md) records exactly what was
reviewed. No attribute ID remapping, inferred turnover or new possession-closure
rule was introduced. No held-out predictive result selected these schema decisions.

The new target has **507 unresolved cutoffs among 96,450 cutoffs** across the 63
new matches, due to unsupported/cross-period native membership. They stay null
and excluded from supervised loss; they are not negatives. Missing-label bounds
and all exclusions are reported. Conditional envelopes and unavailable physical
outputs remain explicit even when source-record gates pass.

## Genuine held-out baseline execution

The PR #17 study/partition document remains byte-identical. All seven exposed
matches are excluded from **every confirmatory partition, including training**.
The 40 training and 12 validation matches were acquired/verified first. Seven
models were frozen and independently verified before any of the five test event/
lineup payloads was acquired. Test acquisition itself requires the frozen model
manifest and independent development proof. No post-test fitting or parameter
selection occurred; the old five-owner-action experiment remains unchanged.

The independent verifier recomputes source features and training/validation
probabilities with rational weights, including prior-score evidence strictly
before cutoff. It checks the selected parameters, final predictions, per-match
Brier and weighted reliability. JSON roundtrip model-overlap leakage was detected
and fixed with a regression test **before** held-out acquisition.

Primary loss weights match → labelled possession → cutoff, as frozen. Alpha:
context/location 0.25; forwardness/gain alternatives 4. The constant uses the
predeclared training-only match-unit prior regularization (prior 0.1433395360).
This regularization has small-sample bias and is not a provider xG model.

| Predeclared baseline | Test primary Brier ↓ | Improvement over constant ↑ |
| --- | ---: | ---: |
| Constant prior | 0.135706 | 0 |
| Period × pre-event score state | 0.135897 | −0.000191 |
| Native endpoint location | 0.113794 | +0.021912 |
| Native forwardness bins | 0.135965 | −0.000260 |
| Native gain ≥5 | 0.136030 | −0.000324 |
| Native gain ≥10 | 0.136025 | −0.000320 |
| Native gain ≥15 | 0.136040 | −0.000334 |

These scores concern the **new recorded-Shot-before-observed-closure target**;
they cannot be numerically compared with the historical five-record target's
scores. All candidates are reported, including negative findings. No hard-zero
probabilities or infinite log loss occur under the predeclared smoothing. Constant
versus location log loss is 0.443343 versus 0.375933. Complete reliability deciles,
stratum support, retrieval-at-10 diagnostics and sensitivity scores stay local.

The five test matches have 8,313 cutoffs: 1,414 positive, 6,853 negative, **46
unresolved**. There are 145 distinct linked Shots and 128 positive possessions;
up to **76** cutoffs share one Shot. These are not 1,414 independent positive trials.
All 8 test teams and 177 rostered provider player IDs also occur in training.
The test matches form only **3** connected team/player dependence components.

The location improvement's match-resampling interval is [0.014854, 0.028969],
conditional on these five observed matches and the resampling assumptions.
Component resampling and leave-one-test-team-out sensitivity are also reported;
three components cannot establish reliable general inference. Context and native
forwardness/gain alternatives lose to the prior, and their conditional intervals
include zero. No unseen-team, season/league, physical-chance, causal-action or
player-value conclusion is established. **Scientific status remains INCONCLUSIVE;
independent analyst usefulness has not been evaluated.**

## Reproduction and local artifacts

Entry points (Python 3.11, frozen lockfile):

```sh
uv run --frozen python -m fil.research.accepted_corpus --help
uv run --frozen python -m fil.research.corpus_expansion --help
uv run --frozen python -m fil.research.corpus_baselines --help
uv run --frozen python -m fil.research.complete_corpus --help
uv run --frozen python scripts/verify_accepted_corpus.py REPORT_LIST ORIGINAL_RAW
uv run --frozen python scripts/verify_corpus_baselines.py MODEL_FREEZE [EVALUATION]
uv run --frozen python scripts/verify_complete_corpus.py CORPUS ORIGINAL_CONFIG
uv run --frozen ruff check .
uv run --frozen pytest -q
uv lock --check
uv build
```

`/tmp/fil-complete-corpus.json`, `/tmp/fil-corpus-model-freeze.json`,
`/tmp/fil-corpus-evaluation.json` and `/tmp/fil-accepted-gate.json` point to local
content-addressed evidence. Full quality/provenance, canonical Parquet, raw files,
models, predictions and independent proofs remain under ignored `data/`.
Phase artifacts retain their actual implementation SHAs; no result is relabelled
as produced by a later documentation commit. Reproduction after test exposure
can verify frozen artifacts, not create a new allegedly untouched model freeze.

No browser/performance result is claimed: no UI was changed. Existing product
startup/interaction limitations and human acceptance remain unchanged. Current
test/CI evidence and final branch SHA are reported with delivery.

Local validation: **466 passed** editable (10.83 s) and freshly rebuilt regular
installation (11.96 s), no failed/skipped tests. `ruff check .`, `uv lock --check`,
wheel/sdist build and all four installed CLI help checks exit 0. Independent
source/batch, rational baseline and complete-corpus/conditional-census verifiers
pass. Repeat corpus generation preserves bytes and modification times for **540**
protected/output files; all **23** original fixture files retain their earlier
hashes and modification times. Historical BLOCKED evidence remains intact.
Test runtimes are validation observations, not product performance measurements.

## Rights and remaining external dependency

The reviewed StatsBomb research interpretation, registration attestation,
attribution duties and all owner restrictions remain binding. This is not an
express general model-training licence or permission to distribute provider data.
No xT/VAEP, ratings, external AI uploads, weight publication, deployment or merge.

Figshare metadata remains unavailable because enforced environment policy still
omits **api.figshare.com**. No denied-operation retry/bypass or Wyscout archive
acquisition occurred. The metadata inventory and paper CC BY 4.0 cross-check must
wait for that existing administrator allowlist action. No additional StatsBomb
owner decision is needed for this completed, already authorized scope.
