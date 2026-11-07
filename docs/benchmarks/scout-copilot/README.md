# Synthetic scouting benchmark

The checked-in cases and outcomes exercise the local, deterministic fallback, not a live
model. They are development cases for a tiny self-authored fixture, not a measure of
football knowledge or generalization. IDs and counts in the references are checked against
the fixture; the same cases are reused to make comparisons reproducible.

The non-AI comparison models the existing discovery search: the full request is entered
as its player/team substring filter. This is an automated interaction proxy, not a human
study, and the discovery interface permits a user to reformulate queries. Do not infer
user value or relative productivity from these numbers.

No live model was called. Latency, price, and model quality are unavailable until an
authorized provider and real inference are evaluated. No provider data is involved.

Run from the repository root:

```sh
uv run --frozen python scripts/evaluate_scout.py --output docs/benchmarks/scout-copilot/outcomes.json
```

The 36 labeled requests cover direct lookup, authored match facts, combined filters,
source actions, failed-pass counter-evidence, insufficient comparisons, missing attributes,
and adversarial requests. They deliberately include paraphrases and are a small development
set, not 36 independent real-world scenarios or a held-out benchmark. References contain
expected intent, candidate names and abstention. The grader additionally checks exact
fixture counts, candidate-specific original event IDs, complete context, the authored
incomplete pass and the permitted deterministic explanation template. A template mismatch
is only a narrow unsupported-claim proxy; arbitrary prose still requires independent review.
All responses and failures remain in `outcomes.json` alongside the source fixture SHA-256.
