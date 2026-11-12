# Match Explorer UI notes

The Streamlit Match Explorer is the local research surface. It renders one verified
historical match, and every number in it links to original event IDs. This page records
the visual system and, deliberately, why there are no committed screenshots of it.

## Why no screenshots here

The Explorer only runs on a verified local provider bundle. Any screenshot of it would
contain provider-derived names, event IDs and coordinates, so committing one would
redistribute source material the project is only licensed to keep local. This is the
same rule that keeps the corpus ignored (`data/raw/`), and it is why the images in
`docs/images/` come from the synthetic public demo instead.

If you run it locally, the screenshots stay local too:

```bash
python -m fil.explorer.bootstrap --raw <verified raw bundle> --pipeline-revision <sha>
FIL_EXPLORER_CONFIG=data/interim/local-explorer/*/local-config.json \
  python -m streamlit run src/fil/explorer/app.py
```

## What the surface is

- A hero block with the official score, competition, season, date and source, so the
  reader knows the scope before reading any metric.
- One shared selection (period, window, team, player, event type, outcome, score state)
  that drives every panel below it. Nothing carries a stale filter.
- Metric cards, a cumulative chance-weight curve, a shot map, a comparison ledger and an
  evidence inspector that shows the original record.

## Visual system

| Token | Value | Use |
| --- | --- | --- |
| background | `#0b1220` with a radial lift at the top | page |
| panel | `#121c2b` / `#162233` | cards, tabs, expanders |
| line | `#26344a` | borders and dividers |
| ink | `#e8eef6` | body text |
| muted | `#9fb0c6` | captions, labels |
| accent | `#67b6d4` | links, selected tab |
| accent 2 | `#7bd3c4` | provenance chip, deltas |

Type is Inter with a system fallback, headings at negative tracking, metric labels in
small caps. Metric cards use a subtle top gradient and an inset highlight instead of a
drop shadow, so a wall of KPIs does not read as floating boxes.

The layout keeps the original two-column metric grid below 600 px, because the default
Streamlit stacking turned six metrics into six full-width rows on a phone.

## Constraints that shaped it

- No external fonts or assets: the app must run offline against a local bundle.
- No colour used as the only signal: team identity is always named as well as coloured.
- Cards never imply a rating. The panels show counts, sums and event IDs, and the
  captions say which of those is an accounting choice rather than a football judgement.
