# Tactical Dashboard — FIL-012 / v0.4

This slice is a descriptive, single-match event analysis. Select **Tactical
Dashboard** in the Explorer's View control. Both views share period, 5/10/15-minute
window, team, player, event type, outcome and pre-event score-state filters.
The official full-match score remains visible; foreground shots/xG/NPxG follow
the selection. Reset clears shared filters and entity focus while retaining View.

## Source-verified completed passes

`fil.ingestion.statsbomb_tactics.extract_tactics` adapts only verified
`statsbomb_open_data` canonical events carrying their original JSON and manifest.
It checks native identity, sequence, timestamp, actors, recipient and unchanged
coordinates against canonical fields. Original rows are never rewritten.

StatsBomb Open Data Specification v1.1, printed pp26–28, explicitly says:
“Passes missing an 'outcome' are completed passes.” The reviewed pinned document
is [Specification v1.1](https://github.com/hudl/open-data/blob/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/doc/StatsBomb%20Open%20Data%20Specification%20v1.1.pdf),
SHA-256 `d5a8267939c5db35a9501b1a272cc9861a2bb3bef2f53c723d4a43ec1f5ef477`.
This is a provider-specific omission rule, not a general null-means-success rule.
The adapter additionally requires a native Pass object with supported finite
nonnegative length, finite angle within ±π (1e-6 tolerance for native rounding),
a recognized height ID/name, valid passer, official team and positive recipient
ID, during periods 1–4. Missing coordinates do not erase a completed pass; they
prevent unsupported spatial calculations.

Explicit-null outcome, provider Unknown (77), unsupported/malformed pass
contracts and absent recipients remain separately audited. Incomplete (9),
Injury Clearance (74), Out (75) and Pass Offside (76) are failed passes. No
recipient is inferred from subsequent events. Duplicate event IDs fail. Carries
are native Carry observations, not reconstructed possession or proof of retention;
unsupported carry outcomes are unknown. Shootout actions are excluded.

## Directed networks and representative positions

A directed edge `(team_id, passer_id, recipient_id)` has weight equal to the
number of unique selected completed-pass original IDs. The reverse lookup
returns exactly those IDs. Nodes preserve player IDs, including recipients with
no located pass origins. Changing the shared selection recomputes edges, counts,
positions and evidence together. Network player drilldown includes incoming and
outgoing selected completed passes; edge drilldown includes only that edge.

Positions are arithmetic means of valid selected **completed-pass origins** for
that player. Sample counts, original sample IDs and x/y extrema expose the
sampling limits. No recipient position is invented from a pass endpoint; carries
and failed passes are not position samples. Unplaced nodes stay in QA tables.
These event averages are not formation, tracking, minutes played, touch maps or
physical locations between events. Sparse/unequal exposure is not corrected by
inventing per-90 rates. Coincident endpoints cannot display a meaningful arrow;
exact edge rows and IDs remain available. Reciprocal arrow offsets and width
buckets are display choices only; no source coordinates change.

## Progression v1 — fil-progression-1

This is an explicit project definition in **native provider units**, not an
industry-standard progressive-pass metric. Domain: supported completed passes
and observed carries in periods 1–4 with finite start/end coordinates in
[0,120]×[0,80]. Null/invalid endpoints yield null classifications with reasons.
Failed, unknown and excluded actions never become progressive actions.

For start `(x,y)` and end `(ex,ey)`, let the conventional attacking target be
`G=(120,40)`. Define `dx=ex-x` and
`gain=hypot(120-x,40-y)-hypot(120-ex,40-ey)`. A progressive action requires
`dx>0` and `gain>=10`, inclusively, in provider units. This excludes backward,
stationary and purely lateral actions. The target is a declared native +x
convention, not a certified physical attacking goal for every pass/carry.
See [SPATIAL.md](SPATIAL.md): physical stadium directions remain unknown,
coordinates are never flipped and the UI states this uncertainty.

Separately, final-third entry means `x<80` and `ex>=80`; conventional box entry
means the start is outside and end inside `x>=102, 18<=y<=62`. Entries are
independent of the ten-unit progression threshold, and use inclusive box bounds.
These geometric proxies do not establish a defensive line break, opponent
positions, tactical intent, threat, xT, VAEP or causal player contribution.
The QA table retains gain, dx, all classifications, reasons and exact source IDs.

## Comparisons and evidence

H1/H2 comparisons include each complete source-observed half and stoppage time.
Two explicit windows use the same period-aware partitioner as Explorer, including
terminal-instants only in the terminal bin. These comparisons replace only the
time dimension; score-state comparisons replace only score state. Other shared
filters remain active. Score states compare the acting team's verified score
**before** that original event, not possession team or final score. Linked own
goal events score once. Tables report raw counts and selected-event exposure;
unequal durations and player opportunity prevent causal/per-90 interpretations.

Click an edge midpoint, player or progressive endpoint to inspect contributing
original IDs, timestamps, native coordinates, source JSON and source manifest.
The entity selector also exposes all edges and unplaced players. Filtering clears
stale entity/event selections. All 2,978 original events remain in Explorer;
audit tables additionally retain every native pass/carry and exclusions.

## Immutable local artifacts and verification

From the frozen environment, using the existing verified local config:

```sh
python -m fil.explorer.tactical_data --config /absolute/local-config.json \
  --pipeline-revision FULL_IMPLEMENTATION_SHA --output data/interim/tactics
python scripts/verify_tactics_source.py /absolute/local-config.json /absolute/tactical-bundle
python scripts/check_tactics_browser.py /absolute/local-config.json \
  --url http://127.0.0.1:8504 --output data/interim/tactical-review
```

The bundle contains typed actions, completed passes, directed edges, nodes and
comparisons Parquet files, quality JSON and a SHA-256 manifest. It records input
fingerprints, original source/score manifests, code SHA, metric versions, UTC
creation time and exact Arrow/writer settings. It checks the entire input tree
before/after and verifies exact existing artifacts without repair/overwrite.
Artifacts must be outside immutable inputs. Local provider data/screenshots
remain ignored; source rights and attribution policy are unchanged.

Independent verification recomputes the expected edges, event sets, positions,
progression and comparisons directly from original provider JSON, including all
5/10/15-minute bins and pre-event score contexts. Chromium checks exercise actual
chart clicks, shared filters, empty selections, comparisons, desktop/mobile and
return to Explorer. Performance uses the original fresh-server/browser navigation
to Event ledger methodology; no OS cache eviction. Tactical computations are
lazy and cached by verified content. Existing startup/interaction budget failures
remain visible; actual results belong in [the report](reports/TACTICAL_DELIVERY.md).
