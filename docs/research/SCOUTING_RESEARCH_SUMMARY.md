# Research summary — can scouting data measure what it claims to measure?

This is the reader-facing summary of the scouting decision study. The protocols,
executions and limits live in the linked documents; this page states the question, the
answer and why the answer is credible.

## The question

A scouting decision usually starts with a ranking: who generates high-quality chances,
beyond goals. Two things must hold before such a ranking means anything. The underlying
quantity has to be stable enough per player to rank, and a richer metric has to add
information beyond the conventional one.

Most scouting content skips both checks. This study runs them.

## What was found

**1. One tournament cannot support the question.** With one appearance in the criterion
window, the observable ceiling was 0.436 against a pre-declared floor of 0.45. The study
stopped before any ranking, and reported that as the result rather than tuning the
threshold. That negative result is what motivated the second design.

**2. A league season can.** Fourteen comparable appearances per window move the ceiling
from 0.44 to 0.86. Both measurement gates pass.

**3. Source xG orders players better than goals.** Ranking players on window A and
scoring against window B, xG adds a small but detectable increment over goals, and the
increment replicated in a league that was never opened during development.

| Stage | Sample | Rank correlation | Ceiling | Decision |
| --- | --- | --- | --- | --- |
| Tournament, 1 appearance criterion | 63 matches, 377 pairs | — | 0.436 | stop |
| League, 14 appearances per window | 1,140 matches, 960 players | goals 0.741, xG 0.791 | 0.856 | proceed |
| Held-out league | 377 matches, 320 players | goals 0.690, xG 0.751 | 0.824 | replicated |

Primary contrast, xG minus goals: **+0.050 [0.033, 0.068]** on the development leagues,
**+0.061 [0.030, 0.094]** on the held-out league.

## The honest sentence

The increment is real, replicated, and still smaller than the pre-declared minimum
worthwhile difference of 0.10. It is detectable, not decision-grade. Anyone quoting this
as "xG is twice as good as goals" is misreading it; anyone quoting the failed gate as
"xG is useless" is misreading it in the other direction.

## Why the numbers are checkable

- Every threshold, arm, prior and endpoint was frozen before the data was opened.
- The held-out league was fetched only after the analysis code was frozen, and the
  confirmation script exposes no tunable argument.
- Source files are verified against a pinned revision by size and git blob SHA-1.
- Missing source values raise instead of becoming zero; unattributed shots block the
  run; shootouts are excluded and counted.
- No player label, shortlist or ability score is produced anywhere in the pipeline.

## What this does not say

No ability, potential, market value, transfer recommendation or causal claim. No per-90
quantity: minutes are not certified in this corpus. The criterion is future xG, not
goals. One season per league, no promoted/relegated separation, and players are
resampled without resampling teams, so the intervals are conditional.

## Reproduce

```bash
python scripts/fetch_league_corpus.py --implementation <sha>   # development set
python scripts/run_league_stage_a.py                           # gates
python scripts/run_league_increment.py                         # increment
python scripts/fetch_league_corpus.py --holdout --implementation <sha>
python scripts/run_holdout_confirmation.py --implementation <sha>
```

Every script writes a JSON record with inputs, settings and results. The source corpus
stays local and Git-ignored.

## Documents

| Document | Contents |
| --- | --- |
| [SCOUTING_DECISION_PROTOCOL.md](SCOUTING_DECISION_PROTOCOL.md) | Tournament design, gates, stop rules |
| [SCOUTING_STAGE_A_RESULT.md](SCOUTING_STAGE_A_RESULT.md) | Tournament execution: stop at the ceiling |
| [SCOUTING_MD3_CHECK.md](SCOUTING_MD3_CHECK.md) | Why the tournament criterion was noisy |
| [LEAGUE_SCOUTING_PROTOCOL.md](LEAGUE_SCOUTING_PROTOCOL.md) | League design, amendment, freeze |
| [LEAGUE_STAGE_A_RESULT.md](LEAGUE_STAGE_A_RESULT.md) | League gates pass |
| [LEAGUE_INCREMENT_RESULT.md](LEAGUE_INCREMENT_RESULT.md) | Development-league increment |
| [LEAGUE_CONFIRMATION_RESULT.md](LEAGUE_CONFIRMATION_RESULT.md) | Held-out replication |
| [SCOUTING_DATA_REQUIREMENTS.md](SCOUTING_DATA_REQUIREMENTS.md) | What a confirmatory corpus needs |
