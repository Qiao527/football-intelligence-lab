"""Pure score reconstruction over verified clocks and provider-neutral scoring signals."""

import re
from collections import Counter
from dataclasses import dataclass

import pyarrow as pa

from fil.time.clock import CLOCK_SCHEMA

SCORE_VERSION = "fil-score-1"


class ScoreError(ValueError):
    """Unresolved score semantics or failed official reconciliation; do not publish."""


@dataclass(frozen=True)
class OfficialScore:
    match_id: int
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int

    def __post_init__(self) -> None:
        for name in ("match_id", "home_team_id", "away_team_id", "home_score", "away_score"):
            value = getattr(self, name)
            if type(value) is not int or value < (0 if name.endswith("score") else 1):
                raise ScoreError(f"Invalid official {name}")
        if self.home_team_id == self.away_team_id:
            raise ScoreError("Official teams must be distinct")


@dataclass(frozen=True)
class ScoringSignal:
    event_id: str
    kind: str  # shot, own_for, own_against
    team_id: int
    player_id: int | None
    scored: bool
    penalty: bool
    related_event_ids: tuple[str, ...] = ()


_STATE_FIELDS = (
    [pa.field("score_decision_id", pa.string())]
    + [
        pa.field(f"{domain}_{team}_{when}", pa.int32(), nullable=False)
        for domain in ("score", "shootout")
        for team in ("home", "away")
        for when in ("before", "after")
    ]
    + [
        pa.field("score_version", pa.string(), nullable=False),
        pa.field("score_pipeline_git_sha", pa.string(), nullable=False),
        pa.field("clock_manifest_sha256", pa.string(), nullable=False),
    ]
)
SCORE_SCHEMA = pa.schema(
    list(CLOCK_SCHEMA) + _STATE_FIELDS,
    metadata={**CLOCK_SCHEMA.metadata, b"fil.score_version": SCORE_VERSION.encode()},
)
DECISION_SCHEMA = pa.schema(
    [
        pa.field("decision_id", pa.string(), nullable=False),
        pa.field("source_event_ids", pa.list_(pa.field("element", pa.string())), nullable=False),
        pa.field("match_id", pa.int64(), nullable=False),
        pa.field("period", pa.int64(), nullable=False),
        pa.field("provider_index", pa.int64(), nullable=False),
        pa.field("period_timestamp", pa.string(), nullable=False),
        pa.field("period_elapsed_ms", pa.int64(), nullable=False),
        pa.field("chronological_ms", pa.int64()),
        pa.field("display_clock", pa.string(), nullable=False),
        pa.field("beneficiary_team_id", pa.int64(), nullable=False),
        pa.field("actor_team_id", pa.int64()),
        pa.field("actor_player_id", pa.int64()),
        pa.field("kind", pa.string(), nullable=False),
        pa.field("scored", pa.bool_(), nullable=False),
        pa.field("domain", pa.string(), nullable=False),
        pa.field("deduplication", pa.string(), nullable=False),
        pa.field("source_manifest_sha256", pa.string(), nullable=False),
        pa.field("clock_manifest_sha256", pa.string(), nullable=False),
        pa.field("score_pipeline_git_sha", pa.string(), nullable=False),
        pa.field("score_version", pa.string(), nullable=False),
    ],
    metadata={b"fil.score_version": SCORE_VERSION.encode()},
)


def reconstruct_score(
    clock: pa.Table,
    signals: tuple[ScoringSignal, ...],
    official: OfficialScore,
    revision: str,
    clock_manifest_sha256: str,
) -> tuple[pa.Table, pa.Table, dict]:
    """Return all event states, scoring decisions and QA; fail closed on final mismatch.

    Match-play score is the cumulative count of distinct awarded goals in periods 1–4.
    Linked own-goal perspectives form one award at their earliest provider index.
    Period-5 successful penalties use a separate cumulative score, never match-play score.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or not re.fullmatch(
        r"[0-9a-f]{64}", clock_manifest_sha256
    ):
        raise ScoreError("Expected full implementation SHA and clock manifest SHA-256")
    if not clock.schema.equals(CLOCK_SCHEMA, check_metadata=True) or not clock.num_rows:
        raise ScoreError("Expected nonempty verified clock schema")
    # Reconstruct the scoring projection only; append state arrays to the original
    # Arrow columns below so wide source JSON/nullable fields never round-trip.
    rows = clock.select(
        [
            "event_id",
            "match_id",
            "period",
            "provider_index",
            "source_manifest_sha256",
            "canonical_manifest_sha256",
            "source_revision",
            "event_type",
            "team_id",
            "player_id",
            "shot_outcome",
            "shot_type",
            "period_elapsed_ms",
            "chronological_ms",
            "period_timestamp",
            "display_clock",
            "quality_flags",
            "chronological_estimated",
        ]
    ).to_pylist()
    by_id = {r["event_id"]: r for r in rows}
    if len(by_id) != len(rows) or any(not k for k in by_id):
        raise ScoreError("Duplicate or missing event IDs")
    if any(r["match_id"] != official.match_id for r in rows):
        raise ScoreError("Official/event match identity differs")
    keys = [(r["period"], r["provider_index"]) for r in rows]
    if keys != sorted(set(keys)) or any(a[1] >= b[1] for a, b in zip(keys, keys[1:], strict=False)):
        raise ScoreError("Expected unique, increasing provider order")
    for name in ("source_manifest_sha256", "canonical_manifest_sha256", "source_revision"):
        if len({r[name] for r in rows}) != 1:
            raise ScoreError("Mixed input provenance")
    teams = (official.home_team_id, official.away_team_id)
    by_signal = {s.event_id: s for s in signals}
    if len(by_signal) != len(signals):
        raise ScoreError("Duplicate scoring signal IDs")
    required = {
        r["event_id"]
        for r in rows
        if r["event_type"] in {"Shot", "Own Goal For", "Own Goal Against"}
    }
    if set(by_signal) != required:
        raise ScoreError("Missing or unexpected scoring signals")
    match_periods = {r["period"] for r in rows if r["period"] < 5}
    if match_periods not in ({1, 2}, {1, 2, 3, 4}):
        raise ScoreError("Incomplete match-play period coverage")
    if not any(r["event_type"] == "Half End" and r["period"] == max(match_periods) for r in rows):
        raise ScoreError("Final period completion marker missing")
    for s in signals:
        if s.event_id not in by_id or s.kind not in {"shot", "own_for", "own_against"}:
            raise ScoreError("Unknown event or scoring signal kind")
        r = by_id[s.event_id]
        if (
            r["event_type"]
            != {"shot": "Shot", "own_for": "Own Goal For", "own_against": "Own Goal Against"}[
                s.kind
            ]
        ):
            raise ScoreError("Scoring signal conflicts with source event type")
        if s.event_id in s.related_event_ids:
            raise ScoreError("Self-linked scoring representation")
        if type(s.team_id) is not int or s.team_id not in teams or r["team_id"] != s.team_id:
            raise ScoreError("Unknown or conflicting scoring team")
        if s.player_id != r["player_id"]:
            raise ScoreError("Conflicting scorer identity")
        if type(s.scored) is not bool or type(s.penalty) is not bool:
            raise ScoreError("Scored/penalty must be booleans")
        if s.kind == "shot" and (
            s.scored != (r["shot_outcome"] == "Goal") or s.penalty != (r["shot_type"] == "Penalty")
        ):
            raise ScoreError("Scoring signal conflicts with canonical shot semantics")
        if s.kind != "shot" and (not s.scored or s.penalty or r["period"] == 5):
            raise ScoreError("Invalid own-goal domain/flags")
        if r["period"] == 5 and not s.penalty:
            raise ScoreError("Non-penalty shootout attempt")
        if any(i not in by_id for i in s.related_event_ids):
            raise ScoreError("Unavailable related source event")
    # Undirected explicit source links, including one-way links. Time alone is never a link.
    adjacency = {s.event_id: set() for s in signals}
    for s in signals:
        for other in s.related_event_ids:
            if other in by_signal:
                adjacency[s.event_id].add(other)
                adjacency[other].add(s.event_id)
    visited: set[str] = set()
    decisions = []
    warnings = []
    own_instants: set[tuple[int, int]] = set()
    for row in rows:
        event_id = row["event_id"]
        if event_id not in by_signal or event_id in visited:
            continue
        component = {event_id}
        pending = [event_id]
        while pending:
            for other in adjacency[pending.pop()]:
                if other not in component:
                    component.add(other)
                    pending.append(other)
        group = sorted(component, key=lambda i: by_id[i]["provider_index"])
        members = [by_signal[i] for i in group]
        visited.update(group)
        first = by_id[group[0]]
        own = members[0].kind != "shot"
        if len(group) > 1:
            if len(group) != 2 or {s.kind for s in members} != {"own_for", "own_against"}:
                raise ScoreError("Ambiguous linked scoring representations")
            if len({(by_id[i]["period"], by_id[i]["period_elapsed_ms"]) for i in group}) != 1:
                raise ScoreError("Linked own goals disagree on period/time")
            if len({s.team_id for s in members}) != 2:
                raise ScoreError("Linked own goals must have opposing teams")
        if own:
            instant = (first["period"], first["period_elapsed_ms"])
            if instant in own_instants:
                raise ScoreError("Unlinked own-goal representations at same instant")
            own_instants.add(instant)
            defender = next((s for s in members if s.kind == "own_against"), None)
            credit = next((s for s in members if s.kind == "own_for"), None)
            beneficiary = credit.team_id if credit else teams[1 - teams.index(defender.team_id)]
            actor_team = defender.team_id if defender else None
            actor_player = defender.player_id if defender else None
            if len(group) == 1:
                warnings.append(f"single_own_goal_representation:{group[0]}")
            kind, scored = "own_goal", True
        else:
            s = members[0]
            beneficiary, actor_team, actor_player = s.team_id, s.team_id, s.player_id
            kind, scored = ("penalty" if s.penalty else "shot"), s.scored
        decisions.append(
            {
                "decision_id": group[0],
                "source_event_ids": group,
                **{
                    k: first[k]
                    for k in (
                        "match_id",
                        "period",
                        "provider_index",
                        "period_timestamp",
                        "period_elapsed_ms",
                        "chronological_ms",
                        "display_clock",
                        "source_manifest_sha256",
                    )
                },
                "beneficiary_team_id": beneficiary,
                "actor_team_id": actor_team,
                "actor_player_id": actor_player,
                "kind": kind,
                "scored": scored,
                "domain": "shootout" if first["period"] == 5 else "match_play",
                "deduplication": "explicit_related_pair" if len(group) == 2 else "single_record",
                "clock_manifest_sha256": clock_manifest_sha256,
                "score_pipeline_git_sha": revision,
                "score_version": SCORE_VERSION,
            }
        )
    decision_by_event = {i: d for d in decisions for i in d["source_event_ids"]}
    scores = {"score": [0, 0], "shootout": [0, 0]}
    state_rows = []
    for r in rows:
        d = decision_by_event.get(r["event_id"])
        state = {
            f"{domain}_{team}_before": scores[domain][n]
            for domain in scores
            for n, team in enumerate(("home", "away"))
        }
        if d and d["decision_id"] == r["event_id"] and d["scored"]:
            scores["shootout" if d["domain"] == "shootout" else "score"][
                teams.index(d["beneficiary_team_id"])
            ] += 1
        state.update(
            {
                f"{domain}_{team}_after": scores[domain][n]
                for domain in scores
                for n, team in enumerate(("home", "away"))
            }
        )
        state_rows.append(
            {
                **state,
                "score_decision_id": d["decision_id"] if d else None,
                "score_version": SCORE_VERSION,
                "score_pipeline_git_sha": revision,
                "clock_manifest_sha256": clock_manifest_sha256,
            }
        )
    if scores["score"] != [official.home_score, official.away_score]:
        raise ScoreError(
            f"score_reconciliation_failed: reconstructed {scores['score']}, "
            f"official {[official.home_score, official.away_score]}"
        )
    unknown = [r["event_id"] for r in rows if "unrecognized_event_type" in r["quality_flags"]]
    if unknown:
        warnings.append("unrecognized_non_scoring_events_retained; review before other fixtures")
    report = {
        "score_version": SCORE_VERSION,
        "match_id": official.match_id,
        "home_team_id": teams[0],
        "away_team_id": teams[1],
        "official_score": [official.home_score, official.away_score],
        "reconstructed_score": scores["score"],
        "shootout_score": scores["shootout"] if any(r["period"] == 5 for r in rows) else None,
        "shootout_official_reconciliation": (
            "not_performed: no separate verified shootout metadata supplied"
            if any(r["period"] == 5 for r in rows)
            else "not_applicable: no shootout observed"
        ),
        "score_reconciliation_failed": False,
        "raw_clock_rows": len(rows),
        "score_state_rows": len(state_rows),
        "excluded_state_rows": 0,
        "scoring_source_records": len(signals),
        "decision_count": len(decisions),
        "merged_own_goal_pairs": sum(
            d["deduplication"] == "explicit_related_pair" for d in decisions
        ),
        "match_play_goals": sum(d["scored"] and d["domain"] == "match_play" for d in decisions),
        "match_play_penalty_goals": sum(
            d["scored"] and d["domain"] == "match_play" and d["kind"] == "penalty"
            for d in decisions
        ),
        "own_goals": sum(d["kind"] == "own_goal" for d in decisions),
        "warnings": warnings,
        "unrecognized_event_ids": unknown,
        "source_event_type_counts": dict(sorted(Counter(r["event_type"] for r in rows).items())),
        "null_actor_player_decisions": sum(d["actor_player_id"] is None for d in decisions),
        "estimated_clock_event_count": sum(bool(r["chronological_estimated"]) for r in rows),
        "transformations": [
            "retain every clock row/field",
            "explicit own-goal pair -> one award",
            "shot outcome Goal -> one award",
            "period 5 -> separate shootout",
        ],
        "goal_event_ids": [d["source_event_ids"] for d in decisions if d["scored"]],
    }
    return (
        pa.Table.from_arrays(
            [clock[field.name] for field in CLOCK_SCHEMA]
            + [
                pa.array([r[field.name] for r in state_rows], type=field.type)
                for field in _STATE_FIELDS
            ],
            schema=SCORE_SCHEMA,
        ),
        pa.Table.from_pylist(decisions, schema=DECISION_SCHEMA),
        report,
    )
