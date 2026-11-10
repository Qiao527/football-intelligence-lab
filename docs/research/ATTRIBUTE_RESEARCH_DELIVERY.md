# Attribute research engineering delivery

Parent: draft PR #18, `research/fil-authorized-corpus`, exact commit
`32cdf25df067ce00da5b6a10783d6f8e01e03137`; its hosted lint-and-test checks passed
before branching. Work branch: `research/fil-attribute-connectivity`. No existing
PR is merged or retargeted; no deployment, rights expansion or acquisition occurs.

## Delivered implementation

- [Framework](PLAYER_ATTRIBUTE_RESEARCH_FRAMEWORK.md): measurement versus ability,
  opportunities, validity, dependence, failure criteria and future read-only analyst
  boundary. No agent or dashboard implementation.
- [ATTRIBUTE_REGISTRY](../../src/fil/research/attribute_registry.json): three versioned
  candidate specifications with strict packaged validation and allowed statuses.
- [Exploratory study](ATTACKING_CONNECTIVITY_STUDY.md) and
  [validation roadmap](ATTRIBUTE_VALIDATION_ROADMAP.md): actual corpus observations,
  negative evidence and exact future independent-validation requirements.
- `fil.research.connectivity`: source/metric gates, immutable input verification,
  completed-pass and ordered-chain extraction, original-event linkage, baselines,
  contextual support, outcome-blind selection, dependence/sensitivity diagnostics
  and a local-only human evidence report. Source facts are never altered.
- `scripts/verify_connectivity.py`: independently scans raw JSON with a state
  machine, checks source/metadata bindings, native geometry, original order and
  recipients, exact later Shots/alternatives, baseline counts, conditional
  denominators, pre-event goals and context, selection and redundancy arithmetic.
  It imports no production extraction/calculation functions.
- 29 additional regression cases; CI checks the installed CLI and packaged registry.
  No dependency or lockfile change.

The protocol was committed before executing this extraction, but the existing
corpus is development-exposed. This is an exploratory study, not independent
confirmation. The original frozen PR #18 study is unchanged; no new forecasting,
hierarchical player model, xT/VAEP, ability score or ranking is fitted.

## Real findings

The corpus reconciles **64 matches / 227,825 original events**. There are **50,167**
roster-valid completed passes and **25,252** eligible ordered chains across **6,006**
native memberships. Those chains reuse **36,321** distinct passes and reference
**956** distinct later recorded Shots; neither chains nor linked Shots form
independent action trials. Of **736** rostered IDs, **603** have observed actor or
received-pass evidence; **588** appear as chain intermediaries. There are **1,787**
active player-match rows and **178** players meet diagnostic support requirements.

The primary cross-zone non-return count is **18,967**, dropping to **14,138** on a
coarser grid. Completed-pass volume correlation is **0.905130**; received volume
correlation is **0.857450**. Fourteen within-team-match pairs share both volume
counts but differ in the descriptor. This is observable non-equivalence to two
counts, not incremental football validity. All matches form **one** team/player
dependence component. No population interval or stable-ability claim is certified.
The scientific verdict is **INCONCLUSIVE**.

Full player comparisons, exact positive/counterexample IDs and per-action evidence
are local, ignored artifacts, not part of the Git diff. Empty role metadata,
unsupported native memberships, original pass exclusions and counterexamples are
retained. Exact physical exposure/direction, official minutes, per90 and stable
roles remain unavailable. No off-ball movement, intention or causal importance
is inferred. See the study for all reported failures and context limitations.

## Reproduction and checks actually run

Run from the repository root with Python 3.11. The approved source corpus must
already exist locally; this command performs no acquisition. Reproduction is not
new untouched confirmation. The actual calculation revision is
`6da53c8c29b797847fcd6c64be616dd42edebfd6`; later documentation commits do not
relabel it. `/tmp/fil-connectivity.json` points to the local immutable bundle.

```sh
uv run --frozen python -m fil.research.connectivity \
  --corpus data/interim/accepted-corpus/corpus/a44ebe2d87093584ba44541fc26a0a42d9f62b84 \
  --pipeline-revision 6da53c8c29b797847fcd6c64be616dd42edebfd6
uv run --frozen python scripts/verify_connectivity.py \
  data/interim/attribute-research/fil-attacking-connectivity-1/6da53c8c29b797847fcd6c64be616dd42edebfd6
uv run --frozen ruff check .
uv run --frozen pytest -q
uv lock --check
uv build
```

Set `UV_CACHE_DIR=/tmp/fil-uv-cache` in this managed environment. An empty regular
installation was created at `/tmp/fil-attributes-wheel-env` using
`UV_PROJECT_ENVIRONMENT=/tmp/fil-attributes-wheel-env uv sync --frozen --no-editable
--reinstall-package football-intelligence-lab` (with the managed Python installation
directory set). Then run lint, tests, CLI help and registry loading with
`uv run --frozen --no-editable` and that environment. Its imported package path is
under that environment's `lib/python3.11/site-packages`, not the source checkout.

| Verification | Actual result |
| --- | --- |
| Ruff / lock agreement / wheel and sdist build | Exit 0 |
| Full editable tests | **495 passed**, 10.24 s; no failures/skips |
| Empty-environment regular installation tests | **495 passed**, 12.02 s; no failures/skips |
| Installed CLI help / three packaged definitions | Exit 0 |
| Independent connectivity raw-source verifier | PASS, all 64 matches / 25,252 chains |
| Independent full corpus / conditional census verifier | PASS, 227,825 unique compound source IDs |
| Original France–Croatia fixture | 2,978 events; official 4–2; source xG 2.5782512977 |
| Identical extraction rebuild | 485 selected protected/output/model/evaluation files retain bytes and mtimes |
| Earlier original-fixture preservation inventory | All 23 files retain recorded bytes and mtimes |

The final source reconciliation proof, independent connectivity proof and
reproducibility proof are immutable sibling local JSON files. A new extraction
completed in **10.996 s** in this environment; an exact rebuild and preservation
check took **10.653 s**. These are research pipeline observations, not controlled
performance comparisons or product browser benchmarks. No startup or interaction
improvement is claimed. Existing product performance/human-acceptance limitations
remain visible; no UI changed, so no browser/screenshots were needed or claimed.

Self-review tightened malformed registry field-type handling and added regression
cases. Source corruption stops before output creation. Regression coverage also
checks explicit-null/failed pass interruption, own-goal and future-score semantics,
period/membership ambiguity, missing geometry, actual alternative paths and absent
opportunity. An initial TEST_ONLY Shot fixture omitted its required source `type`;
the fixture was corrected without weakening production score validation. No failed
result was reinterpreted as a pass.

Hosted CI and final branch SHA are reported with the PR delivery after push; local
checks are distinct from hosted results. Existing branch protection/merge conditions
are unchanged, and every current PR remains unmerged.

## Rights and unavoidable external dependency

The existing source agreement, owner registration attestation, attribution duties
and local noncommercial scope remain binding. Raw/provider-derived player evidence,
models and source-linked examples stay under ignored `data/`; none is redistributed,
deployed or uploaded to an external AI service. No additional training rights,
model weights publication or Wyscout archive is approved.

The environment still does not list `api.figshare.com`. Its current readiness state
is unknown, so successful metadata access is not asserted. The existing precise
administrator action remains metadata-only HTTPS allowlisting for that host; no
repeat denied request, bypass or substitute mirror was attempted. No new owner
approval is needed for the completed descriptive StatsBomb work. Independent
cross-league replication and any additional model fitting will require exact
source/usage review and separate authorization before execution.
