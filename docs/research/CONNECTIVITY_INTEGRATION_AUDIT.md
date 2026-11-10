# Read-only stacked PR integration audit

Snapshot captured for this audit; exact receipt is retained locally. All API calls were read-only.

Main: `0fd8306e6d09a2ab062acb39443272f145114572`, `protected: false`.

| PR | Base branch | Head (abbreviated) | Ahead / behind current base | State / hosted checks |
| --- | --- | --- | ---: | --- |
| #4 | `feat/fil-002-data-acquisition` | `3d81faf9ae66` | 3 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #5 | `feat/fil-003-event-normalization` | `48d566a2664a` | 3 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #6 | `feat/fil-004-period-aware-clock` | `9afe745d701c` | 3 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #7 | `main` | `195a3efb4bef` | 3 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #8 | `integrate/fil-003-005` | `363494ccd8b7` | 10 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #10 | `feat/fil-v03-match-explorer` | `2645eb916e0a` | 7 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #11 | `feat/fil-012-tactical-dashboard` | `83586739faee` | 4 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #12 | `feat/fil-v05-possession-flow` | `1ec94984a76a` | 4 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #13 | `feat/fil-player-involvement-foundation` | `1a761c17ee26` | 3 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #14 | `research/fil-evidence-foundation` | `90ba21dd22e3` | 4 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #15 | `research/fil-corpus-readiness` | `6b159be796cc` | 8 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #16 | `research/fil-worldcup-corpus` | `b204ada492c0` | 7 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #17 | `research/fil-temporal-forensics` | `a6f64008a352` | 4 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #18 | `research/fil-metric-eligibility` | `32cdf25df067` | 9 / 0 | Draft; MERGEABLE; CLEAN; checks pass |
| #19 | `research/fil-authorized-corpus` | `d5a0e833f3ea` | 5 / 0 | Draft; MERGEABLE; CLEAN; checks pass |

Fifteen existing PRs remain open drafts; #1–#3 were already merged. Every open
head is ahead of its current base with zero commits behind in the API comparison.
GitHub reports each as MERGEABLE/CLEAN and both hosted checks successful. This
describes current-base mergeability only, not product acceptance or merge eligibility.

## Integration risks

- **Mandatory enforcement remains unsatisfied.** Main reports `protected: false`.
  Green checks and CLEAN cannot substitute for enforceable required lint-and-test,
  PR requirements, no force pushes/deletion or administrator bypass protection.
  The prior plan/protection owner action remains external; this audit does not
  establish current paid-plan eligibility or request the same action again.
- **Long dependent chain.** #7 → #8 → #10 → #11 → #12 → #13 → #14 → #15 → #16
  → #17 → #18 → #19. Each green result is against its present base. Any future
  authorized squash/reconciliation changes commit ancestry and requires scoped
  retarget/rebase review, source reconciliation and new hosted CI. None is done here.
- **Legacy overlap.** #4/#5/#6 are the older component chain. Comparing #6 with
  integration #7 reports DIVERGED (integration ahead 4, behind 13), with overlapping
  ingestion/schema/time/score/test/source-policy/CI paths. Do not assume those
  branches can all be merged independently without replay or conflicting semantics.
  The snapshot retains the exact file inventory; no content-equivalence is asserted.
- **Validation scope.** CI verifies code/installations and TEST_ONLY regressions.
  Provider records remain local; passing CI does not independently reproduce the
  ignored full-corpus research artifacts, certify rights or satisfy human product
  acceptance. Existing UI performance and human acceptance limitations remain.
- **No approval inference.** Draft status and successful checks do not establish
  independent scientific review, authorized main integration or product acceptance.

Full read-only PR/ancestry/main API snapshots and their hashes are under ignored
`data/interim/connectivity-falsification/governance/`. Existing PR heads/bases,
branch protection and data rights were not changed. The new focused research
draft uses PR #19 as its parent; this audit does not authorize merging it.
