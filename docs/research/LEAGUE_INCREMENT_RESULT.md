# League increment result — source xG orders players better than goals

Status: exploratory, development leagues only, one run after the protocol amendment.
No player label, shortlist or ability claim is produced. The held-out league is
unopened.

## Method

- Rankings use window A only: per-appearance rates shrunk toward the leave-one-out
  positional-group mean with an appearances-equivalent prior of 10.
- C0 is goals per appearance; C1 is source xG per appearance; C2 is open-play
  non-penalty xG per appearance.
- Criterion is window-B xG per appearance, matching the primary stage A estimand.
- Paired Spearman differences, player-cluster bootstrap, 10,000 draws, seed 1729.

Command: `.venv/bin/python scripts/run_league_increment.py` (63s, exit 0).

## Result

| Arm | Rank correlation with window-B xG per appearance |
| --- | --- |
| C0 goals | 0.741 |
| C1 source xG | 0.791 |
| C2 open-play non-penalty xG | 0.785 |

| Contrast | Difference | 95% player-bootstrap interval | Label |
| --- | --- | --- | --- |
| C1 − C0 (primary) | +0.050 | [0.033, 0.068] | `increment` |
| C2 − C0 (secondary) | +0.044 | [0.026, 0.063] | `increment` |

Top-25 overlap with the criterion ordering: C0 0.52, C1 0.60, C2 0.52.

Per-league C1 − C0 point estimates: Premier League +0.054 (318 players),
La Liga +0.019 (327), Serie A +0.081 (315).

## Reading

- Source xG adds a detectable ordering advantage over goals. The interval excludes
  zero and the direction holds in all three leagues.
- The size is half the pre-declared minimum worthwhile difference of 0.10. The
  protocol defines no label for a positive interval smaller than that bar, so both
  facts are reported without relabelling: **detectable, but not decision-grade**.
- C0 is not a straw man. Goals per appearance already reaches 0.741 against future
  xG, because both quantities are driven by team chance creation and the shrinkage
  prior supplies most of the between-player ordering. The increment is about the
  residual ordering, not about goals being worthless.
- This does not contradict the stage A finding that single-appearance goals are
  nearly unrepeatable (0.152). That was reliability of a level; this is ranking
  against a different, also noisy, criterion. They answer different questions.
- C2 is slightly below C1. Excluding penalties and set pieces does not improve the
  ordering, so the gain is not coming from set-piece volume.

## Limits

- Players are resampled; teams are not. Team-level dependence is only partly
  addressed by the three-league split, so the interval is conditional.
- Per-league intervals were not bootstrapped at 10,000 draws; only point estimates
  are reported. La Liga's +0.019 is close enough to zero that it should not be read
  as negative or as positive without its own interval.
- The criterion is xG, not goals. An ordering that predicts goals would need a
  separate run and would inherit goals' much lower reliability.
- No minutes, no per-90, one season per league, no promoted/relegated separation.
- The held-out league is sealed, so nothing here is confirmatory.

## Next

The frozen analysis was run once on Ligue 1 and replicated:
[LEAGUE_CONFIRMATION_RESULT.md](LEAGUE_CONFIRMATION_RESULT.md). Ligue 1 is now exposed
and cannot be used as a holdout again.
