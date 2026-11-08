# FIL 2.1 interpretation validation

The provider boundary accepts a strict five-field query. Independent, conservative lexical
checks normalize a limited set of equivalent phrases, then reuse the deterministic rules parser
to verify intent, team, player and numeric filters independently of the model. The rules parser
is not an independent semantic model. Unknown wording and unverified constraints abstain. These checks
are not a general proof of semantic equivalence or prompt-injection resistance. A validated
query retrieves deterministic source facts; provider text is never displayed as evidence.
The current web interface still uses the rules fallback.

The OpenAI Responses adapter sends only the prompt text from the exact, hash-verified
self-authored `cases.json`, `heldout.json` and `chinese_example.json` files. It does not send events, arbitrary user
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
Responses structured outputs. Explicitly set the spending limit with the provider and supply
the same USD amount to `--spend-limit-usd`, then confirm the provider setting with
`--provider-limit-confirmed`. This is a required declaration, not a verified or enforced
hard cap: this script cannot inspect or enforce the provider's billing controls. Do not run
without a suitable provider-side limit. The default live run is the 16-case challenge; use
`--suite development` or `--suite both` to change scope. Only fixed synthetic prompts are sent:

```sh
uv run --frozen python scripts/evaluate_scout_21.py --output /tmp/fil-live-results.json \
  --live-model MODEL --spend-limit-usd LIMIT --provider-limit-confirmed \
  --input-usd-per-million RATE --cached-input-usd-per-million RATE \
  --output-usd-per-million RATE
```

Update and review the adapter's approved hashes if either synthetic case file is intentionally
changed. This is an explicit privacy gate, not an assertion that arbitrary new prompts are safe.

The optional `--suite chinese` checks the user's single approved Chinese example. For that
fixed prompt, the model adapter asks for four structured requirements: midfield position,
qualitatively low goals, defensive transitions and build-up. A fixed independently reviewed
reference validates the extraction; no numeric goal threshold is invented. The final query
must abstain because the fixture contains no position field or defensible low-goals comparison.
This is a mocked and pending live safety check, not evidence of general Chinese support.
The existing English challenge remains separate and unchanged.

## DeepSeek synthetic contribution experiment

`--provider deepseek --live-model deepseek-flash --suite contribution` runs one fictional
fixture review. The provider receives only facts generated from the hash-pinned synthetic
fixture, not arbitrary match files or user text. The rules reference returns all qualifying
unranked candidates. The model may select candidates and event IDs; local checks require
source-backed transition and completed build-up actions and all recorded incomplete passes.
Only verified facts are returned; model prose is not trusted. Empty or invalid responses
abstain. The sample is 0–0 and does not establish that anyone caused a win. It has no
positions, certified minutes, off-ball movement or complete match coverage. This is one
exploratory case, not a test of real-world discovery, match-winning impact or usefulness.

For an authorized run, set `DEEPSEEK_API_KEY` securely, configure a provider-side spending
control if available, and use the explicitly agreed budget of at most $0.60. The CLI's
limit is a declaration: it does **not** enforce a billing cap, inspect the provider's
controls, or replace an account limit. If those controls cannot be established, do not run.
DeepSeek's [JSON output](https://api-docs.deepseek.com/guides/json_mode/) guarantees JSON
format, not our schema; local validation is mandatory. Model prices and usage details are
in [DeepSeek's pricing documentation](https://api-docs.deepseek.com/quick_start/pricing/).

```sh
uv run --frozen python scripts/evaluate_scout_21.py --suite contribution \
  --provider deepseek --live-model deepseek-flash --spend-limit-usd 0.60 \
  --provider-limit-confirmed --output /tmp/fil-deepseek-contribution.json
```

No provider was called while preparing this experiment. Input, cached-input and output
rates may be supplied using the documented rate flags; without all rates, cost remains null.
Reconcile actual billed cost separately. The current user interface remains rules-only.

The fictional contribution report separately exposes recorded build-up passes, transition
interceptions, shots and incomplete passes for every recorded player. Repeated observations
are identified only when actions appear in at least two distinct (period, possession) pairs;
these are sample observations, not validated tactical patterns or evidence of causality.
Other defensive action coverage and attacking/defending off-ball behaviour are unavailable
and remain null. No playing-time or opportunity adjustment is possible. The model can cite
only verified source actions and must include every recorded incomplete pass as counter-evidence.
