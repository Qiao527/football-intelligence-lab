# League scouting protocol v2 — fil-league-scouting-task-2

Frozen on 2026-11-11 after owner ratification of the five declared choices. No league
data was acquired or inspected before this freeze. Supersedes
`fil-scouting-decision-task-1` for the population only; the v1 protocol, its execution
and its negative result remain unchanged history.

## Why a new population

The v1 corpus is one men's international tournament: at most three group matches per
player, so the criterion window had a single appearance and the measurement ceiling
fell to 0.436, below the 0.45 gate. A league season supplies roughly nineteen fixtures
per window, which raises the composite reliability from 0.36 to about 0.85 and makes
the increment test interpretable for the first time.

This is a population change, not a data top-up: windows are defined by a team's league
fixtures, not by matchday numbers inside a tournament.

## Source, scope and rights

- Provider: StatsBomb Open Data, revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`,
  same repository and licence already used for the v1 corpus.
- Development leagues (men's, 2015/16): Premier League 380 matches, La Liga 380,
  Serie A 380.
- Held-out league: Ligue 1, 377 matches, sealed until the confirmatory run. Three
  fixtures are absent from the provider release; they are reported and never
  imputed, and they make some teams' fixture lists one match shorter.
- Excluded: the 2015/16 Bundesliga slice, which contains 34 matches rather than a
  season, and every partial season in the repository (34–38 match samples).
- Rights unchanged: local non-commercial research, no redistribution, no external
  upload, no deployment, no model publication. No new permission is claimed.
- Minutes are **not** certified. Per-appearance denominators only; per-90 remains
  blocked and must not appear in any output.

## Windows

For each player-team-season, take that team's league fixtures ordered by date and
split them at the halfway point of the team's own fixture list.

- Window A (observation): the first `ceil(n/2)` fixtures.
- Window B (criterion): the remaining fixtures.
- Primary inclusion for the reliability stage: at least five recorded appearances in
  each window.
- Declared sensitivity: drop each team's final three fixtures from window B, because
  end-of-season matches can be played with nothing at stake.
- Appearance means at least one raw record naming the player as actor. A roster member
  with no records is unobserved, never zero exposure.

The end-of-season threat is the league analogue of the matchday-3 problem already
measured in v1. It is reported, not assumed away.

## Reliability stage (unchanged estimands, new windows)

- `r_single` = test–retest correlation between consecutive window-A appearances for the
  same player, so both members of a pair share the window and roughly the same role
  context.
- `r_obs` = Spearman–Brown composite over the median number of window-A appearances
  per included player.
- `r_crit` = the same single-appearance estimate carried to window B by
  Spearman–Brown over the median number of window-B appearances. Unlike v1 the
  criterion is a composite, not one match, which is the entire point of the change.
- Ceiling `C = sqrt(r_obs * r_crit)`; stop if `C < 0.45`.
- Ratified thresholds carry over unchanged: 0.50 / 0.30 / 0.10 / 0.45 / 0.10.

Role stability: the provider position metadata is joined per appearance and kept
verbatim. The fraction of included players whose recorded positions differ between
windows is reported, and a sensitivity restricted to unchanged positions is required.
No role is inferred from event averages.

## Increment stage (runs only if both gates pass)

- Arms: C0 goals/shots/appearances; C1 plus source xG and non-penalty xG; C2 plus
  native shot locations, body part and play pattern. The shared limitations panel
  appears in every arm.
- Ranking input: per-appearance rates shrunk toward the positional-group mean with a
  fixed appearances-equivalent prior of 10; sensitivities at 0, 5 and 20.
- Primary endpoint: difference in Spearman correlation with window-B xG per
  appearance between C2 and C0, on the development leagues.
- Secondary: top-*k* precision, Brier score for "at least one shot in window B", and
  calibration in fixed bins.
- Uncertainty: player-cluster bootstrap; cluster components by team; leave-one-league-
  out sensitivity on the development leagues.
- Pre-declared labels for a zero-spanning interval stay as in v1: `uninformative`,
  `no detectable increment`, `inconclusive`.

## Confirmatory run

The held-out league is opened once, after the development-league result and the
analysis code are frozen, with the exact code commit recorded. No refitting, no prior
or *k* changes, no candidate-threshold changes. A failure there is reported as a
failure to replicate, not repaired by returning to the development leagues.

Exposure log: every stage records which league, match ids, columns and summaries were
inspected, in order.

## Not claimed

No ability, potential, value, injury risk, transfer or budget claim. No causal effect.
No physical direction or tracking. No per-90 quantity. No pooling with the v1
tournament corpus unless a separate contract specifies it.

## Owner decisions

Ratified by the project owner on 2026-11-11:

1. Held-out league: **Ligue 1** (377 matches), replacing the proposed Serie A. Serie A
   moves into the development set.
2. Window split at each team's own fixture halfway point: confirmed.
3. End-of-season sensitivity dropping the final three fixtures: confirmed.
4. Minimum five appearances per window: confirmed.
5. The three missing fixtures now sit in the held-out league rather than a development
   league; they are reported, never imputed, and no missing match is scored.

The development set is therefore 1,140 matches (Premier League 380, La Liga 380,
Serie A 380) and the held-out set is 377.
