# Football Intelligence Lab (FIL)

FIL provides a reproducible Python foundation and a source-preserving acquisition
workflow for one pinned historical StatsBomb match. It implements no metrics,
normalization, dashboards or AI agent and has no runtime dependencies. The
historical v0.2 notebook reported in the product reference is absent here.

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
Do not add analytics libraries until a scoped task needs them.

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
