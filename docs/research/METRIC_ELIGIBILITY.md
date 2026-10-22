# Metric-specific quality acceptance proposal

Version: **fil-metric-eligibility-proposal-1**. Status: **PROPOSED_NOT_ACCEPTED**.
This file and its diagnostic runner do not change DATA-* production behavior,
`pilot_gate`, the acquisition allowlist, historical clocks or the owner condition.
The remaining 57 matches stay unacquired and the expansion gate stays BLOCKED.
Acceptance of PR #16 as a forensic investigation did not accept a gate revision.

“Fully supported” below means the declared **source-record** calculation passes
its independently checked input contract. It does not certify football ground
truth, complete physical coverage, statistical adequacy, legal rights or analyst
usefulness. “Conditionally supported” requires named assumptions/exclusions shown
with every derived result; “blocked” produces null/withheld results, not zero.
These are proposed analytical eligibility states, not operational permission.

| Output / scope | Independent acceptance evidence | Fail / condition | 8656 proposal |
| --- | --- | --- | --- |
| Source identity and original records | Approved revision/file scope, upstream blob/bytes/SHA-256, manifest; original count/IDs/JSON and canonical identity/time/geometry/xG projections | Any identity corruption blocks every downstream output; preserve/quarantine bytes | Source-record facts can be supported |
| Provider event order | Unique increasing original indices, non-reversing native period sequence, supported period set | Never sort/repair source to hide failure; block transitions if unresolved | Supported source order |
| Score reconstruction | Versioned Shot/penalty/linked own-goal semantics, original evidence IDs, separate shootouts, official match-play metadata reconciliation | Unknown/ambiguous scoring links or mismatch block score; shootout official comparison unavailable without separate metadata | Supported native-order 2–1, no chosen physical boundary |
| Native event spatial geometry | Original StatsBomb frame, finite 120×80 domain, nullable coordinates, exact move/Shot identity | Missing coordinates exclude affected records and disclose denominator; invalid coordinates block spatial output; no flips | Native source geometry only |
| Physical attacking-direction/continuous position metrics | Independent provider-supported orientation/tracking contract | Not supplied here; always blocked | Blocked |
| Same-period differences of observed source timestamps | Both source records, index order, valid monotonic native clocks; shared period-prefix uncertainty cancels exactly | Do not report as physical/live-ball duration; equal stamps imply zero source-clock difference only | Fully supported **source-clock** arithmetic |
| Boundary-independent source facts | Original periods/IDs/native possession membership, Shot/xG/goals and recorded transitions | Record semantics/missingness remain explicit; no physical-time claims | Unchanged by marker selection |
| Completion before all scenario boundaries | Every supported record starts before earliest marker; supplied duration completions do not exceed it | Missing duration cannot certify completion; overlapping or boundary-zone records unresolved for this claim | Known completions satisfy the case-specific check |
| Cross-period event-phase offsets/differences | Valid opposing-team reciprocal start/end pairs; enumerate correlated period boundaries once | Marker interval is an uncertified sensitivity scenario, not confidence bounds or certified match time; exclude breaks | Conditional |
| Recorded-census exposure envelopes | Above plus independent XI/roster/substitution/Off-On/dismissal census and no duration overlap | Contradiction withholds all exposure ranges; unused roster remains null | Conditional sensitivity only |
| Official minutes, per90, exact-time exposure | Independent physical timing/appearance certification, separately reviewed | Remain unavailable; no certification path implemented by this proposal | Blocked/null |

## Independent tests and regression behavior

`fil.research.eligibility.assess` receives raw bytes and canonical records only
after the existing upstream scope/hash verifier. It compares all original JSON
and metric-relevant canonical projections, namespace and source hashes; a metadata
date or score alone cannot bless a payload. Score decisions use native order and
explicit links without constructing a fake CLOCK_SCHEMA. The existing scoring
and clock implementations are untouched. Independent raw checks compare the new
decisions with old score reports where available and with raw goals for 8656.

The period-envelope model from PR #16 remains separately versioned and unaccepted.
The proposed diagnostics exclude shootouts from match-play temporal/exposure
calculations and retain their records and scoring domain separately. Every output
retains source IDs and uncertainty. Same-period source differences do not need a
physical endpoint or a valid full-period envelope; cross-period calculations do.
Source-clock differences cannot establish physical action completion/availability.

TEST_ONLY regression coverage includes the four observed 8656 spreads (107,160,
280,40 ms), cancellation of correlated prefix uncertainty, source/canonical/hash
tampering, missing/invalid geometry, unlinked markers, reversed source clocks,
linked versus unlinked own goals, official mismatch and separate shootouts.
Real source checks use all seven held matches and preserve the 2,978-event 8658
fixture, 4–2 reconciliation and source xG. They are verification on exposed data,
not an independent future predictive trial.

## Proposed operational policy if later explicitly accepted

Retain hard source identity, schema/record preservation, score and required
provider-semantics failures. Admit only named metric domains whose contracts
pass, with exact exclusion counts and unresolved outputs retained as null. Never
interpret a conditional envelope as physical certification or enable per90. An
uncertain physical boundary alone need not invalidate record-order/spatial
evidence, provided no other affected-domain failure is hidden.

Before a new expansion executor is enabled, owner acceptance must identify the
policy version/hash, permitted domains, remaining exact 57 file pairs and existing
rights restrictions. Then independently review all six pilots under those domain
contracts, preserving old BLOCKED artifacts; create a new gate artifact bound to
raw/report hashes. Record outcomes before opening any new event payload. No such
acceptance, replacement gate artifact or executor change is made in this PR.

The proposal offers a reviewable route toward defensible record-based research;
it does not ask for an arbitrary timing tolerance, guessed endpoint or automatic
passing reclassification. Forecasting/analyst design is separately frozen in
[PROSPECTIVE_PROTOCOL.md](PROSPECTIVE_PROTOCOL.md). Wyscout primary-source work and
its distinct future authorization remain in [WYSCOUT_PRIMARY_AUDIT.md](WYSCOUT_PRIMARY_AUDIT.md).
