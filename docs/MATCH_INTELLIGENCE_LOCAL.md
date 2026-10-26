# Authorized local research mode

The default application needs no provider data. These commands are **only for the already
approved, already acquired local corpus**. They do not download anything, expand an allowlist
or authorize third-party use. Run from the repository root because accepted policy and approved
file-enumeration identities are checked against the existing versioned documents.

```bash
uv run --frozen python -m fil.intelligence prepare \
  --corpus data/interim/accepted-corpus/corpus/a44ebe2d87093584ba44541fc26a0a42d9f62b84 \
  --reference data/raw/statsbomb/8658/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb
uv run --frozen python -m fil.intelligence run \
  --local-library data/interim/intelligence/library.json
```

Select **Local research** in the sidebar, choose one of the 64 supported matches and run analysis.
The adapter requires pinned revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`, the accepted
metric-specific policy and unchanged source/quality identities. The catalog is metadata; a
report is displayed only after selected-match source/order/score verification. Physical period
boundaries, official minutes and physical attacking direction remain uncertified.

The source is **Hudl / StatsBomb Open Data**, covered by the reviewed provider-specific terms,
not FIL's MIT code license. Existing restrictions remain: local noncommercial research only;
no redistribution, public real-data service, external AI uploads, model publication or new
training scope. Owner approval does not override provider terms. This sprint acquires no data.
The application has no real-data download button. Sharing the screen with another person is
still a rights/access question; a local UI is not permission to distribute a provider report.

Raw data, library config, derived reports, source checks, timings and real-data screenshots
stay under ignored `data/`. Do not attach them to GitHub or distribute them for applications.
Use the fictional fixture route for a public-safe portfolio demonstration. No public deployment
has been performed or authorized here.

Independent local source check:

```bash
uv run --frozen python scripts/verify_intelligence_source.py \
  --library data/interim/intelligence/library.json
```

This checks all 64 matches against raw JSON using a separate Fraction-based computation,
original score reconciliation logic, complete membership coverage, all selected Shot IDs and
four filter variants. It also checks no input mutation and repeatability. It evaluates
engineering/source validity, **not independent football usefulness**. Existing research studies,
negative findings and the frozen football-relevance experiment are not rewritten.
