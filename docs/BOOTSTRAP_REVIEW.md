# FIL bootstrap review

## Scope and provenance

This change initializes the repository on `chore/fil-bootstrap` from baseline
`6a83fab20a59324eade106d0a67b258f236dd5fc` (the verified `origin/main` tip
at inspection). The baseline contained only `LICENSE`; its working tree was clean.

Imported all **17 files** from the user-provided `FIL_Codex_Starter_Pack.zip`,
preserving relative paths and file bytes. Archive SHA-256:
`10781a534a5c91256f66c72625137999449d7e22ba2d288c5e7846d49d99a153`.
The separately uploaded engineering handbook matches the archived handbook
byte for byte. `README.md` and this review are the only additional files.
No dependencies, application code, datasets, CI jobs, dashboards, or AI agent
were added. The existing `LICENSE` is unchanged.

The user's bootstrap request controls this change. Embedded prompts and task
briefs are guidance for later work, not authorization to execute FIL-001–004.
In particular, this import is not an execution of the FIL-000 task's forbidden
branch/edit/commit operations: the user explicitly requested those bootstrap
operations. Repository inspection after import was read-only until writing
these review notes and the README.

## Verified inventory

```text
.agents/skills/
  fil-source-audit/SKILL.md
  fil-metric-validation/SKILL.md
  fil-research-evidence/SKILL.md
.github/PULL_REQUEST_TEMPLATE.md
AGENTS.md
LICENSE                         # pre-existing
README.md                       # bootstrap addition
README_INSTALL.md
docs/
  BOOTSTRAP_REVIEW.md            # bootstrap addition
  CODEX_WORKFLOW.md
  Football_Intelligence_Lab_Master_Reference.md
  Football_Intelligence_Lab_Engineering_Handbook_v3.0.md
  STATUS.md
  tasks/FIL-000.md ... FIL-004.md
src/fil/ingestion/AGENTS.md
src/fil/metrics/AGENTS.md
```

No notebook, `evidence_packet.json`, raw source manifest, canonical schema,
metric implementation, test suite, package metadata, lockfile, or runnable CLI
exists. The `src/fil` directories contain instructions only. The v0.2 prototype
reported in the Master Reference is **unverified here**, not recovered or run.

| Task | Current implementation status | Evidence / next prerequisite |
| --- | --- | --- |
| FIL-001 | MISSING | No Python metadata, lockfile, CI or tests; guidance import is not the reproducible environment required by the task. |
| FIL-002 | MISSING | No raw fixture, rights review or provenance manifest. |
| FIL-003 | MISSING | No normalizer, schema or Parquet artifacts. |
| FIL-004 | MISSING | No clock module or period-boundary tests. |

## Instruction consistency findings

- Both referenced documents and all root/directory instruction files are
  present and were read. Shared integrity rules agree: immutable raw data,
  source IDs and nulls preserved, period-aware clocks, provider xG, explicit
  source rights, independent review, and deferred AI/research features.
- **Gate labels differ.** Root `AGENTS.md` uses G0–G5 delivery stages; handbook
  section 10.1 uses G0–G7 data/interaction/research gates. For example, root G3
  means shots/xG, while section 10.1 G3 means spatial checks. Future task/PR
  acceptance should name the gate and document section, not just its number;
  harmonizing the taxonomy needs an explicit documentation decision before
  enforcing automated gates. No gate has passed in this bootstrap.
- **Layouts differ in detail.** Master Reference section 7 sketches `src/ingestion`
  and `src/metrics`; handbook section 2.2 refines this to `src/fil/...`, matching
  the imported local instructions. Keep the refined layout for future work;
  the target tree is not a list of already implemented modules.
- **Historical status is not current implementation.** Master Reference section
  6.1 reports an external v0.2 notebook. Imported `docs/STATUS.md` qualifies
  that claim as a documentation baseline; this review supplies the actual
  checkout inventory and does not claim the notebook exists here.
- Root Python 3.11 target is compatible with the handbook's 3.11-or-3.12 choice.
  The current host reports Python 3.12.14; no Python 3.11 project environment
  was prepared or validated in this documentation import. FIL-001 must resolve
  and pin the target before compatibility claims.
- Instructions mentioning a metric dictionary, source policy, manifests,
  fixtures, CLI, or CI describe future prerequisites. Their absence is expected
  for this import and blocks claims of analytical readiness.
- `FIL-000` remains a read-only audit brief; it does not authorize later
  implementation. The workflow's suggestion to implement a next prerequisite
  is deferred to a separate user-scoped task.

The supplied reference and instruction files remain unchanged so reviewers can
distinguish source material from these audit findings.

## Project skill validation

All three skills have `SKILL.md` front matter with a nonempty `name` and
`description`; names match their parent directories. Bodies were reviewed.
They contain procedural guidance, with no bundled scripts, hooks, third-party
installer, credential binding, or automatic permission grant.

| Skill | Intended trigger | Bootstrap disposition |
| --- | --- | --- |
| `fil-source-audit` | Importing/refreshing football event data | Structurally valid; not executed, no event data imported. |
| `fil-metric-validation` | Changing metrics, clocks, schemas or filters | Structurally valid; not executed, no such code exists. |
| `fil-research-evidence` | v0.5+ research with validated event data | Structurally valid; deferred, prerequisites absent. |

This validates file structure and guidance, not runtime discovery by every
Codex client or the correctness of future analytical outputs.

## Verification evidence

Commands were run from the repository root unless stated otherwise.

| Command / check | Exit | Observed result |
| --- | --- | --- |
| `git switch -c chore/fil-bootstrap` | 0 | Requested branch created. |
| Python archive safety/import check | 0 | No absolute/traversal/Git-metadata paths, symlinks or existing-file collisions; standalone handbook identical. |
| Python archive/structure/skill validation | 0 | All 17 imported files byte-identical; three skills and three AGENTS files; reference/task paths present; LICENSE unchanged; no Python implementation or manifest. |
| Initial validation with mistaken expected count of 18 | 1 | Count assertion failed; corrected to actual archive count of 17, then reran successfully. |
| `git diff --exit-code HEAD -- LICENSE` | 0 | Existing license unchanged. |
| `git ls-remote origin refs/heads/main` | 0 | Main matches the baseline SHA above. |
| `ruff check .` | 127 | Command unavailable; lint did not run. |
| `pytest -q` | 127 | Command unavailable; tests did not run. No test suite exists. |
| `git diff --cached --check` | 2 | Nine pre-existing Markdown hard-break lines in the supplied references have trailing spaces; preserved for byte-identical import. |
| `git -c core.whitespace=blank-at-eof,space-before-tab diff --cached --check` | 0 | Remaining whitespace checks pass; Markdown line-ending spaces explicitly permitted for this check only. |
| `python --version` | 0 | Python 3.12.14; not a project compatibility test. |
| `gh auth status` | 1 | CLI authentication check unsuccessful; no credential values inspected. |
| `gh api repos/Qiao527/football-intelligence-lab --jq '{default_branch: .default_branch, permissions: .permissions}'` | 1 | API request returned Forbidden; Git read access does not establish API access. |

Reproduce the main import/integrity checks using the original uploaded ZIP:

```bash
python - /path/to/FIL_Codex_Starter_Pack.zip <<'PY'
from pathlib import Path, PurePosixPath
import hashlib, re, stat, subprocess, sys, zipfile
archive = Path(sys.argv[1])
assert hashlib.sha256(archive.read_bytes()).hexdigest() == "10781a534a5c91256f66c72625137999449d7e22ba2d288c5e7846d49d99a153"
with zipfile.ZipFile(archive) as z:
    files = [i for i in z.infolist() if not i.is_dir()]
    assert len(files) == 17
    for i in files:
        p = PurePosixPath(i.filename)
        assert not p.is_absolute() and '..' not in p.parts and '.git' not in p.parts
        assert not stat.S_ISLNK(i.external_attr >> 16)
        assert Path(i.filename).read_bytes() == z.read(i)
assert Path('LICENSE').read_bytes() == subprocess.check_output(
    ['git', 'show', '6a83fab20a59324eade106d0a67b258f236dd5fc:LICENSE'])
skills = sorted(Path('.agents/skills').glob('*/SKILL.md'))
assert len(skills) == 3
for p in skills:
    m = re.fullmatch(r'---\nname: ([a-z0-9-]+)\ndescription: ([^\n]+)\n---\n(.+)', p.read_text(), re.S)
    assert m and m[1] == p.parent.name and m[3].strip()
assert len(list(Path('src').rglob('AGENTS.md'))) == 2
assert not list(Path('src').rglob('*.py'))
assert not Path('pyproject.toml').exists()
print('PASS: archive integrity, paths, LICENSE, skill metadata, bootstrap-only scope')
PY
git -c core.whitespace=blank-at-eof,space-before-tab diff --check 6a83fab20a59324eade106d0a67b258f236dd5fc
```

No fixture provenance, numerical reconciliation, screenshots, application
behavior, test PASS, independent review, or merge authorization is claimed.
The smallest proposed next PR is FIL-001: choose the pinned Python target and
reviewed dependencies, then add reproducible project metadata, lockfile and
meaningful checks. Do not start source acquisition or analytics in this PR.
