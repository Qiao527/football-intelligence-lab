# Scouting data requirements for a confirmatory version

This is a requirements specification, not an acquisition request and not a claim that
any of it exists. It records what would have to be true for
`fil-scouting-decision-task-1` to move from a measurement audit to a confirmatory
answer. Current status: stage A stopped at the ceiling gate on the 63-match re-fetched
corpus (`SCOUTING_STAGE_A_RESULT.md`).

## What the current corpus already supports

One tournament of source events, lineups, provider shot xG and provider stage/date
metadata is enough to:

- build observed appearances without minutes and without role inference;
- estimate single-appearance reliability and the attenuation ceiling;
- show that a one-appearance criterion cannot support an increment claim.

That is all it supports. It cannot rank players, and it cannot separate "no
increment" from "increment lost to noise".

## Why five appearances, not three

With `r_single = 0.36` measured on this corpus, Spearman-Brown gives the reliability of
an *n*-appearance composite as `n r / (1 + (n-1) r)`:

| Appearances | Composite reliability |
| --- | --- |
| 1 | 0.36 |
| 2 | 0.53 |
| 3 | 0.63 |
| 5 | 0.74 |
| 10 | 0.85 |

A criterion window of one appearance caps the observable association at
`sqrt(0.53 x 0.36) = 0.44`, which is what stopped stage A. About **five comparable
appearances per player in each window** would put the ceiling near 0.74, comfortably
above the 0.45 threshold and high enough that a null result would mean something.

Five appearances per window is roughly ten matches with a stable role. A three-match
group stage cannot supply it; a club season or two to three tournaments can.

## Requirements

| ID | Requirement | Why it is needed | Blocking for |
| --- | --- | --- | --- |
| R1 | ≥5 comparable appearances per player in the observation window and ≥5 in the criterion window | raises the ceiling from 0.44 to about 0.74 | any increment claim |
| R2 | certified match-play minutes | per-90 quantities and honest exposure denominators do not exist without it | every per-90 framing |
| R3 | an untouched corpus, with file hashes and a partition manifest frozen before payload inspection | the 63 matches are development-exposed; no confirmatory claim is possible on them | confirmatory status |
| R4 | identity mapping across seasons and competitions, with a stated conflict rule | R1 and R3 imply more than one competition or season | pooled cohorts |
| R5 | a declared role taxonomy and provider position intervals | positions are currently verbatim metadata; no attacker mapping is defined | candidate-universe definition by role |
| R6 | repeated player-team crossings | separates player from team/role context | any "ability" reading |
| R7 | cost, contract or market data under explicit rights | only if a value or budget question is retained | recruitment framing |
| R8 | ≥2 independent analysts plus adjudication time and consent | the human task cannot be simulated or self-assessed | human decision claim |

R1, R2 and R3 are the ones that matter. Without them, no amount of extra modelling
substitutes for missing evidence.

## Acceptance checks for any future corpus

Every one of these is checkable before any metric is computed:

- file enumeration pinned to a revision, with size and content hash per file;
- competition metadata hash recorded, and match dates/stages read from it;
- per team-match goals reconciling to official scores, with own goals separated;
- every shot carrying finite source xG in `[0, 1]`, with no missing values imputed;
- shootouts excluded from match-play totals and reported separately;
- per-player shot totals summing to team shots, with unattributed shots reported;
- lineup position intervals present, with absent metadata counted rather than filled;
- minutes either certified for every appearance or explicitly unavailable.

## What is explicitly not requested

No video, no tracking, no pressure or availability data, no confidential medical or
contract information, and no provider data whose rights forbid local research use. A
larger corpus with the same weaknesses would not help: more rows do not fix a missing
criterion window.
