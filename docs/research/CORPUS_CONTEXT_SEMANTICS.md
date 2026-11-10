# Original provider context-type review

This is an outcome-blind provider-schema review, not a target, feature or split
change. Original warning flags and all first-pass BLOCKED reports remain intact.

The original 8658 adapter's recognized-type list was explicitly scoped to names
reviewed in that fixture. It already preserves every original record, including
types absent from that list. A missing list entry does not itself establish an
undocumented provider event. Before unquarantining affected source-record outputs,
the accepted corpus adapter independently checks the original type ID/name against
the already pinned provider PDFs:

| Native type | Original type ID | Primary evidence | Limited use here |
| --- | ---: | --- | --- |
| Bad Behaviour | 24 | Open specification v1.1 p14; Open Events v4 type/attribute tables | Recorded disciplinary context; no Shot or pass/carry cutoff |
| 50/50 | 33 | Open specification v1.1 p14; Open Events v4 type/attribute tables | Retained contest context; no inferred successful pass, actor movement or Shot |
| Offside | 8 | Open specification v1.1 p25; Open Events v4 type table | Retained context; no inferred turnover or possession boundary |

PDF hashes remain `d5a8267939c5db35a9501b1a272cc9861a2bb3bef2f53c723d4a43ec1f5ef477`
and `05de42cc76b0c9cd26213d8e5c72610cac7d4d92c9c2ac878073a565dbb6c44a`.
The acquisition reference binds these to their pinned upstream identities.
Names and type IDs above agree in the held raw records. Some attribute numeric
IDs differ from later documentation; they are never silently remapped. No 50/50
outcome is interpreted as possession recovery or successful progression. Census
logic uses explicit source card names, with its own uncertainties and exclusions.

The new target still uses only source completed-owner passes/recorded carries as
cutoffs and strictly later owner Shot records as positives. These context records
remain in full membership/order checks. Offside is **not** promoted to an inferred
terminal state; closure still requires the frozen different-native-ID or paired
period-end evidence. Unknown types or ID/name conflicts continue to fail closed.

All six pilot reports were first generated at `873cf9f` and preserved, including
the conservative unfamiliar-type failures; successful reviewed pilot reassessment
was generated at `0f6685c`. First development assessments at `540aea8` retained
16 Offside-related quarantines. Later assessments use a new implementation SHA,
never overwrite those reports, and are independently verified again. No test
payload was opened or predictive score used to select these schema decisions.
