# FIL project status — FIL-003 stacked development

- FIL-003 branch: `feat/fil-003-event-normalization`, based on FIL-002 branch
  `feat/fil-002-data-acquisition` at `5a18a4e1a417cfbf33941796552b25c9c8ab0c36`.
  Parent PR #3 exists (native Git head verified); owner reports its hosted CI
  passed. Stacked development is explicitly authorized; merge is not a prerequisite.
- Workflow now records dependency/evidence/assumptions, parent reconciliation,
  autonomous scoped progress, API delivery limitations and human acceptance.
- Implemented canonical schema v1 (53 typed columns), isolated StatsBomb adapter,
  deterministic Parquet build, offline verification, full source lineage and
  exact-ID reverse lookup. PyArrow 21.0.0 is the sole runtime dependency.
- Verified real match: 2,978 raw → 2,978 canonical rows, no exclusions/duplicate
  IDs; all original source records retained. Raw and derived provider files
  stay local/ignored and are not redistributed or packaged.
- Frozen install, Ruff, all 97 tests (0 skipped), package builds, real-data
  reconciliation, idempotent rebuild and fresh editable/regular installs pass.
  Repeated Parquet and quality-report bytes match on the tested platform.
- DATA-SOURCE/DEL-SOURCE remain scoped to the owner's confirmed local
  noncommercial research use. DATA-SCHEMA/DEL-SCHEMA have local technical
  verification; FIL-003 is **not human accepted**. See FIL-003_VERIFICATION.md.
- No reconstructed clocks, xG/xT calculations, score reconciliation, player
  ratings, networks, dashboards, scraping or AI agent. Provider xG is copied
  only; later gates and FIL-004 remain unimplemented/unpassed.
- Parent was re-fetched unchanged; no reconciliation needed. Original references,
  LICENSE, source policy, source acquisition code and raw provenance are intact.
- FIL-003 hosted CI/PR delivery are recorded separately when observable. No
  merge, deployment, rights expansion or material architecture change performed.
