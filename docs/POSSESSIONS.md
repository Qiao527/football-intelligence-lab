# Source-traceable possessions and process analytics — fil-possession-1

This is the first factual v0.5 slice requested for FIL. It follows Engineering
Handbook §13 and Master Reference §3.3. Player ratings, candidate labels,
intentions, off-ball movement, trained possession value and causal bottleneck
claims are outside this slice.

## Source and identity contract

The analysis unit is `(match_id, provider_possession_id)`. StatsBomb Specification
v1.1, printed pp9–10, defines `possession` as a provider-labelled control period
and `possession_team` as the team starting it in control, including on opposition
events. Consecutive IDs may belong to the same team (for example after a throw-in).
We preserve this segmentation; no guessed replacement IDs or event-type-based
resegmentation are mixed into it.

Reviewed [provider specification](https://github.com/hudl/open-data/blob/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/doc/StatsBomb%20Open%20Data%20Specification%20v1.1.pdf),
SHA-256 `d5a8267939c5db35a9501b1a272cc9861a2bb3bef2f53c723d4a43ec1f5ef477`.
The real fixture is match 8658, France–Croatia, 2018-07-15, at source revision
`4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. All existing source rights apply;
provider files, local configs and screenshots remain local/ignored.

`ingestion.statsbomb_possessions.source_records` checks original ID, provider
index, period/timestamp, acting team/player, native possession ID/team and source
coordinates against the canonical row and embedded original JSON. The existing
full raw→canonical→clock→score verification remains a prerequisite. Duplicate
IDs/indices, inconsistent native owners, unsupported providers/frames, invalid
native IDs or reappearance of a closed labelled ID fail publication. Unknown
native IDs remain null in the action table; they are not assigned a synthetic
possession. Unassigned gaps carry explicit uncertainty. Missing owners retain
unknown-owner context rather than being called the opposition.

## Ordered sequences and boundaries

Every original record is retained in `possession_actions`, including Pressure,
fouls, opposing-team events, camera/administrative records and shootout events.
Order is provider index, preserving tied timestamps. Each labelled possession
stores the exact full `event_ids`, 1-based sequence order, first/last record IDs,
period-relative milliseconds, owner, participants, boundary evidence IDs and
quality flags. `team_id` and `possession_team_id` remain separate.

An `owner_action` means a record from the native owner, during periods 1–4,
with type Pass, Carry, Ball Receipt*, Dribble, Shot, Miscontrol, Dispossessed,
Clearance, Ball Recovery, Interception, Duel, Shield or Goal Keeper. This is an
explicit counting vocabulary; it does not certify that every action succeeded
or that the owner controlled the ball at every instant. Other owner records and
opposition records remain context. Participant IDs are distinct observed owner
action actors, not an inferred lineup. Period 5 remains in lineage but contributes
no owner-action, shot, pass/carry or progression process counts.

The source has a native ID spanning periods 1 and 2. It stays one possession and
is flagged `cross_period_provider_id`; its continuous duration/time-to-shot are
null. Paths contain an explicit PERIOD_BREAK when owner actions cross periods.
No line joins separate events or periods. Same-period `observed_span_seconds`
is last minus first recorded period timestamp, including stoppages/event gaps;
it is not live-ball control time or tracking duration.

## Entry and exit states

Entry is the first owner action; first/last context record IDs remain separate.
Native first-pass Kick Off, Goal Kick, Throw-in, Free Kick or Corner yields
`native_restart:<type>`; otherwise the reason states only the first observed
owner event type. No recovery method, counterattack, pressure escape or tactical
intention is guessed.

`shot_ending` means the last counted owner action is a Shot. A possession may
contain multiple shots, and may contain shots without being shot-ending after
later owner actions. Context/opponent records after a shot do not remove it.
`shot_event_ids`, count and exact source xG sum preserve all owner shots. The
linked own goal is a separate recorded terminal fact, not a shot or invented xG.

A **supported turnover** requires the last owner action to be Dispossessed,
Miscontrol, native Incomplete pass (9), or native Incomplete dribble, followed by
a new opposing-owner provider ID in the same period. Explicit out/offside,
non-advantage foul evidence, period boundaries, a next-owner native restart, or
unassigned intervening records prevent this classification. A provider team
change alone is insufficient. This is a conservative observed ending category,
not every actual turnover or an attribution of fault.

`end_reason` priority is period boundary → recorded own goal → shot-ending →
explicit out/offside → non-advantage foul observed → supported turnover →
provider boundary unresolved. A foul label reports the record, not inferred
referee intent. Every possession retains the next native ID/team (when present)
and boundary record IDs, including unresolved cases.

## Zones, progression paths and entries

All geometry remains native 120×80, y downward. Physical attacking ends remain
unknown. +x is the same declared convention as [progression v1](TACTICS.md),
not recovered stadium orientation. Native geometric zones: DEF `x<40`, MID
`40<=x<80`, ATT `x>=80`, with BOX taking precedence for `x>=102,18<=y<=62`.
Missing/unsupported points are UNKNOWN and are never imputed.

`zone_path` lists owner-action observed start zones and, for supported completed
passes/observed carries only, end zones. Adjacent identical states are collapsed;
backward/repeated visits, UNKNOWN and period breaks are retained. Direct
DEF→ATT is not expanded into an unobserved middle-third touch. These are event
observations, not continuous trajectories or proof of controlled occupation.
The path map draws each native pass/carry independently, with no invented links.

Progressive actions, final-third and box entries reuse the source-verified
[TACTICS.md](TACTICS.md) definitions/version: completed passes/observed carries,
valid endpoints, positive dx and ≥10-unit gain to conventional (120,40) for
progression; `x<80<=end_x` for third entry; outside→inside conventional box for
box entry. Entry counts can include repeated entries. Failed/unknown actions
remain in the sequence but do not become supported movements.

`reached_final_third` / `reached_box` mean **observed evidence** at an owner
start point or supported movement endpoint, including possessions starting there.
False means no such evidence, not certified absence of entry. Missing-position
quality flags expose incomplete coverage. `actions_to_first_final_third` counts
owner actions (including receipts) up to first such evidence; absence is null.

## Metric dictionary and denominators

All definitions use full native possession context, version `fil-possession-1`:

| Metric | Formal definition / units | Null and inclusion policy |
| --- | --- | --- |
| Eligible possession | Native ID with known official owner and ≥1 counted owner action | Admin-only/unknown-owner/shootout-only IDs remain lineage, outside analytic denominator |
| Source xG sum | Sum source `statsbomb_xg` over counted owner Shot IDs | Zero for no shots with known owner; unknown-owner sum is null; missing/invalid shot xG fails rather than becoming zero; match-play penalties included, shootout excluded |
| xG / possession | Eligible-cohort source xG sum / eligible possession count | Null for empty denominator; raw single-match descriptive ratio |
| P(shot given observed final third) | Number of reached-final-third eligible possessions with ≥1 shot / reached-final-third eligible possessions | Not pass count; starts in the third qualify; numerator/denominator exposed |
| P(box given observed final third) | Reached-final-third eligible possessions with observed box evidence / same denominator | Geometric evidence only; explicit numerator/denominator |
| Time to first shot | First counted Shot timestamp − first source record timestamp, seconds | Null for zero-shot/cross-period sequences; includes event gaps |
| Median time to shot | Median non-null first-shot spans | Shot-producing same-period subset only; selection bias and subset count disclosed |
| Turnover / entry / progressive counts | Number of classified native sequences or owner action IDs under rules above | Descriptive counts; no inferred lost value, per-90 rate, causal player importance or efficiency claim |

Aggregating all per-possession `event_ids` covers every assigned original ID
exactly once. All original records, including unassigned events, occur exactly
once in the action table. Boundary evidence may reference the next possession
for context and must not be counted as an additional member.

## Shared filters, context and drilldown

Select **Possession Flow** from Explorer's View control. The exact existing
`MatchFilter` selects period/window/acting team/player/type/outcome/pre-event
score-state events. The cohort is the set of native possessions **touched by
at least one selected original event**. It is not resegmented at a window edge.
Thus a selected opposition Pressure can legitimately expose another team's full
possession. Whole-cohort labels and per-action `matches_shared_filter` distinguish
this context from the original selected-event shot/xG KPIs above. Cohorts from
overlapping windows are not additive possession counts.

Terminal-state bar clicks or selectors choose a context chain; path endpoint
clicks and the original-event selector resolve exact source IDs/JSON and manifest.
All owner/opponent/admin records are available in the ordered ledger. Filtering
invalidates incompatible chain/event/ending state, and Reset clears focus while
retaining View. Source qualifications (including the cross-half native ID) are
visible without expanding JSON. No-possession selections show an explicit empty
state. Original Explorer/Tactical behavior remains independently regression checked.

## Immutable local QA and verification

```sh
python -m fil.possessions.artifacts --config /absolute/local-config.json \
  --pipeline-revision FULL_IMPLEMENTATION_SHA --output data/interim/possessions
python scripts/verify_possessions_source.py /absolute/local-config.json /absolute/bundle
python scripts/check_possessions_browser.py /absolute/local-config.json \
  --url http://127.0.0.1:8508 --output data/interim/possession-review
```

The immutable bundle has two typed Parquet tables, quality JSON with process
summary and a SHA-256 manifest. It records full input-tree fingerprint, source/
score manifests, version, actual code SHA, UTC creation, pinned Arrow/writer
settings and unchanged rights. Output is outside input trees; existing bundles
are recomputed and compared exactly, never silently repaired. Input-tree hashes
are checked before/after generation. Source and screenshots are not pushed.

Independent verification recomputes native groups, order, actors, geometry,
entries, paths/backtracking, terminal categories, shots/xG and span nulls directly
from original JSON. It checks real period/window/score/acting-team cohort queries
against raw memberships. Tests include malformed/missing labels, inconsistent
owners, duplicate/noncontiguous IDs, half boundaries/stoppage, tied timestamps,
shootout exclusion, zero/multi-shot sequences, no-coordinate/empty states,
source tampering, immutable rebuilds and shared UI context/reset behavior.

## Research audit clarification

`shot_after_final_third_*` and `box_after_final_third_*` summary fields currently
measure within-native-ID **co-occurrence**, not verified temporal ordering.
Their conditional fractions must not be interpreted as ordered transition
probabilities or tactical effectiveness. See [critical audit](research/ANALYTICS_AUDIT.md).
The strict later-shot labels in the research case use provider indices explicitly.
