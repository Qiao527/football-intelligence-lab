> Historical starter-pack instructions. For the working product, use [README.md](README.md).

# Football Intelligence Lab — Codex Starter Pack

This package is **configuration and task guidance**, not a runnable analytics program. It does not connect to GitHub or run Codex by itself.

## Safe installation
1. Create a new branch inside your actual FIL repository.
2. Unzip into a temporary folder and inspect the files. DO NOT blindly overwrite existing AGENTS.md or source files.
3. Copy the desired files to matching relative paths, merging with accurate existing project guidance.
4. Read `docs/Football_Intelligence_Lab_Master_Reference.md` and `docs/Football_Intelligence_Lab_Engineering_Handbook_v3.0.md`.
5. Open Codex at the repository root and issue the FIL-000 read-only audit, as defined in `docs/tasks/FIL-000.md`.
6. Review actual status before instructing Codex to implement FIL-001 or any other task.

## Key files
- `AGENTS.md` — persistent repository-wide project rules.
- `src/fil/*/AGENTS.md` — directory-level constraints (copy if corresponding dirs exist / are in planned architecture).
- `.agents/skills/fil-*/SKILL.md` — three phase-aware specialist guidance packs.
- `.github/PULL_REQUEST_TEMPLATE.md` — human-verifiable evidence and merge conditions.
- `docs/CODEX_WORKFLOW.md` — task cycle and Codex prompt.
- `docs/STATUS.md` — historical status baseline, replace only after real repo audit.

## Data / privacy
No API keys, user tokens, commercial football data or executable third-party agent hooks are included.
