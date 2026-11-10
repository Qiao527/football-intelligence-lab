# FIL capability decisions, 23 October 2026

**Adopt a small, explicit research review card and keep FIL's existing local evidence
ledger. Install no agent framework, memory service or additional runtime dependency.**
K-Dense supplies useful reference material and a testable record validator; it does
not supply independent football evidence or demonstrated better discovery. Existing
Codex tools, FIL research skills, source manifests, protocols, pytest and independent
verifiers already cover much of the proposed workflow. The immediate scientific
bottleneck is comparison design and construct evidence, not agent orchestration.

## Evidence and limits

Inspected public repository metadata, complete recursive file trees for the seven
requested projects, selected implementation files, licenses, documentation and a
latest-Actions-run snapshot. Files and full commit identities are inventoried in
[CAPABILITY_AUDIT_SOURCES.json](CAPABILITY_AUDIT_SOURCES.json). Links below resolve to
the inspected revisions, not moving branches. This is a bounded source review, not
a complete security audit, dependency audit or certification of upstream CI.

All seven are nonarchived and had recent pushes at observation: K-Dense 19 October;
Superpowers 23 October; Addy 13 October; gstack 23 October; Hindsight 23 October;
claude-mem 23 October; MiroFish 16 October. Activity is not evidence of effectiveness
or safe defaults. The latest Actions snapshots span other commits, pending runs,
skipped jobs and unrelated workflows. In particular, MiroFish's observed success
was **Update Star History**, not a research-validity or application test. No claim
that all inspected heads passed CI follows from these snapshots. Public counts of
issues/stars are not used as a quality score.

No hooks installed, no third-party agent invoked, no containers started, no provider
data sent externally, and no architecture, allowlist or acquisition scope changed.
Only the completely reviewed, dependency-free K-Dense validator/helper were executed,
on synthetic records in a temporary directory. Existing research continued alongside
this audit; neither the audit nor the probe is an independent football evaluation.

## Decisions

| Resource | Capability beyond a bare Codex session | FIL decision and marginal value |
|---|---|---|
| K-Dense scientific-agent-skills | Reusable scientific review patterns; cross-linked hypothesis/measurement/prediction records; deterministic lint scripts | **Use selected patterns now; evaluate the validator experimentally.** No whole-pack installation. Adds an explicit review artifact, not new reasoning machinery. Existing FIL skills already cover rivals, dependence, falsification and uncertainty. |
| obra/superpowers | Packaged debugging, testing, planning and verification procedures; host integration | **Reference only.** Existing AGENTS, research skills and CI cover most value. Do not add a competing global router or obligatory orchestration. |
| addyosmani/agent-skills | Engineering skills and evaluation task scaffolds | **Reference only; defer install.** Useful examples of measurable task contracts. No FIL productivity evidence; do not duplicate skill routing. |
| garrytan/gstack | Browser command service, product/release skills, substantial evaluation and platform tooling | **Do not adopt for the research milestone.** Current Playwright/browser checks and PR workflow already exist. Bun/browser builds, setup, updates and additional permission surfaces do not solve the scientific gap. |
| vectorize-io/hindsight | Persistent retained facts, retrieval and reflection using a database and LLM | **Defer behind a retrieval benchmark.** Real persistence is additional software capability; no demonstrated need over FIL's versioned files/manifests yet. Local inference is possible, but operational cost and provenance errors remain. |
| thedotmack/claude-mem | Automatic tool/session capture, generated summaries and persistent search | **Reject automatic capture for current FIL work.** Broad observations can contain protected raw/derived data. Not a substitute for an adjudicated research ledger. A future public/synthetic-only trial would need explicit capture and endpoint controls. |
| 666ghj/MiroFish | LLM-driven social simulation, graph memory and scenario reporting | **Reject for this mission.** Simulated agents are not observed football players or independent counterfactual evidence. Inspected implementation requires external Zep Cloud. |

These are task-fit decisions, not a claim that every rejected project is defective.
No project gets credit for a benchmark advertised by its authors as if FIL reproduced
that benchmark. No full-agent comparison was run and no measured improvement in
scientific novelty, hypothesis quality, predictive accuracy or productivity is claimed.

## Implementation and security findings

**K-Dense — MIT at the inspected pin.** Reviewed the hypothesis-generation,
critical-thinking and statistical-analysis skills, plus the complete validator and
its helper. The validator uses only the Python standard library, bounds input size,
rejects duplicate JSON keys, checks IDs/cross-links and reports human-review or blocked
states. It does not dereference the declared evidence ledger or verify source claims.
The statistical guidance includes important dependence/identification cautions, but
generic test/power recipes still need football-specific sampling assumptions. A large
skill collection also contains service-specific workflows; reviewing three skills
does not approve all scripts or external integrations. Promotional instructions inside
third-party skills were treated as reference text, not FIL policy.

Sources: [critical thinking](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/scientific-critical-thinking/SKILL.md),
[statistics](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/statistical-analysis/SKILL.md),
[validator](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/hypothesis-generation/scripts/validate_hypothesis_schema.py),
[helper](https://github.com/K-Dense-AI/scientific-agent-skills/blob/593377bb048752abb0152deab9fbb1083a6087df/skills/hypothesis-generation/scripts/_common.py).

**Superpowers and Addy — MIT.** Superpowers' SessionStart hook injects its meta-skill
into host context. That is a real instruction surface; don't install merely for a
verification checklist. Addy's hook explicitly says it is **not wired by default**
on hosts with native routing, including Codex. Its evaluation scaffolds are useful
examples, but are not FIL measurements. These procedures can make an unaided session
more consistent; they do not add access to scientific truth beyond Codex and FIL's
existing instructions, tests and source access.

Sources: [Superpowers hook](https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/hooks/session-start),
[verification](https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/skills/verification-before-completion/SKILL.md),
[Addy optional hook](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/hooks/session-start.sh),
[evaluation scaffolds](https://github.com/addyosmani/agent-skills/blob/aeac41d4d005999432bb7312f7ff06383a91d59d/evals/README.md).

**gstack — MIT; package 1.91.182.** Inspected setup, package commands, security policy
and telemetry scripts. Setup builds tools and installs host skills; documented team
mode includes updates. Browser tools may operate logged-in sessions depending on
configuration. Reviewed telemetry sync exits when its configured tier is `off`;
do not misrepresent telemetry as inevitably enabled or provider data as inevitably
uploaded. Any future use needs explicit review of browser state, endpoints, update
pinning, tool permission boundaries and dependencies. None was executed here.

Sources: [setup](https://github.com/garrytan/gstack/blob/b04cc35832183a89ed71eed628de15a6f315a1a8/setup),
[package](https://github.com/garrytan/gstack/blob/b04cc35832183a89ed71eed628de15a6f315a1a8/package.json),
[telemetry sync](https://github.com/garrytan/gstack/blob/b04cc35832183a89ed71eed628de15a6f315a1a8/bin/gstack-telemetry-sync).

**Hindsight — MIT.** Retain/recall/reflect plus persistent database state is a genuine
capability beyond stateless prompts. Inspected configuration, LLM transport and a
local llama.cpp compose example: a fully local inference path exists. That example
downloads model assets on first boot and uses moving container tags; it is not a
reviewed offline deployment artifact. Local-only operation would require pinned
images/models, model-license review, endpoint/embedding configuration audit, bounded
ingestion, deletion/export tests and evidence-linked contradiction handling. Generated
reflections must remain interpretations; immutable records remain authoritative.

Sources: [configuration](https://github.com/vectorize-io/hindsight/blob/2004c4fe46b0cc47ffa10cf482237e7173b6db9e/hindsight-api-slim/hindsight_api/config.py),
[transport](https://github.com/vectorize-io/hindsight/blob/2004c4fe46b0cc47ffa10cf482237e7173b6db9e/hindsight-api-slim/hindsight_api/engine/llm_transport.py),
[local example](https://github.com/vectorize-io/hindsight/blob/2004c4fe46b0cc47ffa10cf482237e7173b6db9e/docker/docker-compose/local-llm/docker-compose.yaml).

**claude-mem — Apache-2.0 at this pin; package 15.0.1.** Reviewed Codex and plugin
hook registrations, configuration defaults, security policy and architecture docs.
PostToolUse matches broadly and sends observations to its worker; Stop triggers
summarization. Documented SQLite/FTS and Chroma provide persistent retrieval. The
inspected default provider is `claude`; configurable OpenAI-compatible endpoints
also exist. Neither local storage nor a configurable endpoint proves that captured
content stays local. No claim that local operation is categorically impossible is
needed to reject unscreened automatic capture in FIL.

Sources: [Codex hooks](https://github.com/thedotmack/claude-mem/blob/dcb28a768c6be4b8e451843210558275caa8ec44/plugin/hooks/codex-hooks.json),
[settings](https://github.com/thedotmack/claude-mem/blob/dcb28a768c6be4b8e451843210558275caa8ec44/src/shared/SettingsDefaultsManager.ts),
[license](https://github.com/thedotmack/claude-mem/blob/dcb28a768c6be4b8e451843210558275caa8ec44/LICENSE).

**MiroFish — AGPL-3.0.** Inspected configuration, OpenAI-compatible client and Zep
memory updater. Configuration requires LLM and Zep keys and rejects `ZEP_API_URL`
with an explicit Cloud-only message. Upload and simulation/report code form an
external data path. An agent consensus would not independently test football claims.
AGPL integration obligations would also require review before redistribution or a
networked modified service; no such integration is proposed.

Sources: [configuration](https://github.com/666ghj/MiroFish/blob/7657031ac01184afe2cb220f5ee3545573b5e843/backend/app/config.py),
[memory updater](https://github.com/666ghj/MiroFish/blob/7657031ac01184afe2cb220f5ee3545573b5e843/backend/app/services/zep_graph_memory_updater.py).

## Measured bounded probe

Frozen [protocol](CAPABILITY_POC_PROTOCOL.md) before execution. The hash-guarded
[runner](../../scripts/probe_hypothesis_validator.py) copies two reviewed scripts,
the synthetic upstream template and its license into a temporary directory, strips the child
environment, requests no network permission and imposes execution limits. This is
reviewed code execution, not a general-purpose security sandbox.

Ten predeclared cases, three repetitions each, 30 retained samples. JSON parsing
accepted all ten syntactically valid fixtures. The component consistently rejected
all five deliberately malformed/inconsistent/declared-prohibited records: missing
falsifier field, dangling prediction link, missing causal estimand, undeclared source
and declared sensitive external upload. The blocked-governance record was **valid
but blocked**, with process exit code zero. A caller must inspect report status,
not treat successful execution as permission to proceed.

The control and all three semantic counterexamples were `VALID_FOR_HUMAN_REVIEW`:
invented provenance, iid analysis of dependent events, and a tautological falsifier.
This agrees with the script's explicit disclaimer; it is not a security defect or
failed promise of scientific certification. All outcomes were stable across repeats.
Initial per-case subprocess time: median 0.0510 s, range 0.0481–0.0608 s. These are
execution costs, not agent productivity or FIL startup improvements. Complete inputs,
stdout/stderr, hashes and timings: ignored local
`data/interim/capability-audit/probe-v1/receipt.json`.

A separate 30-sample reproduction produced identical case outputs. The final runner,
which also preserves the upstream license in the temporary copy, produced another
30 identical outputs. A modified helper was refused by its hash guard before any
third-party execution. These repetitions check reproducibility, not additional
independent scientific tasks; there are still only ten designed cases. The final
receipt is `data/interim/capability-audit/probe-final-verification.json`.

FIL's existing attribute registry already enforces required falsification, confounder,
baseline and independent-validation fields. The new component's useful incremental
coverage is linked hypothesis/prediction/measurement/analysis references and explicit
blocked-state reporting. The schemas differ, so their raw rejection counts are not
a fair comparative score. The simple JSON baseline quantifies linting only. There
is **no measured advantage over FIL's complete scientific review workflow**.

## Football libraries and smaller alternatives

| Alternative inspected | Useful capability | Decision |
|---|---|---|
| socceraction, `93a1242d46c104889205753accaabadb00c45c6d`, MIT | Reference SPADL conversions and established action-value research implementations | Read-only semantic cross-checks; don't install or fit xT/VAEP. Converter preserves original IDs for source actions but also transforms geometry, fixes actions and adds inferred dribbles. It cannot replace the immutable ledger. |
| StatsBombpy, `dc4a2461b7406df451e1bbb549e56d8d963cb5d7` in `hudl/statsbombpy` | Provider-maintained API/data convenience functions | Do not replace approved acquisition. `public.py` fetches configurable paths; defaults point to moving `master`, not FIL's authorized revision. README includes a provider user agreement; software access is not acquisition/training authorization. Binary `doc/LICENSE.pdf` not independently reviewed here, so no blanket rights clearance. |
| mplsoccer, `150be3f5d891526506a4c35b03256f173a70a14a`, MIT | Explicit provider pitch dimensions and publication plotting primitives | Good later choice if a specific local scientific figure needs it. No new dependency now: no plotting need in this milestone. Native pitch conventions remain distinct from certified physical attacking direction. |
| Existing JSON/Markdown/Git manifests, `rg`, pytest and independent scripts | Explicit persistent evidence, exact provenance, repeatable regression checking | **Keep now.** Low operational cost, transparent diffs and no new data path. Plain retrieval is the baseline any memory service must beat. |

Sources: [socceraction converter](https://github.com/ML-KULeuven/socceraction/blob/93a1242d46c104889205753accaabadb00c45c6d/socceraction/spadl/statsbomb.py),
[StatsBombpy paths](https://github.com/hudl/statsbombpy/blob/dc4a2461b7406df451e1bbb549e56d8d963cb5d7/statsbombpy/config.py),
[mplsoccer dimensions](https://github.com/andrewRowlinson/mplsoccer/blob/150be3f5d891526506a4c35b03256f173a70a14a/mplsoccer/soccer/dimensions.py).
No alternative's software license changes provider data rights.

## What changes in the next scientific milestone

Use this small review card inside the existing protocol, without installing a skill
router: **question and unit; at least two competing explanations; observations that
would distinguish them; source/measurement uncertainty; identification/common-support
assumptions; exact disconfirming result; frozen decision rule; evidence IDs and
protocol version; result-awareness/deviation log; independent check**. This is a
curated synthesis informed by K-Dense's MIT-licensed materials and FIL's existing
research skills, not a copied skill pack. Keep source facts, interpretations and
rejected claims distinct in the existing ledger. Retain permissions and exposed-match
status beside each evidence reference so memory cannot turn old tests into new ones.

The comparison-identifiability study remains the primary milestone. Its exact design
rank and source-linked support diagnostics test whether the current corpus supports
the proposed comparison, without fitting player effects. Review its protected local
research-lead report and [scope/limits](IDENTIFIABILITY_SCOPE.md). A new prompt,
retriever or simulated agent cannot add missing observed contexts, certification of
role/time, external construct evidence or untouched data.

Next: define a bounded context-conditioned football behavior question and a blinded
analyst task against a searchable event ledger; audit a genuinely longitudinal source
and identity/mobility contract before any new acquisition proposal. No new player
ability score or unapproved model fitting. Current provider-derived findings stay
local. A second annotation of already observed matches is not independent football
confirmation.

Only evaluate additional tooling if an observed task warrants it. For hypothesis
cards, use matched public/synthetic tasks, freeze errors/rubric before generation,
blind scientific reviewers, and measure unsupported claims, useful discriminating
tests, review time and missed dependence/rights constraints. For memory, freeze
fact/contradiction/version/permission queries, compare `rg` plus manifests against
local-only retrieval, and score exact evidence citation, stale/retracted claims,
unauthorized-content exposure, latency and maintenance cost. Do not deploy a memory
service unless repeatable benefit exceeds a simple index without provenance loss.
These are proposed experiments, not measured gains or authorization to ingest data.

No new owner decision is needed to follow the present recommendation. Any future
source acquisition, protected-data processing endpoint or additional model-training
scope retains its existing separate approval gate.
