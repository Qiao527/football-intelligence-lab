# Held-out replication — the xG increment reproduces in Ligue 1

Status: one-shot confirmatory run on the sealed league. The analysis code was frozen
before the league was fetched; the held-out league has now been used and cannot serve
as a holdout again.

## Freeze and unsealing

- Analysis code frozen at commit `e3261b2`. The league modules
  (`league_scouting.py`, `league_increment.py`) have no diff since that commit.
- What changed after the freeze is acquisition and plumbing only: a `--holdout` flag
  on the fetch script and the new `run_holdout_confirmation.py`, which imports the
  frozen constants and exposes no tunable argument.
- Ligue 1 fetched into a separate root, `data/raw/statsbomb-league-holdout`: 377
  matches, 1,168,742,747 bytes, every file verified against the git tree blob SHA-1
  and size.
- Three bundles stalled during the parallel fetch and were built individually with the
  same verification; the total still matches the provider's 377 enumerated fixtures.

## Result

| Quantity | Development (3 leagues) | Held out (Ligue 1) |
| --- | --- | --- |
| Matches | 1,140 | 377 |
| Players included | 960 | 320 |
| Stage A ceiling | 0.856 | 0.824 |
| Stage A decision | proceed | proceed |
| C0 goals rank correlation | 0.741 | 0.690 |
| C1 source xG rank correlation | 0.791 | 0.751 |
| C2 open-play non-penalty xG | 0.785 | 0.733 |
| C1 − C0 | +0.050 [0.033, 0.068] | **+0.061 [0.030, 0.094]** |

**Verdict: `replicated`.** The paired interval in the held-out league excludes zero,
with the same sign and a similar magnitude.

## Reading

- The increment is not an artefact of the three development leagues. It reappears in a
  league that was never opened during development.
- The effect is still smaller than the pre-declared minimum worthwhile difference of
  0.10 in both samples. Replication raises confidence that the effect is real; it does
  not raise it to decision grade. Both statements belong together.
- The holdout point estimate is slightly larger (+0.061) but its interval is wider, as
  expected from 320 players instead of 960. The two intervals overlap substantially.
- Stage A also replicated: the league design clears the reliability and ceiling gates
  in a fresh league with a slightly lower ceiling (0.824).
- C2 remains below C1 in both samples. The filter-based "open play" arm does not add
  anything, which is consistent with the increment coming from chance quality rather
  than set-piece volume.

## Limits

- The criterion is window-B xG per appearance, not goals. Nothing here says xG orders
  players better for scoring goals.
- Players are resampled, teams are not; team dependence is only partly addressed.
- One season per league, no minutes, no per-90, no promoted/relegated separation.
- The held-out league is now exposed. Further work needs a new untouched corpus or a
  new question; it cannot reuse Ligue 1 as confirmation.
- This remains a measurement and ordering result, not an ability, value or transfer
  claim, and no player label or shortlist is published.

## Files

- `scripts/run_holdout_confirmation.py`, `scripts/fetch_league_corpus.py`
- Local output: `data/interim/scouting/holdout-confirmation.json` (Git-ignored)
- Corpus: `data/raw/statsbomb-league-holdout/` (Git-ignored)
