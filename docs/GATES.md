# Gate namespaces and legacy mapping

FIL-001 separates engineering prerequisites, delivery stages and validation
checks. New evidence must name a gate rather than use bare G numbers.

## Engineering prerequisite

**ENG-FOUNDATION** (FIL-001): reproducible Python 3.11 project metadata, committed
lockfile, fresh install, passing lint/tests, documented commands and CI definition.
Report hosted CI separately: defining a workflow does not prove it ran.
This replaces the misleading G0 on FIL-001 in handbook §33.2. It does not waive
source/rights checks for FIL-002 or pass any football gate.

## Delivery stages (AGENTS.md and handbook §33.2)

| Legacy | New name | Preserved acceptance |
| --- | --- | --- |
| G0 | DEL-SOURCE | Source usable and rights recorded. |
| G1 | DEL-SCHEMA | Normalization and schema PASS. |
| G2 | DEL-TIME-SCORE | Period-aware timing and score reconciliation PASS. |
| G3 | DEL-SHOTS-WINDOWS | Shots/xG and windows PASS. |
| G4 | DEL-FILTERS-EVIDENCE | Shared filters and drilldown PASS. |
| G5 | DEL-REVIEW | v0.3 quality/regression evidence and human review. |

## Validation gates (handbook §10.1)

| Legacy | New name | Preserved check and failure behavior |
| --- | --- | --- |
| G0 Source | DATA-SOURCE | URL/hash/JSON/manifest reviewable; reject entry on failure. |
| G1 Schema | DATA-SCHEMA | Keys, period, types, required fields; quarantine failures. |
| G2 Time | DATA-TIME | Stable period/index, clock and windows; stop timeline publication. |
| G3 Spatial | DATA-SPATIAL | Coordinate bounds, nullable values, direction; stop spatial analysis. |
| G4 Shots | DATA-SHOTS | xG bounds, unique shots, cumulative reconciliation; stop xG publication. |
| G5 Score | DATA-SCORE | Goal/own-goal deduplication and official score reconciliation; stop final score publication. |
| G6 Interaction | DATA-INTERACTION | Shared window/state across charts; block v0.3 acceptance. |
| G7 Research | DATA-RESEARCH | Role, sample, counter-evidence, traceability; candidates cannot become verified. |

Delivery stages group multiple validation checks; the sequences are not
interchangeable. DEL-TIME-SCORE includes DATA-TIME and DATA-SCORE;
DEL-SHOTS-WINDOWS includes DATA-SHOTS and time-window invariants.

## Explicit reference corrections in FIL-001

- AGENTS.md: name the six original delivery stages and separate ENG-FOUNDATION.
- Handbook §10.1: rename eight labels to DATA-* and add a mapping note; preserve
  all check and failure cells unchanged.
- Handbook §19.1: replace G0–G6 with the seven explicit DATA-* names.
- Handbook §25: qualify source/schema/time-score delivery prerequisites before
  visualization, retaining the timing and score requirements.
- Handbook §33.2: namespace delivery labels; classify FIL-001 as ENG-FOUNDATION
  and qualify the warning about premature G1–G4 completion claims.
- Master Reference is unchanged. Bootstrap documents remain historical evidence.

No data model, metric definition, failure behavior, phase ordering, rights
condition or human approval requirement is relaxed. No DEL-* or DATA-* gate
has passed in this foundation; no football data is present.
