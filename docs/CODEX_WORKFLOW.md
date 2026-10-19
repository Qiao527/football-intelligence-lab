# FIL Codex-first delivery playbook

## Responsibility
- Human project owner: chooses scope and success conditions, authorizes new dependencies, data redistribution and merges.
- Codex Lead Engineer: implements vertical slices, owns tests and PR readiness; may propose design changes as explicit ADRs.
- Independent reviewer: separate Codex review context or human code review; must check raw event facts and tests independently, not accept a self-report as proof.
- Optional Claude: product/UX critique or second opinion; no default ownership or conflicting concurrent edits.

## Routine (every ticket)
1. **Inspect:** status, branch, relevant AGENTS.md files, handbook, source manifests, prior regressions.
2. **Plan:** state issue, in/out scope, files touched, input fixture, acceptance commands and risks.
3. **Implement:** one atomic, testable improvement; no unapproved new stacks or nonessential refactor.
4. **Verify:** ruff, pytest, independent source-event reconciliation; test data semantics not just UI.
5. **Review:** PR description and checklist. A separate reviewer checks a fresh diff, evidence and exceptions.
6. **Human gate:** developer reviews UI/analytics and explicitly authorizes merge/deploy.

## Recommended first execution
Read AGENTS.md and the two project reference documents. Inspect the existing repository without changing files. Audit current v0.2 code and manifests against FIL-001–FIL-004. Report what exists, test coverage and discrepancies. Then implement ONLY the first missing prerequisite in a reviewable change, run actual checks and show evidence. Do not start AI Analyst, network simulation, a new frontend stack or unauthorized API scraping.

## Starred-tool policy
- Frameworks are **references**, not mandatory global plugins. Default: repo-native AGENTS.md + three narrow FIL skills + tests.
- Evaluate addyosmani/agent-skills OR obra/superpowers on a throwaway branch; compare against baseline; adopt only a useful subset after license/security review.
- K-Dense scientific skills: selective use for research stage; not required for ingestion/UI.
- gstack: optional review discipline; not needed to achieve v0.3.
- FinceptTerminal: UI inspiration only until license analysis permits more.
- No autonomous multi-agent manager, unattended credential/tool permissions, browser scraping or repository-wide hooks by default.
