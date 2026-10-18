---
name: fil-metric-validation
description: Test football metric definitions, game clocks, xG reconciliation, shot inclusion rules, filter ranges and event provenance with independent fixture evidence. Use after changing src/fil/metrics, src/fil/time, schema adapters or Match Explorer filters.
---
# FIL Metric Validation
1. Read the metric dictionary and identify source version, grain, units, filters, null treatment, and expected invariants.
2. Write or run tests for H1 stoppage vs H2 minute 0, extra-time periods, period-5 shootout, ordinary penalties, own-goal score linkage, empty selections and duplicate IDs.
3. Independently recompute group sums directly from verified provider events, not solely from the candidate output table.
4. Check tolerance and ordering: final team cumulative xG equals valid shot xG sum; time-window counts partition the included events exactly once.
5. Ensure UI selection IDs resolve to exact raw events and that missing features show NA, not zero.
6. Report commands/exit codes, missing evidence and PASS/FAIL findings. Never invent golden numbers.
