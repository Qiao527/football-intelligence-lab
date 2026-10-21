# Football Intelligence Lab (FIL)

FIL provides a reproducible Python foundation, immutable source acquisition and
canonical event normalization for one pinned historical StatsBomb match. It
includes period-aware clocks, traceable score reconstruction and a locally runnable
Streamlit Match Explorer with source xG analytics and a descriptive Tactical
Dashboard with directed passing networks and progression v1, plus source-traceable
Possession Flow and process analytics. Runtime dependencies are
PyArrow (typed Parquet), Streamlit and Plotly (local UI). AI agents are not implemented. The historical v0.2 notebook reported in the product
reference is absent here.

## Clean installation and checks

Prerequisite: **uv 0.12.23** ([official installation options](https://docs.astral.sh/uv/getting-started/installation/)).
The project enforces this version. `.python-version` pins **Python 3.11.14**;
`pyproject.toml` restricts support to Python 3.11. In a checkout containing FIL-001:

```bash
uv --version
uv python install
uv lock --check
uv sync --frozen
uv run --frozen ruff check .
uv run --frozen pytest -q
uv run --frozen python -I -c 'import fil; print(fil.__file__)'
```

For this cloud workspace, home is read-only. Before those commands, configure
writable tool storage outside the checkout:

```bash
export UV_CACHE_DIR=/workspace/.cache/uv
export UV_PYTHON_INSTALL_DIR=/workspace/.local/share/uv/python
export UV_PYTHON_BIN_DIR=/workspace/.local/bin
```

No activation, credentials, football data, GPU, database or service is needed for tests.
`uv sync` installs the editable package and the default `dev` group (Ruff and
pytest only). `uv.lock` fixes their transitive versions and artifact hashes.
The isolated build backend is exactly pinned in `pyproject.toml`. Package version
`0.1.0` identifies the foundation, not completion of a product roadmap version.

## Local development

Keep `uv.lock` committed. After an intentional reviewed dependency change, use
`uv lock`, inspect the diff, then rerun all frozen checks. Also run
`uv lock --check`: frozen sync alone does not reject every stale manifest.
PyArrow is pinned for FIL-003 storage. Add further libraries only when a scoped task needs them.

Test a separate, regular (non-editable) installation:

```bash
UV_PROJECT_ENVIRONMENT=.venv-wheel uv sync --frozen --no-editable
UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable ruff check .
UV_PROJECT_ENVIRONMENT=.venv-wheel uv run --frozen --no-editable pytest -q
```

Use an unused environment path for a fresh installation. CI repeats these checks
on Ubuntu 24.04 with no restored dependency cache, including manifest/lock
agreement, lint and tests in editable and regular installations. Only Linux
x86_64 / Python 3.11.14 is locally validated; other platforms are unverified.

## Project guidance

- [Repository instructions](AGENTS.md)
- [Product reference](docs/Football_Intelligence_Lab_Master_Reference.md)
- [Engineering handbook v3.0](docs/Football_Intelligence_Lab_Engineering_Handbook_v3.0.md)
- [Gate definitions and legacy mapping](docs/GATES.md)
- [Development workflow](docs/CODEX_WORKFLOW.md)
- [Current status](docs/STATUS.md)
- [Stacked development policy](docs/CODEX_WORKFLOW.md)
- [Canonical schema and normalization CLI](docs/CANONICAL_EVENTS.md)
- [Tactical definitions, evidence and local QA](docs/TACTICS.md)
- [Possession definitions, context semantics and local QA](docs/POSSESSIONS.md)
- [FIL-003 evidence and upstream dependency](docs/FIL-003_VERIFICATION.md)
- [Period-aware clock contract](docs/MATCH_CLOCK.md)
- [FIL-004 verification and stack status](docs/FIL-004_VERIFICATION.md)
- [FIL-001 verification](docs/FIL-001_VERIFICATION.md)
- [FIL-002 verification](docs/FIL-002_VERIFICATION.md)
- [Source terms and scoped gate assessment](docs/SOURCE_POLICY.md)
- [Local manifest specification](docs/SOURCE_MANIFEST.md)
- [Historical bootstrap review](docs/BOOTSTRAP_REVIEW.md)

The references describe intended functionality; their CLI, datasets, analytics
libraries and UI examples are future specifications. The existing [MIT license](LICENSE)
is unchanged. Future third-party data has separate license/attribution requirements.

## FIL-002: acquire and verify match 8658

Review [SOURCE_POLICY.md](docs/SOURCE_POLICY.md) before acquisition. The source
asks users to register with StatsBomb; the owner must confirm terms compliance
and noncommercial research use. Provider data is **not** covered by FIL's MIT
license or approved for redistribution. Published analysis requires StatsBomb
acknowledgement and its logo. Do not commit or distribute downloaded raw files.

From a clean checkout, with the uv environment configured above:

```bash
uv run --frozen python -m fil.ingestion.statsbomb acquire \
  --pipeline-revision "$(git rev-parse HEAD)"
uv run --frozen python -m fil.ingestion.statsbomb verify \
  data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb
```

`acquire` needs HTTPS access to `raw.githubusercontent.com`. It fetches only
the reviewed revision's README, license, competitions, match metadata, events
and lineups. No 360/tracking data is assumed. Files and `manifest.json` are
stored beneath ignored `data/raw/statsbomb/8658/<revision>/`; `--root` can select
another local ignored storage directory. No automatic fetch runs during tests,
CI, package installation or build.

`verify` is offline. Repeating acquisition verifies and reuses the cache without
network or timestamp/file changes. Changed/missing/duplicate/invalid inputs or
corrupt cached files fail with exit 1; CLI usage errors exit 2. A corrupt bundle
is never silently repaired. Preserve it for diagnosis and use another ignored
root if reacquisition is needed. A new upstream revision requires a separately
reviewed source-pin change. Read [manifest behavior](docs/SOURCE_MANIFEST.md)
for checks, atomic publication and limits.

An integrity PASS from this CLI is not DATA-SOURCE or DEL-SOURCE approval:
the rights assessment is tracked separately in SOURCE_POLICY.md. The owner has
confirmed registration and noncommercial research use for the reviewed fixture,
so those source gates pass within that scope. The immutable manifest/CLI retains
its acquisition-time pending status; it is not rewritten by a later confirmation.


## FIL-003: canonical normalization (offline)

FIL-003 is stacked on validated `feat/fil-002-data-acquisition` (PR #3), not
blocked on its merge. See the workflow and verification documents for its exact
parent SHA and acceptance status. Review the source policy before using data.

From the matching clean implementation checkout, acquire the raw bundle above
if it is not already present, then:

```bash
raw_bundle=data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb
uv run --frozen python -m fil.ingestion.normalize build \
  --raw-bundle "$raw_bundle" --pipeline-revision "$(git rev-parse HEAD)"
```

Use the returned `dataset` directory for verification or lookup:

```bash
uv run --frozen python -m fil.ingestion.normalize verify \
  --raw-bundle "$raw_bundle" --dataset "$dataset"
uv run --frozen python -m fil.ingestion.normalize lookup \
  --raw-bundle "$raw_bundle" --dataset "$dataset" \
  --event-id 4a44199a-3111-4e28-b567-9c1393e68dff
```

Set `dataset` to the path printed by build (it includes source-manifest digest,
adapter version and implementation SHA). Outputs are ignored under
`data/interim/events/`: Parquet, a full null/count quality report and an artifact
manifest. `--output-root` may select another ignored directory, never inside the
raw bundle. Normalization verifies the FIL-002 source bundle first and never
fetches or modifies it. Failures exit 1; usage errors exit 2.

Every source event is retained, including unrecognized types. Rebuilds verify
and reuse valid existing outputs without rewriting them. New roots generate
semantically identical tables with the same pinned implementation and source;
creation timestamps may differ. A corrupt artifact fails closed and is never
silently replaced. See the schema document for transformations and limitations.

Both raw and canonical records remain restricted to local noncommercial
research; neither Git, package artifacts nor a PR should contain provider data.
A copied provider `shot_xg` field is not a calculated xG metric. Clock, score,
spatial-direction and metric gates are outside FIL-003.


## FIL-004: period-aware clock (offline)

FIL-004 is stacked on `feat/fil-003-event-normalization` (PR #4). It preserves
all 53 canonical columns and adds exact millisecond clocks, display labels,
period-end/offset estimates and a pointer to the verified canonical manifest.
No provider field, raw source or canonical artifact is rewritten.

Set `raw_bundle` and `dataset` to the verified FIL-002/FIL-003 input directories
above. From the matching clean implementation checkout:

```bash
uv run --frozen python -m fil.time build \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --pipeline-revision "$(git rev-parse HEAD)"
```

Use the returned `clock_dataset` path with:

```bash
uv run --frozen python -m fil.time verify \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --clock-dataset "$clock_dataset"
```

Outputs stay ignored under `data/interim/clocks/`: `clock_events.parquet`,
`quality.json` and `manifest.json`. Existing artifacts are verified/reused,
never silently repaired. These commands are offline and reverify the complete
source/canonical chain; normal tests and CI use TEST-ONLY fixtures.

Use `fil.time.clock` for `PeriodRange`, exact timestamp parsing, period-relative
half-open filtering, regular/extra/match-play/shootout scopes, bin partitions
and chronological-range conversion. Default match-play excludes period 5;
shootout events retain source fields but have null match-play chronology.
Half End and the following Half Start can share a scalar boundary; period-aware
selection and original event IDs distinguish them. Read MATCH_CLOCK.md for the
terminal-endpoint rule, estimate propagation and strict malformed-input handling.
This clock is an event-phase axis, not elapsed wall time or a video timecode.
No score reconciliation or later analytics gate is claimed.


## FIL-005: score reconstruction and goal attribution (offline)

Stacked on validated FIL-004 PR #5. Read [the score contract and CLI](docs/SCORE_RECONSTRUCTION.md),
[stack reconciliation plan](docs/STACK_RECONCILIATION.md) and
[verification evidence](docs/FIL-005_VERIFICATION.md).
Using the verified input paths above:

```bash
uv run --frozen python -m fil.metrics.score_cli build \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --clock-dataset "$clock_dataset" --pipeline-revision "$(git rev-parse HEAD)"
uv run --frozen python -m fil.metrics.score_cli verify \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --clock-dataset "$clock_dataset" --score-dataset "$score_dataset"
```

Set `score_dataset` to build's returned path. Outputs stay ignored under
`data/interim/scores/`. All input fields survive; every score decision links to
original source IDs and verified manifests. Explicitly linked own-goal records
count once, match-play penalties count normally, and shootout goals stay separate.
Ambiguity or official final-score disagreement blocks output, never forces a
match. Repeated runs verify/reuse unchanged artifacts. No data redistribution,
new dependencies, later analytics implementation or merge is authorized.

## Local v0.3 Match Explorer

The Explorer uses the handbook's Streamlit/Plotly approach: read-only verified
source xG, cumulative progression, 5/10/15-minute threat windows, source-native
shot map, score-state progression, shared filters and exact original JSON
source evidence. It is for local noncommercial research; no deployment or
provider-data redistribution is included.

After frozen installation, review SOURCE_POLICY.md and acquire the source with
the existing FIL-002 command if needed. From a clean checkout:

```bash
uv run --frozen python -m fil.explorer.bootstrap \
  --raw data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb \
  --pipeline-revision "$(git rev-parse HEAD)"
# Copy the printed config path into the command below:
uv run --frozen python -m fil.explorer --config PATH_TO_LOCAL_CONFIG
```

Open the local Streamlit application in your browser (port 8501). The launcher
binds loopback only and disables telemetry; there are no externally hosted data
services or provider-data exports. No credentials/services are needed for unit
tests. A fresh raw acquisition needs source HTTPS and the existing usage rights.

Choose a period/window/team/player/type/outcome in the shared sidebar. Clicking
a threat bar selects its exact period bin. Clicking a shot opens that source ID,
original timestamp/JSON, source file link and manifest lineage. Reset restores
full match. Official 4–2 score and full-match cumulative/score backgrounds stay
visible under filtering. Threat is a transparent shot-xG sum, not tracking,
control or a predicted momentum model. See [metric definitions](docs/METRICS.md).

```bash
# Optional real-browser checks against the running local app (local Chromium required)
uv sync --frozen --group browser
uv run --frozen --group browser python scripts/check_explorer_browser.py PATH_TO_LOCAL_CONFIG
```

The Playwright tool is isolated in the optional browser group; normal offline
pytest includes Streamlit AppTest with clearly TEST-ONLY data and needs no browser.
Screenshots/browser reports remain ignored under data/interim/review. Do not
commit/publish provider-derived datasets or screenshots without rights review.
See [mission evidence](docs/reports/MISSION.md),
[integration report](docs/reports/INTEGRATION.md), and
[GitHub one-time setup](docs/GITHUB_AUTOMATION.md). Hosted checks and product
acceptance are reported separately from local verification.
