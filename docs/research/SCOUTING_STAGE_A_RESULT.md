# Scouting stage A execution — stop at the measurement ceiling

Status: executed once, on the 63 re-fetched matches, after the protocol and its
thresholds were frozen. Exploratory and development-exposed. No ranking, no criterion
score, no ability label and no player-level output exists from this run.

## Corpus used, and how it was established

- 63 StatsBomb matches (48 group, 15 knockout) at revision
  `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`; the 2018 final (8658) is not in this
  re-fetch and is not used.
- Re-fetched by `scripts/refetch_worldcup_corpus.py` from the public provider
  revision: 126 files, 191,244,134 bytes, every file checked against the approved
  enumeration by size and upstream git blob SHA-1, then by
  `fil.research.acquisition.verify`.
- Competition metadata (`data/matches/43/3.json`) matches the pinned
  `metadata_source_sha256`
  `f89dbd4aedcaf9c9e4ec9d8e745d5d54596500ec357d7489c914a2f126805adf`.
- Cross-check: 224,847 raw events in 63 matches. The previously recorded 64-match
  total was 227,825 and the missing fixture is the 2,978-event final, so the two
  counts reconcile exactly.
- This is a byte-level re-fetch, not a renewed acceptance. The original pilot
  reports, gate and batch proofs remain lost and no such claim is made.

## Method

`scripts/run_scouting_stage_a.py` projects raw records to the appearance contract
(`fil.research.scouting_raw`), builds observed actor appearances with source xG,
non-penalty xG, penalties and position metadata (`fil.research.scouting_appearances`),
then runs `fil.research.scouting_task.reliability_stage` with the ratified
thresholds, seed 1729 and 10,000 player-cluster bootstrap draws.

Before any estimate, the script requires per match/team shot counts from the built
rows to equal the raw Shot records in periods 1–4. It exits non-zero otherwise.

Executed commands:

```
.venv/bin/python scripts/refetch_worldcup_corpus.py --implementation <HEAD>
.venv/bin/python scripts/run_scouting_stage_a.py        # 13.7s, exit 0
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

## Observed coverage

| Quantity | Value |
| --- | --- |
| Matches / raw events | 63 / 224,847 |
| Players with an observation-window appearance | 603 |
| Appearances (all stages) | 1,760 (1,335 group, 425 knockout) |
| Zero-shot appearances | 882 |
| Penalty shots | 28 |
| Appearances without a position label | 0 |
| Players with two observation appearances (reliability pairs) | 377 |
| Players with one (excluded from pairs) | 138 |

## Reliability estimates (test–retest, first versus second group match)

| Metric | `r_single` | 95% player-bootstrap interval |
| --- | --- | --- |
| Shots | 0.419 | [0.297, 0.543] |
| Goals | 0.364 | [0.129, 0.544] |
| xG | 0.360 | [0.255, 0.486] |
| Non-penalty xG | 0.428 | [0.316, 0.558] |

Observation gate: `r_obs = 2r/(1+r) = 0.529` with lower bound `0.407`, against the
ratified 0.50 / 0.30 thresholds. **The gate passes.** The comparative margin against
goals is `-0.004`, far inside the 0.10 margin.

Measurement ceiling: `C = sqrt(0.529 x 0.360) = 0.436`, below the ratified 0.45
threshold. **Stage A therefore stops at the ceiling gate.** The increment test is
declared uninformative in advance and was not run.

## What this does and does not mean

- It does not mean source xG is useless, and it must not be written that way. It
  means this corpus cannot distinguish "no increment" from "increment lost to
  attenuation" for a one-appearance criterion.
- The stop is real but the margin is thin: 0.436 against 0.45, with `r_single`
  interval [0.255, 0.486]. `r_crit` is borrowed from the observation window and is
  expected to be optimistic, which pushes the true ceiling lower than 0.436; the
  decision direction is therefore defensible, but the exact margin should not be
  read as a comfortable failure.
- Shot counts (0.419) and non-penalty xG (0.428) are the most stable quantities;
  total xG (0.360) is the least stable of the four. That ordering is descriptive and
  does not license substituting one for another as a scouting input.
- 138 players contribute no pair, so the estimate describes regular starters, as the
  protocol states. All 603 players still enter the candidate universe.

## Not yet done

- No analyst task exists. No human result is claimed.
- No untouched corpus exists, so nothing here is confirmatory.

The matchday-3 heterogeneity check was run after this record and is reported in
[SCOUTING_MD3_CHECK.md](SCOUTING_MD3_CHECK.md). It does not change the decision.

## Files

- `scripts/refetch_worldcup_corpus.py`, `scripts/run_scouting_stage_a.py`
- `src/fil/research/scouting_raw.py`, `scouting_appearances.py`, `scouting_task.py`
- `tests/test_scouting_raw.py`, `test_scouting_appearances.py`,
  `test_scouting_decision.py`
- Local output: `data/interim/scouting/stage-a.json` (Git-ignored)
