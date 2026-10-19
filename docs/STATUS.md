# FIL project status — FIL-002

- FIL-001 is merged (PR #2); this milestone starts from main `cde6c66`.
- Source-preserving acquisition and offline verification CLI implemented for
  Hudl/StatsBomb match 8658 at upstream revision
  `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. No runtime dependencies added.
- Source records verify FIFA World Cup 2018 Final, 2018-07-15, France–Croatia.
  Actual local events: 2,978; all IDs unique. Lineups and source terms acquired;
  no 360/tracking availability assumed.
- Original provider files and actual manifest are in ignored local `data/raw/`;
  no provider datasets, documents or raw manifest are committed or packaged.
- Frozen installs, Ruff, 41 offline tests (0 skipped), wheel/source build and
  a cold-cache fresh regular installation/acquisition passed. Repeat acquisition
  is offline and preserves file bytes/timestamps. See [evidence](FIL-002_VERIFICATION.md).
- Source integrity checks pass; DATA-SOURCE and DEL-SOURCE remain PENDING on
  owner registration/terms compliance. Redistribution and commercial use are
  not approved. See [source policy](SOURCE_POLICY.md).
- No normalization, clock, score reconciliation, xG/xT, player ratings, networks,
  dashboards, scraping or AI agent implemented. FIL-003 and later gates remain
  unpassed. The historical v0.2 notebook/evidence packet is absent and unverified.
- Original references, LICENSE and dependency lock are unchanged. Branch is
  pushed; API Forbidden responses block PR creation and hosted CI observation.
  The prepared PR body and exact failures are in the verification report.
  No merge, deployment or environment publication performed.
