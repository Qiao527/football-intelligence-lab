# FIL 2.1 interpretation validation

The provider boundary accepts a strict five-field query. Independent, conservative lexical
checks normalize a limited set of equivalent phrases, then reuse the deterministic rules parser
to verify intent, team, player and numeric filters independently of the model. The rules parser
is not an independent semantic model. Unknown wording and unverified constraints abstain. These checks
are not a general proof of semantic equivalence or prompt-injection resistance. A validated
query retrieves deterministic source facts; provider text is never displayed as evidence.
The current web interface still uses the rules fallback.

The OpenAI Responses adapter sends only the prompt text from the exact, hash-verified
self-authored `cases.json` and `heldout.json` files. It does not send events, arbitrary user
queries or local research data. It fixes the API destination, rejects redirects, uses `store: false`, requires an
explicit model and key, and has no default live execution. Missing credentials, network errors,
refusals, invalid schemas and inconsistent constraints fail closed. API format follows
[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
The adapter has only been tested with mocked transport; no live-model result is claimed.

## Benchmark design

- Development: the original 36 labeled cases. The 16 separate challenge prompts have no exact
  overlap, but were created by the implementer after reading the original parser; they are not
  blinded or an independent generalization test. They share one tiny fictional fixture.
- The human-specified structured oracle reference uses the explicit `dev_structured.json` or `structured_query` fields
  supplied for each task. It simulates an expert selecting correct form controls; it does not
  parse natural language, and its latency excludes the human's work. The reference labels and
  baseline were authored together, so its score is an oracle reference, not a
  blind contest or measured user performance.
- Success requires the expected tool, candidate set, abstention, evidence, counts, contradiction
  and deterministic explanation. False abstentions count cases with an unnecessary abstention;
  constraint preservation compares all five query fields on the supported-intent cases. The
  live report separately scores raw model proposals and the final guarded query. Evidence correctness is calculated only on tasks that return
  candidates; abstention precision and recall use the provided case labels. Raw outputs and all
  failures are retained in `validation_21.json`. Timings are one local run, not stable benchmarks.
- Rules and structured queries use zero model tokens and have zero token cost. Live usage and
  cost are **NOT RUN** until explicitly invoked with credentials. The Responses API usage
  does not establish actual billed cost; reconcile that separately with provider billing. When run, provider usage and
  latency are preserved per case; cost is an estimate using explicit per-million USD rates for
  uncached input, cached input and output. If any usage or rate is missing, cost remains null.
  Provider errors are recorded as unsuccessful even when the safe abstention matches the label.

Run offline from the repository root:

```sh
uv run --frozen python scripts/evaluate_scout_21.py --output docs/benchmarks/scout-copilot/validation_21.json
```

For an authorized live evaluation, set `OPENAI_API_KEY` privately and supply a model that supports
Responses structured outputs. The default live run is the 16-case challenge; use
`--suite development` or `--suite both` to change scope. The run sends only the fixed
synthetic prompts; it can incur charges:

```sh
uv run --frozen python scripts/evaluate_scout_21.py --output /tmp/fil-live-results.json \
  --live-model MODEL --input-usd-per-million RATE --cached-input-usd-per-million RATE \
  --output-usd-per-million RATE
```

Update and review the adapter's approved hashes if either synthetic case file is intentionally
changed. This is an explicit privacy gate, not an assertion that arbitrary new prompts are safe.
