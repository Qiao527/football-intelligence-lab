# League stage A execution — both gates pass, the increment test is unlocked

Status: executed once on the frozen development set. The held-out league was not
acquired. No ranking, criterion score or ability label exists from this run.

## Corpus

- StatsBomb Open Data, revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`.
- 1,140 matches: Premier League 380, La Liga 380, Serie A 380.
- 3,429,066,274 bytes over 2,280 files, fetched by
  `scripts/fetch_league_corpus.py`, every file verified against the git tree blob
  SHA-1 and size before the bundle manifest was written.
- Ligue 1 was never downloaded; it remains the sealed confirmation set.
- Minutes are not certified. Everything below is per appearance.

Command: `.venv/bin/python scripts/fetch_league_corpus.py` (5m27s, exit 0).

## Method

`scripts/run_league_stage_a.py` splits each team's own fixture list at its halfway
point (window A observation, window B criterion), keeps players with at least five
appearances in both windows, pairs adjacent window-A appearances per player, and
bootstraps players (10,000 draws, seed 1729). Spearman–Brown is applied at the median
appearance counts to obtain `r_obs` and `r_crit`; the ceiling is their geometric mean.

## Coverage

| Quantity | Value |
| --- | --- |
| Matches | 1,140 |
| Appearances | 31,585 (10,450 / 10,546 / 10,589 by league) |
| Players observed | 1,690 |
| Players included (≥5 in both windows) | 960 |
| Excluded for the appearance minimum | 730 |
| Median appearances per window | 14 / 14 |
| Players whose modal position changes between windows | 33.4% |

## Reliability (adjacent window-A appearances, per player)

| Metric | `r_single` | 95% player-bootstrap interval |
| --- | --- | --- |
| Shots | 0.402 | [0.364, 0.439] |
| Goals | 0.152 | [0.115, 0.189] |
| xG | 0.297 | [0.258, 0.337] |
| Non-penalty xG | 0.296 | [0.252, 0.342] |

Observation gate: `r_obs = 0.856`, lower bound `0.829`, against 0.50 / 0.30 — passes.
Comparative margin against goals: `+0.145`, no penalty.
Measurement ceiling: `r_obs = r_crit = 0.856`, against 0.45 — passes.
**Stage A proceeds.**

## Declared sensitivities

| Variant | Players | xG `r_single` | Ceiling | Decision |
| --- | --- | --- | --- | --- |
| Primary | 960 | 0.297 | 0.856 | proceed |
| Drop each team's last 3 fixtures | 930 | 0.296 | 0.850 | proceed |
| Modal position unchanged between windows | 639 | 0.323 | 0.870 | proceed |

The decision is unchanged under both declared sensitivities.

## Reading

- The league population passes where the tournament failed, for the reason the
  arithmetic predicted: the criterion is a 14-appearance composite instead of one
  match.
- Single-appearance xG reliability is *lower* here (0.297) than in the tournament
  (0.360). Club football adds rotation, opponent and role variation. The composite,
  not the single match, is what carries the signal.
- Goals are close to unusable at the single-appearance level (0.152). This is the
  clearest measurement argument yet that raw scoring is a noisy input for a
  per-appearance ranking, and it is descriptive, not an increment claim.
- A third of included players change modal position between windows, so the
  position-stable sensitivity matters; it gives a slightly higher estimate and the
  same decision.

## Not claimed and not done

- No increment test has been run. Passing the gates only licenses it.
- No player ranking, shortlist, ability label or per-90 quantity exists.
- The held-out league is unopened, so nothing here is confirmatory.
- No analyst task, no human result.

## Files

- `scripts/fetch_league_corpus.py`, `scripts/run_league_stage_a.py`
- `src/fil/research/league_scouting.py`, `tests/test_league_scouting.py`
- Local outputs: `data/interim/scouting/league-stage-a{,-drop3,-stable}.json`
- Corpus: `data/raw/statsbomb-league/` (Git-ignored)
