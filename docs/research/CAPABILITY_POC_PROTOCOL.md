# Bounded capability probe, frozen before execution

Question: does the reviewed K-Dense hypothesis validator add deterministic record
linting beyond merely parsing JSON, and does that certify scientific evidence?
This is a component probe, not an agent benchmark or a comparison of reasoning models.

Pin `K-Dense-AI/scientific-agent-skills` at
`593377bb048752abb0152deab9fbb1083a6087df`. Review the complete
`skills/hypothesis-generation/scripts/validate_hypothesis_schema.py` and `_common.py`
before running; execute only these two dependency-free files against the bundled
synthetic demonstration template. No installation, hooks, provider data, external
API, new model or repository-wide capture. Use a fresh temporary working directory,
explicit child environment, no network permission, timeout and resource limits.
Record exact hashes, every input, output, return code and elapsed time locally.

Freeze these ten cases and repeat each three times in forward/reverse/forward order:

| Case | Mutation | Expected interpretation |
|---|---|---|
| control | Unchanged synthetic template | Valid for human review |
| missing_falsifier | Remove first prediction's falsifier field | Reject malformed schema |
| dangling_prediction | Link first hypothesis to nonexistent prediction | Reject broken reference |
| causal_no_estimand | Empty causal estimands | Reject missing causal specification |
| undeclared_source | Use undeclared observation source ID | Reject undeclared reference |
| external_sensitive | Declare sensitive data sent externally | Reject declared prohibited use |
| blocked_gate | Block data governance with explicit unresolved reason | Valid record, blocked use |
| invented_provenance | Replace provenance with an unsupported evidence assertion | Cannot verify assertion |
| wrong_independent_unit | Specify iid analysis of dependent repeated-player events | Cannot certify dependence assumptions |
| tautological_falsifier | Nonempty falsifier says all outcomes support the hypothesis | Cannot certify falsifiability |

All cases remain syntactically valid JSON; JSON parsing is the intentionally minimal
baseline. Do not represent this as FIL's full baseline: FIL already validates its
own attribute registry, freezes protocols, verifies raw provenance independently,
and tests designs. The two schemas are incompatible, so their rejection rates are
not a fair head-to-head comparison. The proposed additional capability is richer
cross-linked hypothesis records, not automatic scientific validity.

Retain surprises and failures, including failure of the untouched upstream template.
Do not change fixtures after results to improve detection. Report runtime only as
probe execution cost, not a product or agent speed improvement. No measured gain
in football discovery, prediction, memory retrieval or engineering productivity is
implied. Adopting a skill requires a separate task-level benefit, beyond this probe.
