# Matchday-3 heterogeneity check

Status: descriptive diagnostic, run once after stage A stopped at the ceiling gate.
It tests the borrowed `r_crit := r_single` assumption; it does not produce a new
estimate, a new threshold or a reason to re-run the gate.

## Method

For each of the 32 teams: points from matchdays 1–2 using provider match-play scores,
then the team's matchday-3 output. Buckets are `0–1`, `2–3` and `4–6` points. Reported
quantities are medians only, because the buckets hold 12, 6 and 14 teams. No test and
no p-value is computed, and no qualification or tiebreaker status is inferred.

Rotation is measured as starting-XI overlap from the provider `Starting XI` records:
matchday 1 to 2, and matchday 2 to 3.

Command: `.venv/bin/python scripts/check_scouting_md3.py` (exit 0). Local output:
`data/interim/scouting/md3-check.json`.

## Observed

| Bucket | Teams | Kept 1→2 | Kept 2→3 | Used | Shots | xG | xG/app |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0–1 | 12 | 9.0 | 8.0 | 14.0 | 11.5 | 1.324 | 0.096 |
| 2–3 | 6 | 8.0 | 9.5 | 14.0 | 10.0 | 1.441 | 0.103 |
| 4–6 | 14 | 10.0 | 8.0 | 14.0 | 13.0 | 1.083 | 0.081 |
| All | 32 | 9.5 | 8.0 | 14.0 | 12.0 | 1.210 | 0.090 |

`Kept` is starting-XI overlap with the previous matchday, `Used` is players
with at least one recorded action, and `xG/app` is the team total divided by `Used`.

## Reading

- Matchday 3 is a more rotated matchday than matchday 2 for the tournament as a whole:
  median retained starters fall from 9.5 to 8.0 of 11. That is a general property, not
  a qualification effect.
- Rotation barely separates the buckets. Teams already on 4–6 points rotate about as
  much as teams on 0–1 points (8.0 retained in both). The middle bucket is the
  exception at 9.5, on 6 teams, which is too few to interpret.
- The one gradient in the expected direction is output: already-qualified teams record
  lower xG per appearance (0.081) than the 0–1 (0.096) and 2–3 (0.103) buckets, roughly
  16–20% lower, while taking slightly more shots (13 versus 11.5 and 10). More shots
  with less xG per appearance is consistent with lower-quality attempts, but this
  design cannot separate that from opponent strength, game state or rotation.
- No bucket shows a stable, unrotated lineup. The criterion window is a rotated
  matchday for every team, which is the mechanism the protocol worried about.

## Bearing on the stop

The check neither rescues nor overturns the ceiling gate. It gives no evidence that
the borrowed single-appearance reliability is too pessimistic, and some weak evidence
that matchday 3 measures a different team state than matchdays 1–2. Recomputing the
ceiling from this diagnostic would be post-hoc tuning, so it is not done. The stage A
decision stands: stop as `uninformative`, with the thin margin already recorded.

## Limits

Provider points are match-play scores, not qualification or tiebreakers. Starting-XI
overlap ignores substitution timing, and no minutes are certified. Opponent strength,
game state, travel and rest are unmodelled. One tournament, 32 teams, all
development-exposed; nothing here is confirmatory.
