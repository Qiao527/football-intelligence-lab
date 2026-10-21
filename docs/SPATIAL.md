# StatsBomb coordinate audit — fil-statsbomb-spatial-1

The Explorer keeps `raw_statsbomb_120x80` coordinates unchanged. The origin is
upper left; x increases rightward and y increases downward. Values are provider
pitch units, not metres or tracking positions. Start and end x/y must be finite
and within [0,120] / [0,80] when present. Missing values remain null. Unsupported
coordinate domains fail rather than being silently converted.

Reference: Hudl/StatsBomb Open Data Events v4.0.0, Appendix 2, printed page 23,
at the same reviewed source revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`:
[provider specification](https://github.com/hudl/open-data/blob/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/doc/Open%20Data%20Events%20v4.0.0.pdf).
The reviewed PDF SHA-256 is
`05de42cc76b0c9cd26213d8e5c72610cac7d4d92c9c2ac878073a565dbb6c44a`.
The diagram was inspected, not inferred from text extraction. The older
Open Data Specification v1.1 also describes pass angles relative to the team's
attacking goal; this does not identify physical stadium ends.

## Frames and evidence limits

- **Provider frame:** Original event x/y, retained exactly and rendered with y
  downward. The two-team map overlays provider coordinates; it is not a map of
  both teams' simultaneous physical positions.
- **Action attacking left-to-right:** The real fixture's Shot/Goal endpoints
  have x=120 for each observed team/period. This corroborates an already
  positive-x shot frame, so an identity display is consistent for this fixture.
  It does not certify a universal convention for every event type or source
  version. A missing/opposite goal endpoint or no goal evidence leaves that
  group uncertified; shot-location averages are never used to guess direction.
- **World-fixed:** The acquired events, lineups and match metadata provide no
  certified physical attacking-end assignment per team/period. These directions
  remain null/unknown. Home/away labels, period parity, stadium name, or an
  observed shot cluster cannot recover them. No half/team flip is performed.

`metrics.spatial.spatial_report` records version, coordinate domain, axes,
identity transform, null counts, source specification, team/period goal event
IDs and endpoint evidence, and explicit world-fixed uncertainty. It is attached
to verified match metadata and new metric QA reports; original raw/canonical/
clock/score schemas and source records are untouched. The UI exposes the frame
and limits beside the map. Null locations remain in totals and the ledger.

Tests cover both teams/halves, unchanged source fields, unsupported domains,
start/end bounds, nonfinite values, null/no-goal uncertainty and missing/opposite
goal endpoints. The independent real-source verifier also checks every shot's
coordinates against its original JSON. This passes the scoped native-coordinate
audit, not physical-direction certification or tracking validation. Broader
DATA-SPATIAL acceptance remains a product-review decision.
