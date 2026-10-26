# Portfolio language grounded in completed work

## A 60-second project explanation

“Football Intelligence Lab is a working Python application for evidence-driven match review.
Users choose a match, run deterministic analysis, inspect observations and comparison records,
and drill into original event JSON. I built the interactive product and the data contracts
that keep source correctness separate from tactical interpretation. A fictional demonstration
runs without credentials or data downloads; a separate offline adapter verifies the existing
64-match research corpus. It does not claim expert-level AI discovery or player ability.”

## Resume-ready bullets

- Built an end-to-end football match-review application using Python, Streamlit, Plotly and
  PyArrow, with shared filters, dynamic reports and original-event evidence drilldown.
- Integrated a provenance-checked local adapter for 64 authorized historical matches and
  independently reconciled 227,825 original events using separate exact-arithmetic checks.
- Implemented explicit fact/hypothesis/generalization boundaries, complete event-ledger
  comparisons and abstention for unsupported selections; prevented stale cached reports after
  source changes and separated synthetic demonstrations from restricted research data.

Use test counts and timing numbers only from the final verification report for the actual
commit being demonstrated. Do not claim a measured legacy-app speedup, independent scientific
validation, internship impact, production deployment, model training or superior-to-human
analysis. The source corpus and much of the validated infrastructure predate this MVP; distinguish
reused foundation from this sprint's product implementation in interviews.

## Honest answers to likely questions

**Where is the AI?** The long-term research goal is autonomous football discovery. This MVP
is the reliable evidence/application layer; it runs no generative model and fits no new model.

**Are the insights novel?** Not established. The complete baseline can reproduce the facts.
The product makes their scope and evidence inspectable. Independent analyst utility is untested.

**Why not use an LLM summary?** A fluent summary does not establish source correctness or
football usefulness. The current system calculates first and keeps unsupported claims visible.

**Can I try it?** Yes: the default fictional fixtures require no credentials or provider access.
The README provides the local command. There is no public deployment in this sprint.

**What remains?** Human product acceptance, rights-aware independent usefulness evaluation,
legacy integration under actual merge guards and a separate owner decision on public hosting.
