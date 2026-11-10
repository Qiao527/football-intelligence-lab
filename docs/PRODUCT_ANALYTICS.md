# Local product analytics

The primary product metric is **Time to First Defensible Insight**: elapsed time from starting
an investigation at Discovery until the user confirms completion after inspecting evidence.
The app records that confirmation, not whether the insight is actually defensible. Independent
review is required before treating this as a validated measure of defensibility. The funnel is
Discovery → Candidate → Player Profile → Evidence → Completed Investigation; a session only
advances in this order. The script reports counts, completed-investigation count, and median
elapsed time among completed sessions; partial sessions remain in the funnel denominator.

Recording is opt-in, local and in memory only. An explicit download exports stage names and
relative milliseconds; it contains no queries, identities, player IDs, evidence or timestamps.
Stopping clears the unsaved session. The browser makes no analytics network requests and uses
no analytics storage. Records are never uploaded by the application.

Run `.venv/bin/python -m fil.analytics path/to/fil-local-journey.json` to reproduce the
summary. Data may contain multiple sessions in the exported `sessions` list. For manual
quality review, add a `review` object to a session with boolean `candidate_correct` and
`unsupported_claim` fields. Candidate accuracy and unsupported claim rate use reviewed
sessions as their denominator and remain null without reviews. The review must use a documented
rubric and source evidence; the program does not infer correctness or audit model output.
These are guardrails, not measures of real engagement. Tests use synthetic sessions only;
real user claims require consenting participants, an appropriate protocol, and review.
