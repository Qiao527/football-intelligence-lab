# FIL-002 acquisition and verification evidence

## Scope and source identity

Merged foundation baseline: `cde6c66` (PR #2). Implementation branch:
`feat/fil-002-data-acquisition`. Verified implementation commit:
`21e5eff28ab769e0aac61d2d24f0ca7dbd5c2261`; later changes finalize documentation.
Python 3.11.14, uv 0.12.23, pytest 8.4.2, Ruff 0.14.0, uv_build 0.9.5.
No dependencies added; pyproject/lock, original reference documents and LICENSE
remain unchanged.

Official upstream: `https://github.com/hudl/open-data`.
`git ls-remote https://github.com/hudl/open-data.git HEAD` returned pinned SHA
`4b73468fc5b0f1950f9f66fada70ad3a4f9327cb` (exit 0).
All requests used the revision rather than the moving default branch.

Verified from `data/matches/43/3.json`, with competition/season cross-checks
against `data/competitions.json` and team checks against `data/lineups/8658.json`:

| Field | Source record value |
| --- | --- |
| Match ID | 8658 |
| Competition | 43 — FIFA World Cup |
| Season | 3 — 2018 |
| Match date | 2018-07-15 |
| Stage | Final |
| Home team | 771 — France |
| Away team | 785 — Croatia |

No match identity was inferred from file names or the historical design text.
No 360 file was requested or coverage claimed. This is not a Brighton 2026 match.

## Actual local bundle and hashes

Local manifest:
`data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/manifest.json`.
Acquisition time (UTC): `2026-10-19T15:39:14.761696+00:00`.
Manifest SHA-256: `f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c`.
Pipeline SHA in that manifest matches the implementation commit above.
The manifest and all provider files are local and ignored, not committed.

| Upstream path | Bytes | SHA-256 |
| --- | --- | --- |
| `README.md` | 1753 | `98a757466c4d931dba4b6c4290c55c2fe74e4550d7455bbe05fd884dc831aff3` |
| `LICENSE.pdf` | 165130 | `a5462e69aeb71a39268b760b110c5c2190a2e0cee3015ba976f66bd71f6c2bb4` |
| `data/competitions.json` | 34887 | `e6cd42f5d8956d6aa30fb917ce8d4c3b3df1879a93f02f8feba820930a6971fa` |
| `data/matches/43/3.json` | 114527 | `f89dbd4aedcaf9c9e4ec9d8e745d5d54596500ec357d7489c914a2f126805adf` |
| `data/events/8658.json` | 2490969 | `a9aa72c042153fa351c3591ee11e7fba95b0c8841c4489da4aa6809de1edbdf5` |
| `data/lineups/8658.json` | 18572 | `84696fa0d36f14e6aa557d9dcdf11f4ac0f304e6e7a547bb160f740f85a71f53` |

Every source URL is
`https://raw.githubusercontent.com/hudl/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/<upstream-path>`.
The actual manifest records full requested/final URLs, acquisition time, source
terms, identity, QC counts and adapter version; see [specification](SOURCE_MANIFEST.md).
The bytes match the independent initial source-audit downloads exactly.

## Independent observations

Direct standard-library JSON parsing and hashing, separate from the acquisition
module, confirmed **2,978 events, 2,978 unique event IDs, zero duplicate IDs**.
Source period counts: 1 → 1,332; 2 → 1,646. Missing/null player: 59; location: 64;
possession_team: 0. These are source QC counts, not analytical outputs.
No xG/xT, score reconciliation, clock or player metrics were computed.
The manifest retains observed type/key frequencies and explicitly leaves
unknown-type count null because full enum/schema auditing is not implemented.

Independent exact-ID reverse lookups in original JSON each returned one record:

| Original ID | Provider index | Provider event type |
| --- | --- | --- |
| `4a44199a-3111-4e28-b567-9c1393e68dff` | 1 | Starting XI |
| `a8f0457d-52a8-4072-8165-6dc06fe6bddf` | 1490 | Pass |
| `883aa370-a1b5-4e33-877a-7a4c83abd26e` | 2978 | Half End |

Raw JSON whitespace, ordering, IDs, coordinates and unknown fields are preserved;
there is no normalization, row dropping or synthetic football dataset.

## Commands and exit codes

Commands ran from the repository root with README's writable uv environment
variables. Final results below are observed, not proposed commands.

| Command / check | Exit | Result |
| --- | --- | --- |
| Initial pinned README/LICENSE fetch; `pdftotext -layout` | 0 | Read source terms before acquiring event files. |
| `uv lock --check` | 0 | Existing manifest/lock consistent. |
| `uv sync --frozen` | 0 | Existing locked engineering environment installed. |
| `uv run --frozen ruff check .` | 0 | All checks passed. |
| `uv run --frozen pytest -q` | 0 | 41 passed, 0 skipped; 4 foundation + 37 acquisition test cases. |
| `uv build` | 0 | Wheel and source distribution built. |
| `uv run --frozen python -m fil.ingestion.statsbomb --help` | 0 | Acquire and offline-verify commands available. |
| `uv run --frozen python -m fil.ingestion.statsbomb acquire --pipeline-revision "$fil_pipeline_sha"` after `fil_pipeline_sha=$(git rev-parse HEAD)` | 0 | Correctly attributed local bundle acquired; 2,978 events, integrity PASS, rights pending. |
| `uv run --frozen python -m fil.ingestion.statsbomb verify data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb` | 0 | Offline byte/identity/manifest verification passed. |
| Independent JSON/hash/byte comparison and three ID lookups | 0 | Counts/hashes above; every provider file matches initial source audit. |
| `git check-ignore data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/manifest.json` | 0 | Manifest ignored. `git ls-files data/raw` empty. |
| Wheel content inspection with `zipfile` | 0 | Packaged pin registry present; no raw provider files. |

The offline test suite covers manifest generation, immutable source bytes and
unknown-field preservation, unavailable/oversized/redirected HTTP inputs,
malformed JSON/structures, missing/invalid/duplicate UUIDs, source size/hash
mismatches, cross-record metadata mismatch, corrupt manifests/caches/symlinks,
UTC timestamps, deterministic repeat, and cleanup on publication failure.
Transport is injected; live urlopen calls are forbidden in acquisition unit tests.
All fixtures are explicitly TEST-ONLY objects, not real match observations.

## Fresh-checkout reproduction

A new clone was made with
`git clone --no-local --branch feat/fil-002-data-acquisition /workspace/football-intelligence-lab /tmp/fil-002-verify.YlLkPc/checkout`
(exit 0) at the implementation SHA above. It started with no project environment
and an empty uv dependency cache at `/tmp/fil-002-verify.YlLkPc/cache`; the pinned
interpreter was reused, so this is not a fresh operating-system image.

From that checkout, all of the following exited 0:

```bash
fil_pipeline_sha=$(git rev-parse HEAD)
uv lock --check
uv sync --frozen --no-editable
uv run --frozen --no-editable ruff check .
uv run --frozen --no-editable pytest -q
uv build
uv run --frozen --no-editable python -m fil.ingestion.statsbomb acquire \
  --pipeline-revision "$fil_pipeline_sha"
uv run --frozen --no-editable python -m fil.ingestion.statsbomb verify \
  data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb
```

Ruff passed and all 41 tests passed (0 skipped). The regular installation loaded
its packaged pin registry and fetched the actual six files. Its provider bytes
and QC facts match the primary acquisition; its own acquisition timestamp is
allowed to differ. Calling acquire again with urlopen replaced by a function
that raises on any network access succeeded and preserved SHA-256 and mtime_ns
of every raw file and the manifest. Git status remained clean.

## Failures and corrections

- First lint run exited 1 for six E501 line-length findings. Ruff formatting
  corrected them; subsequent lint runs passed. Initial pytest passed 39 cases;
  two additional manifest/publication-failure tests bring the final count to 41.
- The first live CLI invocation supplied an incorrect full FIL SHA. Its raw-byte
  checks passed, but its pipeline provenance was invalid. The complete bundle
  was moved without changing its bytes to ignored
  `data/raw/quarantine/wrong-pipeline-sha/`; it is not accepted verification
  evidence. A new acquisition using Git's actual full HEAD SHA produced the
  canonical manifest above. This also illustrates the documented limit that a
  caller-supplied SHA is an assertion, not proof of code identity.

## Rights and gate assessment

See [SOURCE_POLICY.md](SOURCE_POLICY.md) for source clauses and attribution.
Technical source checks PASS for this pin. **DATA-SOURCE: PENDING** and
**DEL-SOURCE: PENDING**: owner registration/terms compliance remains unconfirmed.
The broad README research wording does not override the more restrictive PDF
terms. No redistribution/commercial permission is inferred, and no provider
files or datasets have been committed or publicly redistributed.

Only local noncommercial research acquisition is performed. Owner confirmation
is needed before closing the rights condition. No normalization or later gate
is passed; FIL-003 is not implemented. Linux x86_64 / Python 3.11.14 is tested;
other platforms and hosted CI are reported separately when observable.


## Hosted CI and PR delivery

`git push -u origin feat/fil-002-data-acquisition` succeeded (exit 0).
`gh pr create --repo Qiao527/football-intelligence-lab --base main --head feat/fil-002-data-acquisition --title "feat: acquire pinned StatsBomb fixture with provenance (FIL-002)" --body-file docs/FIL-002_PR.md`
failed (exit 1): `Post "https://api.github.com/graphql": Forbidden`.
`gh run list --repo Qiao527/football-intelligence-lab --branch feat/fil-002-data-acquisition --limit 5 --json databaseId,headSha,status,conclusion,url`
also failed (exit 1), with API Forbidden. No PR was created by that command and
no hosted CI result is claimed. Local package/CI-equivalent checks pass as
recorded above; remote Actions status remains unverified.

The [prepared PR body](FIL-002_PR.md) is committed for review. GitHub supplied
this [PR creation link](https://github.com/Qiao527/football-intelligence-lab/pull/new/feat/fil-002-data-acquisition).
A maintainer can create the PR with that description and inspect the hosted
workflow, or provide working API access for those operations. Neither a missing
CLI token value nor failed API access was treated as missing Git access: native
Git reads/pushes succeeded. No credentials were printed/requested or permissions
broadened. No merge, deployment or environment publication performed.
