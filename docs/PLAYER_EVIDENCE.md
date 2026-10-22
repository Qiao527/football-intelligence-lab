# Player Evidence foundation

Version `fil-player-involvement-1`; dependent on Possession Flow PR #11 at
`83586739faeeb351dabe364db1df33747960bf4e`. This slice is descriptive, local,
single-match evidence. It does not pass a player ability or discovery validation gate.

## Grain and definitions

Rows use `(source, match_id, team_id, player_id)` with original provider IDs.
All native lineup records and any additional observed actors are retained. A zero
selected count means no selected records, not that a roster player did not play.
Missing positions remain null. Actorless events remain in the source and shared
KPIs; the quality report counts them explicitly.

Shared filters select actor records. Complete provider possession sequences and
shot context are constructed before filtering. Evidence dropdowns distinguish
selected actions from context shots outside the selection. Original JSON, IDs,
source manifest digest and native lineup source locator remain accessible.

| Field | Definition and limits |
| --- | --- |
| selected_events | Original selected records attributed to this team/player, including defensive/context records. Not touches. |
| owner_actions / owner_possessions | Selected owner-action records / distinct native possession IDs containing those actions. Full native chains retain opposition records separately. |
| completed_passes | Verified native Pass, no outcome, valid named recipient; uses existing Tactical extraction. Failed outcomes are 9/74/75/76; other unsupported cases remain unknown. |
| known_pass_completion_fraction | Completed / (completed + failed); unknown cases excluded and counted explicitly. Null for zero known attempts. Not an adjusted passing ability estimate. |
| progressive_passes / progressive_carries | Original Tactical progression v1 flags/IDs in selected actor records. Native +x geometry, no physical direction inference. See Tactical definitions. |
| owner_progressions_per100_actions | 100 × selected progressive owner-actions / selected owner-actions. Receipts, recoveries and other recorded owner actions are in the denominator. Null for zero denominator. Not minutes, possessions, equal opportunity or causal impact. |
| pre_shot_possessions | Distinct native IDs with a selected owner action by this actor before a same-team, same-period recorded Shot by provider index. Context shots and eligible action IDs retained. Includes restarts; no assumed uninterrupted control. Multiple participants may share the same shot; not additive credit. |
| native_shot_links | Selected Pass records with reciprocal `pass.assisted_shot_id` and `shot.key_pass_id`, same team/period (1–4), increasing provider index. One-sided/malformed references retained as unverified audit records, not certified links. |
| native_linked_shot_xg | Sum of original linked shot xG for those certified passes; linked shot may lie outside the filter. Context sum, not an inferred xA model or causal credit. |
| position_metadata | Original lineup position intervals/qualifiers, with source locator. No role inference from event averages. |
| minutes_played | Null throughout. Native interval strings have not passed substitution/stoppage-time/minute certification. No per-90 values. |

Owner-action vocabulary: Pass, Carry, Ball Receipt*, Dribble, Shot, Miscontrol,
Dispossessed, Clearance, Ball Recovery, Interception, Duel, Shield, Goal Keeper;
only records whose acting team equals native possession owner, periods 1–4.
Canonical event order is period/provider index, never rounded display time.

`combine_matches` enforces identical versioned schemas and unique source/match/team/player
grain. It does not pool opportunities, compare players, harmonize competitions,
or establish cross-match validity. Only this one real fixture has been verified.

## Possession audit correction

`fil-possession-2` supersedes v1 without overwriting v1 artifacts. Recorded own
goals cannot simultaneously qualify as inferred turnovers. Boundary evidence
now retains the actual terminal foul/offside/out/half-end/own-goal record even
when later administrative context follows it, plus next-owner restart evidence.
Regression fixtures cover both defects. Native ID segmentation, cross-period ID
uncertainty, source ordering and original event membership are preserved.

## Performance and audit controls

Full tactical and possession audit tables are now opt-in controls. Source
verification and factual reconstruction still execute; only unrequested large
browser serialization is deferred. The default possession is an actionable chain;
administrative chains remain selectable. Dense networks default to marker/hover
labels, with an explicit toggle for all names. Directed edges and source drilldown
remain available. Performance results belong to the delivery report, including
failed targets; these changes alone do not establish a speed improvement.

Local reproducibility: frozen install, `ruff check .`, `pytest -q`,
`python -m fil.explorer.player_data --config CONFIG --pipeline-revision FULL_SHA`,
then `python scripts/verify_players_source.py CONFIG BUNDLE`. Artifacts remain in
ignored local storage; raw data rights and distribution policy are unchanged.
