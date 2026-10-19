# Metric-specific rules
- Implement each metric as a pure function over documented canonical tables where possible.
- Create a metric dictionary entry: formal expression, units, input columns, filters, null policy, event lineage, version, limitations, expected invariants.
- Match-play xG includes recorded match-play penalties, excludes period-5 shootout; non-penalty xG is separate. Ensure v0.3 sums reconcile with provider shot rows.
- No free-form LLM-generated metric numbers. New xT/VAEP experiments require model card, training corpus, leakage check and held-out evaluation.
- Do not claim observed correlation or graph centrality is a causal effect.
