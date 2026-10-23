# Connectivity falsification engineering delivery

Parent: draft PR #19, exact commit
`d5a0e833f3eafdf2c3cf45a1b85702d9c59515a1`. Work branch:
`research/fil-connectivity-falsification`. One focused audit; original descriptor,
registry, source records, eligibility policy, earlier results and frozen studies
remain unchanged. No new model, dashboard, runtime agent, source acquisition,
player score, merge, retarget, deployment or rights expansion.

## Implementation and reproducibility

[Protocol](CONNECTIVITY_FALSIFICATION_PROTOCOL.md) was committed before the new
calculations. All data is development-exposed; this does not make a new independent
confirmation set. Its file hash is enforced, and the exact delivered PR #19 evidence
manifest is pinned. Missing source/parent identity or changed original metric stops
processing. The CLI only reads existing approved files; it performs no acquisition.

`fil.research.connectivity_falsification` adds:

- Complete roster/player-match opportunity decomposition and zero/null support.
- Incoming, receipt-proxy/release, observed-receipt/release and outgoing component
  comparisons, with original native coordinates and all original IDs.
- Nested/shifted grids, continuous native separation, predeclared thresholds and
  explicit eligibility variants; every rejected candidate pair is retained.
- Descriptive baseline correlations/ties, native possession and pre-event score
  strata, last-observed native position evidence, common support and sparse samples.
- Exact retrospective partition sums of squares, with definitional tautologies
  distinguished from empirical context effects. No explanatory/predictive model fit.
- Deterministic original-event agreements/counterexamples and local-only reports.

`scripts/verify_connectivity_falsification.py` independently scans raw records,
regenerates candidate pairs and alternative geometry, checks the earlier independent
parent verifier, rational partition arithmetic, opportunity denominators, context
support, correlations and sensitivity totals. It imports no production calculation.
TEST_ONLY regression cases cover endpoint cancellation, intermediary disagreement,
nested boundaries/offsets, null geometry, eligibility and receipt ambiguity, source
order of position annotations, frozen protocol and original-metric preservation.
A self-review defect in explicit-null Dribble handling was fixed with regression
cases: unknown/null semantics remain ineligible instead of raising an exception.
No current corpus result changed after that fix; initial and final evidence/summary/
report bytes agree. No failing result was reinterpreted or source field repaired.

Run from the repository root, Python 3.11, frozen dependencies:

```sh
uv run --frozen python -m fil.research.connectivity_falsification \
  --parent data/interim/attribute-research/fil-attacking-connectivity-1/6da53c8c29b797847fcd6c64be616dd42edebfd6 \
  --pipeline-revision 376e928980ff1d0d3ef3a220af212ac679919036
uv run --frozen python scripts/verify_connectivity_falsification.py LOCAL_AUDIT_BUNDLE
uv run --frozen ruff check .
uv run --frozen pytest -q
uv lock --check
uv build
```

The actual calculation SHA and bundle paths are in `/tmp/fil-falsification.json`
and the final local delivery receipt. A later documentation-only commit is not
represented as the calculation revision. Reproduction verifies exposed artifacts;
it does not restore untouched observations. With `UV_CACHE_DIR=/tmp/fil-uv-cache`,
a clean regular environment is installed using `uv sync --frozen --no-editable
--reinstall-package football-intelligence-lab` and a fresh `UV_PROJECT_ENVIRONMENT`.
Then run lint, tests and installed CLI help with `uv run --frozen --no-editable`.
CI also checks the installed audit CLI. Dependency manifest and lockfile are unchanged.

## Protected local research package

The user prohibits public provider-derived data. Numerical research tables,
player/chain records, exact event examples and scientific interpretation are **not
included in this Git diff or PR body**. They are under Git-ignored
`data/interim/connectivity-falsification/`:

- `fil-connectivity-falsification-1/<calculation SHA>/audit.md`: computed audit report,
  complete sensitivity/opportunity/attribution results and original-event examples.
- `summary.json`: all per-player denominators and retrospective strata, nulls,
  exclusions, baseline redundancy, sparse support and sensitivity distributions.
- `evidence.json`: every candidate pair and admitted chain, original source IDs,
  components, source position evidence and versioned eligibility outcomes.
- `manifest.json`: exact parent/protocol/source/input/output identities and code SHA.
- Sibling independent verification, full-source reconciliation and reproducibility
  proofs; earlier runs remain intact.
- `reviews/<calculation SHA>/review.md`: scientific interpretation authored after
  examining results, with a separate manifest binding the exact audit and proof.
  `/tmp/fil-falsification-review.json` points to this local review.

The explicit scientific recommendation is **REVISE the descriptor's presentation**,
not a replacement score or automatic upgrade. Retain precise source-order retrieval
and show opportunity/component facts. The current standalone scalar is not evidence
of a measured distinct player ability. Keep the construct INCONCLUSIVE; retire its
ability interpretation. The local review states conditions for retaining a useful
descriptive sequence metric and for retiring an unsuccessful operationalization.
Its numerical evidence and counterevidence are local and source-traceable.

New independent evidence requires an untouched authorized league/season population,
adequate comparable opportunities/roles or certified exposure, predeclared clustered
reliability/context comparisons, independent football relevance annotation and
blinded utility comparison against a searchable ledger. New predictive/hierarchical/
latent modeling requires specific source/modeling authorization review first.
No causal attribution, player ranking, physical direction, tracking movement,
certified minutes/per90 or independent confirmation is claimed.

## Integration audit and limits

[Read-only integration audit](CONNECTIVITY_INTEGRATION_AUDIT.md) records existing
PR/base/head ancestry, hosted status, legacy component overlap and the unprotected
main branch. Successful checks/current mergeability do not satisfy the mandatory
merge guard or scientific/product acceptance. No previous PR is changed.

No UI or browser flow changed, so no browser screenshots/performance result is
claimed. Existing product startup, interaction and human-acceptance limitations
remain visible. Research execution/verification times are not product benchmarks.
Provider files, derived reports, models and source-linked examples remain local;
none is redistributed, published to GitHub or sent to external AI services.

## Final local validation

| Check | Actual outcome |
| --- | --- |
| Ruff | Exit 0 |
| Frozen lock agreement | Exit 0 |
| Full editable suite | **521 passed**, 15.23 s; no failures/skips |
| Fresh regular installation suite | **521 passed**, 16.10 s; no failures/skips |
| Wheel and source distribution build | Exit 0 |
| Installed audit CLI help | Exit 0; package imported from site-packages |
| Independent raw-source audit and preserved parent verification | PASS |

The clean regular environment was `/tmp/fil-falsification-final-wheel-env`; the
managed Python installation directory was explicitly selected. Final source and
idempotence proof identities, hosted CI status, branch SHA and PR URL are recorded
in the local delivery receipt and reported with delivery. Hosted CI is distinct
from the local protected-data verification; provider-derived artifacts are not
uploaded to CI. No product performance improvement is claimed.
