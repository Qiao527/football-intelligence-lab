# Squash-safe stack review and reconciliation — FIL-005

Review snapshot: 2026-10-19 UTC. Native `git fetch` and `git ls-remote origin
refs/pull/{3,4,5}/head` verify these heads; `origin/main` remains
`cde6c66` (FIL-001 / PR #2). None of these feature heads is an ancestor of main.
The owner reports the PR bases and successful hosted CI below. GitHub GraphQL
inspection (`gh pr view 5 ...`) exits 1, Forbidden; PR state, approvals, branch
protection and hosted logs cannot be independently inspected through that API.
An absent commit ancestor alone cannot exclude a squash; main's inspected log
and files currently contain FIL-001 only.

| PR | Feature branch | Recorded head / downstream anchor | Intended base |
| --- | --- | --- | --- |
| #3 | feat/fil-002-data-acquisition | `5a18a4e1a417cfbf33941796552b25c9c8ab0c36` | main |
| #4 | feat/fil-003-event-normalization | `3d81faf9ae66f1b2075a1aba5b877baefa42e418` | FIL-002 |
| #5 | feat/fil-004-period-aware-clock | `48d566a2664a21b84b4ba8777de39116eff5480f` | FIL-003 |
| FIL-005 | feat/fil-005-score-reconstruction | starts exactly at #5 head above | FIL-004 |

Native ancestry verifies #3 → #4 → #5. FIL-005 baseline: frozen installation
and 180 existing tests pass, exit 0. No merge or history rewrite was performed.
Each PR compares only against its immediate parent, not main. A passing parent
is a development dependency, not human acceptance of any milestone.

## Conditional procedure after approved squash merges

1. Before any reconciliation, fetch main and surviving parent/child refs; record
   PR merge evidence, the actual main squash commit, expected remote child heads
   and each child's **latest incorporated parent SHA**. Preserve recoverable
   local backup refs for every affected child. Stop for unexpected source/schema
   changes or ambiguous merge identity; never guess a squash commit from its name.
2. After owner-approved #3 merge, transplant **only FIL-003 commits after the
   FIL-002 anchor** onto updated main:
   `git rebase --onto origin/main <incorporated-FIL-002-SHA> feat/fil-003-event-normalization`.
   Verify main actually contains the accepted FIL-002 implementation (including
   any merge-time fixes). Retarget #4 to main. Do not merge old FIL-002 history.
3. Reconcile #5 onto the newly rewritten FIL-003 branch with
   `git rebase --onto <new-FIL-003-head> <old-incorporated-FIL-003-SHA> feat/fil-004-period-aware-clock`.
   Then reconcile FIL-005 onto new FIL-004 with the equivalent command using its
   **old incorporated FIL-004 SHA**. Update all anchors and rerun affected checks.
   Child bases remain their immediate parent until that parent is merged.
4. After owner-approved #4 squash, rebase only FIL-004's commits after its latest
   FIL-003 anchor onto updated main; retarget #5 to main. Rebase only FIL-005's
   commits after its old FIL-004 anchor onto the rewritten FIL-004 head.
5. After owner-approved #5 squash, rebase only FIL-005's commits after its latest
   incorporated FIL-004 anchor onto updated main; retarget FIL-005 to main.
   If all parents have merged before reconciliation, FIL-005 can be transplanted
   directly using its recorded FIL-004 anchor, after checking accepted content.
6. Inspect each diff/range to prove upstream changes are present exactly once
   and only the milestone's own changes remain in its PR. Resolve conflicts
   against accepted contracts, not blindly choosing either side. Run frozen
   install, lint, full tests, build, fresh regular install and real-data chain
   verification. Rebuild derived artifacts with the new actual code SHA; retain
   immutable old artifacts as historical evidence. Recheck hosted CI.
7. If rewriting a published feature branch is necessary, push using an explicit
   `--force-with-lease=refs/heads/<branch>:<observed-remote-head>`. A failed lease
   requires refetch/review, never unconditional force. Never force or merge main.
   Deleted parent refs do not invalidate retained anchors; use backup refs,
   recorded SHAs and accepted main content. API Forbidden means save the exact
   retarget/creation instructions and report the delivery limitation.

These are a preparation plan, not execution authorization for merges. Changes
to parents require renewed downstream verification. Independent review and
human approval remain mandatory; no milestone is accepted by ancestry or CI alone.
