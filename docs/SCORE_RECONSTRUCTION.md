# Score and goal attribution v1 — FIL-005

`fil-score-1` is a cumulative count of **distinct source-awarded goals**.
This is event reconstruction, not goal prediction, xG aggregation or a decision
about whether a referee should have awarded a goal. Original provider records,
canonical columns and FIL-004 clock semantics remain immutable.

## Metric dictionary

For team T and ordered source event e:

`match_score_after(T,e) = sum(1[beneficiary(g)=T])`

over resolved, scored decisions g in periods 1–4 whose anchor provider index
is at or before e. `before` excludes an award anchored at e. Units: integer
goals, one match, ordered by `(period, provider_index)`, never by display minute
or scalar clock alone. The verified full match, not a filtered window, is the
input domain. Applying a later filter retains the full-match state at each row.

Inputs: original event ID, type, team/player IDs, source `shot.type` and
`shot.outcome`, explicit related IDs; preserved period/index/timestamp and
FIL-004 clocks; verified original match metadata (match/home/away IDs and final
home/away score). `possession_team` never determines the scoring team.

- Shot outcome exactly `Goal`: one goal to the acting team. Match-play penalties
  count in that score; missed/saved/off-target penalties award none. Other shot
  outcomes produce audit decisions with `scored=false`. Missing or unsupported
  shot outcome/type fails; missing is never treated as a miss.
- Own Goal For: beneficiary is that event's team. Own Goal Against: beneficiary
  is the other official team. Defender/actor identity comes from Against;
  missing players remain null. For alone does not identify a defender.
- Resolve an undirected graph of explicit related scoring-event IDs. One For
  plus one Against, opposing teams, same period and exact elapsed timestamp,
  becomes **one award**, anchored at the earlier provider index. Both original
  IDs remain in the decision. One-way explicit links are accepted. Same-time
  unlinked own-goal perspectives, self-links, conflicting teams/times, linked
  shots or more than two scoring representations fail for review. A singleton
  own-goal representation is permitted with a warning, never a fabricated pair.
  No fuzzy time matching or manual adjustment to force the official score.
- Goal Keeper `Goal Conceded` / `Penalty Conceded` records are supporting provider
  perspectives, never an additional awarded goal. They remain unchanged in
  the event state table. Unrelated normal shots at the same timestamp remain
  distinct; a timestamp is not a duplicate ID or an identity key.
- Period 5 accepts penalty shots into a separate `shootout_score`; their goals
  never change match-play score. Successful and failed attempts are preserved.
  Shootout before/after counters initialize to zero; the report is null when no
  shootout is observed. No shootout winner, kick-order validation or official
  shootout result certification is provided without separate verified metadata.
- Require complete regular/extra period coverage and a final Half End marker
  before final-score reconciliation. Timing uncertainty remains FIL-004's
  documented event-clock uncertainty; no timestamps are corrected or shifted.

Expected invariants: every input row survives exactly once; each scoring source
ID belongs to exactly one decision; each award increments only one team's one
domain exactly once; no negative scores; normal and own-goal actors are distinct
from beneficiaries where appropriate; original IDs, order, nulls and clocks
survive exactly; final match-play state equals official metadata or publication
fails with `score_reconciliation_failed`. Zero after complete verified inputs
is a count, not a substitution for missing source semantics.

## Code and local artifacts

`fil.ingestion.statsbomb_score`: original-record interpretation and metadata
selection. `fil.metrics.score`: frozen typed models and pure deterministic
reconstruction. `fil.metrics.score_artifacts`: full-chain verification, immutable
local Parquet/QA/manifest. No dependencies added; PyArrow remains 21.0.0.

`SCORE_SCHEMA` appends 12 fields to the 66-column FIL-004 table: nullable string
`score_decision_id`; eight required int32 counters
`{score,shootout}_{home,away}_{before,after}`; required string `score_version`,
`score_pipeline_git_sha`, `clock_manifest_sha256`. Original 66 values/types and
clock metadata are unchanged, with an added score-version metadata key.

`DECISION_SCHEMA` fixes 20 columns: source-ID anchor `decision_id`, ordered
`source_event_ids` (list<string>), match/period/provider index, original timestamp,
exact elapsed milliseconds, nullable chronology, display label, beneficiary,
nullable actor team/player, kind (`shot`, `penalty`, `own_goal`), boolean scored,
domain (`match_play`, `shootout`), deduplication reason, source/clock manifest
digests, score implementation SHA and version. IDs/integers use int64 and text
uses strings. Actor nulls are preserved, not attributed by guessing.

Every event links through clock manifest → canonical manifest → raw manifest →
original record at its preserved array offset. Decision IDs are original event
IDs, not new provider IDs. Both own-goal representations point to the same
anchor decision. Reverse lookup: find a decision by either source ID, then use
`fil.ingestion.normalize.lookup_event` on each original ID and verified raw and
canonical paths. This never mutates the provider records.

Default output, ignored and never redistributed:

```text
data/interim/scores/match_id=8658/<clock-manifest-sha>/fil-score-1/<implementation-sha>/
  score_events.parquet
  decisions.parquet
  quality.json
  manifest.json
```

Manifest v1 records code/spec versions, upstream manifest digests, match/row/
decision counts, UTC generation time, exact file sizes/SHA-256 and PyArrow/writer
settings (Parquet 2.6, Zstd, no dictionaries, statistics, 65,536-row groups).
QA records reconciliation, goals/penalties/pairs, source types/IDs, row exclusions,
actor nulls, clock estimates and warnings. Unrecognized non-scoring types are
retained and flagged for review; no generalization to future scoring types is
claimed. This adapter supports the reviewed fixture, not all future source schemas.

Build verifies the complete FIL-002/003/004 chain, then hashes the exact buffers
used to read source records, match metadata and clock table. It stages and
verifies outputs before atomic rename. Existing outputs are fully reverified
and reused without writes; corrupt, missing, unexpected or symlink members fail,
never silently repair. Output inside any input bundle is forbidden. Final-score
mismatch raises an error carrying `score_reconciliation_failed`; no successful
artifact/false reconciliation report is written. Fixed inputs/code on the pinned
platform reproduce identical Parquet and QA; fresh manifest creation time differs.
Caller-supplied code SHA is an audit assertion, not a cryptographic code signature.

## Offline CLI

Set `raw_bundle`, `dataset` and `clock_dataset` to the directories returned by
FIL-002/003/004. From a matching clean implementation checkout:

```bash
uv run --frozen python -m fil.metrics.score_cli build \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --clock-dataset "$clock_dataset" --pipeline-revision "$(git rev-parse HEAD)"
uv run --frozen python -m fil.metrics.score_cli verify \
  --raw-bundle "$raw_bundle" --canonical-dataset "$dataset" \
  --clock-dataset "$clock_dataset" --score-dataset "$score_dataset"
```

Set `score_dataset` to build's printed path. `--output-root` selects another
ignored local root. Failure exits 1, usage errors 2, verification success 0.
No network calls, provider data in tests/CI/packages/Git, changes to data rights,
or publication authorization. Read SOURCE_POLICY.md before acquisition/use.
Real fixture evidence and remaining independent-review/hosted limitations are
in FIL-005_VERIFICATION.md. DATA-SCORE and DEL-TIME-SCORE assessments remain
technical checks until independent validation and human approval are complete;
no later analytics gate is passed.
