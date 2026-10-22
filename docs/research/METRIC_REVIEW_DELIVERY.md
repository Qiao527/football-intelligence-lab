# Metric-specific quality and prospective research delivery

Parent: draft PR #16 at `b204ada492c09ad36e6552f3f7097967bb15e129`.
The existing expansion gate remains **BLOCKED**. No additional source payloads
were acquired, no prior artifacts replaced, no original experiment rescored,
and no existing PR merged/retargeted. No UI, rating or action-value model is added.

## Implemented and proposed

- [Eligibility matrix](METRIC_ELIGIBILITY.md): independently testable source,
  native order/score, geometry, known-completion and source-clock contracts.
  Match 8656 remains the real regression case. Same-period source arithmetic is
  separated from conditional boundary/exposure envelopes and blocked physical
  orientation, official minutes and per90. Diagnostics do not alter operational
  acquisition or DATA-* gates.
- [Frozen prospective study](PROSPECTIVE_PROTOCOL.md): recorded-shot-before-segment-
  closure target, confirmed positives/negatives and unresolved observations,
  strict future source evidence, possession-balanced weights and chance-evidence
  missingness. Its first commit predates new label audits. All seven held matches
  are explicitly exposed, including the previously consumed 8655 test match.
- New transparent baseline primitives enforce training-only fit, source/match
  separation, feature cutoff checks, unit match weights, prior/bin shrinkage and
  unsupported-bin fallback. They were run only on TEST_ONLY examples; no new
  real-model predictions or performance scores are presented. Hidden feature
  generation still requires independent code/lineage audit.
- Dependency components join any matches sharing a team or player. Conditional
  match and size-weighted component resampling never certify independence;
  missing identity or one component withholds the component interval. Analyst
  crossover/retrieval design includes a simple-ledger comparator, independent
  relevance adjudication, unsupported claims and uncertainty. Human effect sizes,
  study power and analyst acceptance are still unestablished; no study is run.
- [Original Wyscout audit preparation](WYSCOUT_PRIMARY_AUDIT.md): metadata-only
  inventory parser/tests and a bounded future World Cup research scope. Original
  article versions, file inventory, individual terms and primary-paper CC BY 4.0
  cross-check remain unavailable. No exact archive approval request is fabricated.

## Actual verification and limitations

Independent raw-array verification reconciles the new cutoff labels and original
IDs against all **24,805** held records. It reruns PR #16's independent 16-scenario
verification and PR #15's complete source reconciliation. The original 8658 fixture
remains 2,978 events, official 4–2, source xG 2.5782512977. Original v1 still rejects
8656's conflicting Half End timestamps. The old pilot gate and inputs remain intact.
These are source/engineering checks on development-exposed records, not new
predictive validation or independent analyst judgement. Derived evidence stays
under ignored `data/interim/metric-review/`; nothing is uploaded as a dataset.

The future exact-ID/date/file-identity manifest is generated from already verified
match metadata and the unchanged approved enumeration, without opening any of the
remaining payloads. It fixes **40 train / 12 validation / 5 test** matches, excluding
all seven exposed matches. Its payload SHA-256 values remain null until authorized
acquisition; upstream blob identities/sizes are retained. Five future test matches
are a serious support limit, not an adequacy guarantee. Team links already produce
only four connected components across the proposed 57; player overlap is unknown
without the unacquired lineups. These are metadata facts, not outcome inspection.

The new target removes the old five-future-annotation requirement; it does not
remove variable horizons, annotation density, overlapping shot evidence, selection
or provider-specific possession semantics. Missing-label extremes are descriptive
support bounds, not confidence intervals. Source-record negatives never certify
that no physical chance occurred. No causal credit or player importance follows.

451 tests pass in editable and freshly rebuilt regular installations; lint,
frozen lock validation, wheel/sdist build and installed CLI help pass. Tests include
a regression proving that a proposed metric artifact cannot unlock the unchanged
acquisition executor. A stale cached local wheel was detected by installed tests;
rebuilding with `--reinstall-package football-intelligence-lab` resolves it, and
CI now explicitly requires that rebuild. Hosted CI is reported separately at
the delivered branch SHA.

## Local reproduction

```sh
uv run --frozen python -m fil.research.metric_review \
  --parent-review /tmp/fil-temporal-review.json \
  --reference-raw /absolute/verified/original/8658/raw \
  --pipeline-revision FULL_BRANCH_SHA
uv run --frozen python scripts/verify_metric_review.py \
  /absolute/new/bundle /absolute/verified/original/8658/raw /absolute/original/config.json
uv run --frozen ruff check .
uv run --frozen pytest -q
uv lock --check
uv build
UV_PROJECT_ENVIRONMENT=/tmp/fil-metric-wheel uv sync --frozen --no-editable \
  --reinstall-package football-intelligence-lab
UV_PROJECT_ENVIRONMENT=/tmp/fil-metric-wheel uv run --frozen --no-editable pytest -q
```

The local delivery pointer is `/tmp/fil-metric-review.json`; it is environment
evidence, not a committed data artifact. Content-addressed outputs record code,
method and policy hashes, parent evidence and exact input/output digests. Repeat
generation checks identical bytes and preserves prior file modification times.
No new browser/performance claim is made because this delivery changes no UI.

## Only outstanding owner/environment decisions

1. Review the versioned metric-specific policy before **any** expansion. This PR
   proposes it; acceptance of the forensic PR did not authorize a replacement gate.
   No execution approval is inferred from code/tests or acceptance of this design.
2. The previously identified environment action remains **api.figshare.com** in
   the managed outbound allowlist. Current policy is enforced and still omits it;
   the denied request was not repeated or bypassed. Metadata access is separate
   from subsequent source-specific Wyscout rights review and archive authorization.

Nothing requires a timing-tolerance override, plan purchase, public data release,
deployment, external AI upload, model-weight publication or xT/VAEP approval.
