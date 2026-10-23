# Recorded buildup re-entry investigation — delivery record

Parent: PR #21, `68dbdfd81ceda1ccab042b94548525c65455829c`, branch
`research/fil-comparison-identifiability`. Work branch `research/fil-buildup-reentry`.
This is a focused scientific falsification study, not a new dashboard or player score.
The accepted capability decisions are unchanged; no agent/memory framework added.

## Actual work and interpretation

[Protocol](REENTRY_PROTOCOL.md) was committed before extraction. The implementation
uses a single first-entry landmark per original native membership, equal observation
opportunity, original geometry/sequence, explicit exclusions and two predeclared later-
Shot horizons. It compares volume/location and team-match context, repeat support,
co-occurrence versus ordering, and frozen boundary/annotation sensitivities. No
response, predictive, hierarchical or latent model is fitted. Source xG remains original.

The detailed scientist report is protected local evidence, not part of the Git diff.
It addresses the unresolved football question, competing directions, actual findings,
negative evidence, definition/target sensitivity, independent relevance requirements
and specific owner dependencies. The recommendation is **do not promote the current
operationalization as an effectiveness or repeatable-team measure**; retain its
traceable retrieval only as an unvalidated independent-analyst feasibility candidate.
This is not a finding that physical recycling is beneficial/harmful or that no useful
team processes exist. All current matches remain exposed; no independent scientific
replication or collected human judgment is claimed.

[Independent evaluation/access assessment](REENTRY_EVALUATION.md) specifies the next
human test and records the completed original-source metadata/rights review. It
includes an unsent provider inquiry; no provider or participant was contacted.
Original StatsBomb competition and match metadata were inspected at the approved
revision. No new event/lineup payload, provider, competition dataset or training scope
was acquired/authorized; no production acquisition allowlist changed. Wyscout archives
remain unapproved and Figshare metadata access was not bypassed.

## Reproducibility

From repository root with the existing approved local source files:

```sh
uv run --frozen python -m fil.research.reentry \
  --parent data/interim/comparison-design/fil-player-comparison-design-1/b5842b696814715e0e8500597ca3d02a6a2adfd2 \
  --pipeline-revision fd8ca2fd31e2f178387925b2ef7ca7f0271854c2
uv run --frozen python scripts/verify_reentry.py LOCAL_STUDY_BUNDLE
uv run --frozen python scripts/prepare_reentry_review.py LOCAL_STUDY_BUNDLE NEW_PACKET_DIRECTORY
uv run --frozen python scripts/verify_complete_corpus.py LOCAL_CORPUS_BUNDLE LOCAL_CONFIG
uv run --frozen ruff check .
uv run --frozen pytest -q
uv lock --check
uv build
```

The calculation SHA is the actual code executed, not the later verifier/docs commit.
The original study manifest SHA-256 is
`e16b971b9b554905d100dbbb6e3ca4cdc4c9a24ab4b2516985b9f440d37a3e8b`.
The exact parent/protocol/source hashes are enforced before processing. Re-running
the same calculation preserves artifact bytes and modification times. Historical
source, previous review, frozen-model and evaluation files were checked unchanged.

Local protected package under ignored `data/interim/reentry-study/`:

- `fil-recorded-reentry-study-1/fd8ca2fd31e2f178387925b2ef7ca7f0271854c2/`:
  original-ID evidence for every variant/membership, complete summary, source inputs
  and immutable manifest. `/tmp/fil-reentry.json` points to it.
- Sibling `.independent-final.json`, `.source-reconciliation.json` and
  `.reproducibility.json`: independent source/design and integrity proofs. Earlier
  verification outputs remain preserved.
- `reviews/fd8ca2fd31e2f178387925b2ef7ca7f0271854c2-review2/report.md`: full scientific
  interpretation and original-record positive/counterexamples. Secondary horizon
  diagnostics, a local report builder and manifest are alongside it. The first review
  remains preserved; review2 corrects a formatting typo and adds metadata-version
  limitations without changing the protocol, calculations or evidence.
- `analyst-packets/fd8ca2fd31e2f178387925b2ef7ca7f0271854c2/`: unrun feasibility packet,
  source-only adjudication ledgers, identical condition ledgers/cards, blank judgment
  and answer sheets, planning slots and private machine case map. It is not cleared
  for external participant access. `/tmp/fil-reentry-packet.json` points to it.
- Metadata-only source receipts and exact inventory are separately under ignored
  `data/interim/reentry-metadata/`. Git blob and SHA-256 identities were verified;
  event quality, player continuity and season completeness remain unverified.

`/tmp/fil-reentry-review.json` points to the scientific review; its manifest binds the
exact study, final independent proof, protocol, evaluation specification, metadata
inventory and analyst packet. The final delivery receipt records exact branch/PR/CI.
No protected provider records, numerical research tables or source examples are
uploaded to GitHub or included in package distributions.

## Verification performed

| Check | Actual result |
|---|---|
| Ruff | Exit 0 |
| Editable test suite | **557 passed**, 8.74 s; no failures/skips |
| Fresh regular installation suite | **557 passed**, 9.61 s; no failures/skips |
| Frozen lock agreement | Exit 0; dependencies unchanged |
| Wheel/source build and regular install | Exit 0 |
| Installed re-entry CLI | Exit 0; site-packages import verified |
| Independent raw/landmark/feature/target/stratum/support verification | PASS; includes prior independent parent verification |
| Full original-source/event/score/xG reconciliation | PASS |
| Idempotent rebuild / historical artifact hashes and mtimes | PASS |
| Source metadata Git blob/SHA-256 verification | PASS, metadata only |
| Actual packet audit | Distinct matches, identical source information, blank human labels, local-only restrictions verified |

New TEST_ONLY regression cases exercise original order versus co-occurrence,
failed/null/missing geometry, first-entry uncertainty, pre-landmark Shot exclusion,
annotation-specific horizons, closed negatives versus unresolved tails, unequal Half
End times, period/native-ID discontinuity, source/score/protocol failures, context
overlap, missing outcomes, sparse repeat support and unlabelled packet provenance.
Early test-fixture errors (a synthetic timestamp format and an unclosed test file)
were corrected; no source data, failed scientific outcome or eligibility rule was
changed to obtain a favorable result. Independently checked real examples retain
their exact original events and provider xG.

Hosted CI runs without local protected data and is reported separately from source
verification. No UI changed; no browser, startup or interaction improvement is claimed.
Existing performance/product acceptance and branch-protection limitations remain.
Keep all prior PRs unmerged: no merge, retarget, force push, deployment, publication,
external AI upload, rights waiver or automatic participant recruitment.
