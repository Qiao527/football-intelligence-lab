# Football Intelligence Lab (FIL)

FIL provides a reproducible **engineering foundation**, not a football analytics
application. The importable `fil` package implements no metrics, ingestion,
dashboards or AI agent. There are no runtime dependencies. The historical v0.2
notebook reported in the product reference is absent here.

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

No activation, credentials, data download, GPU, database or service is needed.
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
- [Historical bootstrap review](docs/BOOTSTRAP_REVIEW.md)

The references describe intended functionality; their CLI, datasets, analytics
libraries and UI examples are future specifications. The existing [MIT license](LICENSE)
is unchanged. Future third-party data has separate license/attribution requirements.
