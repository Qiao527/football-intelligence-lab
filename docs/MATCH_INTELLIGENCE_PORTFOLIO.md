# Portfolio language grounded in completed work

## A 60-second project explanation

“Football Intelligence Lab is a source-traceable football scouting product. Ask a scouting
question, get candidates, and open the exact events behind every claim. Users move from
discovery to a player profile to original event JSON; unsupported comparisons abstain instead
of producing plausible prose. I built the web client, the Python API, the analysis core and the
release boundary that keeps synthetic demos, authorized research data and the public artifact
separate. A synthetic deployment is live, a rule-based interpreter is the current baseline, and
no generative model is claimed or deployed.”

## Resume-ready bullets

- Built an end-to-end football match-review application using Python, Streamlit, Plotly and
  PyArrow, with shared filters, dynamic reports and original-event evidence drilldown.
- Integrated a provenance-checked local adapter for 64 authorized historical matches and
  independently reconciled 227,825 original events using separate exact-arithmetic checks.
- Implemented explicit fact/hypothesis/generalization boundaries, complete event-ledger
  comparisons and abstention for unsupported selections; prevented stale cached reports after
  source changes and separated synthetic demonstrations from restricted research data.
- Built a dependency-free web client and Python serverless API, then a release pipeline that
  packages a 26-file allowlist, verifies it byte-for-byte against a manifest, imports every
  entrypoint in isolation and repeats the HTTP/browser contract against the deployed URL.
- Diagnosed a production-only failure class in serverless entrypoint discovery and a builder
  peer-dependency conflict, then fixed both with regression tests and documented the constraints.

Use test counts and timing numbers only from the final verification report for the actual
commit being demonstrated. Do not claim a measured legacy-app speedup, independent scientific
validation, internship impact, model training or superior-to-human analysis. The synthetic alpha
deployment is a real, verified deployment; describe it as a synthetic demo, not as a production
service for real players. The source corpus and much of the validated infrastructure predate this MVP; distinguish
reused foundation from this sprint's product implementation in interviews.

## Honest answers to likely questions

**Where is the AI?** The long-term research goal is autonomous football discovery. This MVP
is the reliable evidence/application layer; it runs no generative model and fits no new model.

**Are the insights novel?** Not established. The complete baseline can reproduce the facts.
The product makes their scope and evidence inspectable. Independent analyst utility is untested.

**Why not use an LLM summary?** A fluent summary does not establish source correctness or
football usefulness. The current system calculates first and keeps unsupported claims visible.

**Can I try it?** Yes. A synthetic deployment is live at
https://fil-public-alpha.vercel.app, and the local commands require no credentials or provider
access. The public app rejects real match IDs by design.

**What remains?** Rights-aware independent usefulness evaluation, a measured AI-versus-rule
comparison on held-out tasks, hosted hardening (domain, rate limits, monitoring) and a decision on
whether public real-player analysis is licensed.
