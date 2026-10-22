"""Predeclared illustrative Pogba case: observed buildup beyond final-pass links.

No player selection by the metric, ability ranking, calibrated action value or
hidden-connector claim. Shot follow-up is context within a native ID, not causation.
"""

import math
from collections import defaultdict

import pyarrow as pa

from fil.ingestion.statsbomb_tactics import extract_tactics
from fil.metrics.players import player_facts
from fil.possessions.extract import reconstruct

VERSION = "fil-research-case-1"


def investigate(events: pa.Table, meta: dict, roster: list[dict], player_id: int = 20004) -> dict:
    home, away = meta["home_team_id"], meta["away_team_id"]
    possessions = reconstruct(events, home, away)
    tactics = extract_tactics(events, home, away)
    players = player_facts(events, events, possessions, tactics, roster)
    candidates = [r for r in players.players.to_pylist() if r["player_id"] == player_id]
    if len(candidates) != 1:
        raise ValueError(
            "Predeclared player unavailable/ambiguous; never choose a winning substitute"
        )
    player = candidates[0]
    original = {r["event_id"]: r for r in events.to_pylist()}
    owned = {r["event_id"]: r for r in possessions.actions.to_pylist() if r["is_owner_action"]}
    shots = defaultdict(list)
    for r in original.values():
        if r["event_type"] == "Shot" and r["event_id"] in owned:
            shots[r["possession_id"], r["team_id"], r["period"]].append(r)
    moves = []
    side = "home" if player["team_id"] == home else "away"
    other_side = "away" if side == "home" else "home"
    for r in tactics.actions.to_pylist():
        if r["event_id"] not in owned or r["status"] not in ("completed", "observed_carry"):
            continue
        if r["team_id"] != player["team_id"]:
            continue
        e = original[r["event_id"]]
        later = [
            s["event_id"]
            for s in shots[e["possession_id"], e["team_id"], e["period"]]
            if s["provider_index"] > e["provider_index"]
        ]
        moves.append(
            dict(
                event_id=r["event_id"],
                player_id=r["player_id"],
                team_id=r["team_id"],
                period=r["period"],
                provider_index=r["provider_index"],
                display_clock=e["display_clock"],
                possession_id=e["possession_id"],
                event_type=r["event_type"],
                delta_x=r["end_x"] - r["x"]
                if all(v is not None for v in (r["x"], r["end_x"]))
                else None,
                distance_gain=r["distance_gain"],
                later_shot_ids=later,
                score_state="leading"
                if e[f"score_{side}_before"] > e[f"score_{other_side}_before"]
                else "trailing"
                if e[f"score_{side}_before"] < e[f"score_{other_side}_before"]
                else "level",
            )
        )

    def summary(rows):
        definitions = {
            "all_completed_moves": lambda r: True,
            "positive_native_dx": lambda r: r["delta_x"] is not None and r["delta_x"] > 0,
        }
        for threshold in (5, 10, 15):
            definitions[f"progression_gain_{threshold}"] = lambda r, t=threshold: (
                r["delta_x"] is not None
                and r["delta_x"] > 0
                and r["distance_gain"] is not None
                and r["distance_gain"] >= t
            )
        result = {}
        for name, rule in definitions.items():
            chosen = [r for r in rows if rule(r)]
            hits = [r for r in chosen if r["later_shot_ids"]]
            result[name] = dict(
                n=len(chosen),
                event_ids=[r["event_id"] for r in chosen],
                shot_followed_n=len(hits),
                shot_followed_ids=[r["event_id"] for r in hits],
                shot_followed_fraction=len(hits) / len(chosen) if chosen else None,
            )
        return result

    own = [r for r in moves if r["player_id"] == player_id]
    phase = {
        str(p): summary([r for r in own if r["period"] == p])
        for p in sorted({r["period"] for r in own})
    }
    states = {
        s: summary([r for r in own if r["score_state"] == s])
        for s in ("level", "leading", "trailing")
    }
    ten = summary(own)["progression_gain_10"]["event_ids"]
    positive = summary(own)["positive_native_dx"]["event_ids"]
    own_shots = [
        r
        for r in original.values()
        if r["event_type"] == "Shot"
        and r["player_id"] == player_id
        and r["team_id"] == player["team_id"]
        and r["period"] in (1, 2, 3, 4)
    ]
    return dict(
        conventional=dict(
            shot_events=len(own_shots),
            shot_goals=sum(r["shot_outcome"] == "Goal" for r in own_shots),
            source_shot_xg=math.fsum(r["shot_xg"] for r in own_shots),
            shot_event_ids=[r["event_id"] for r in own_shots],
        ),
        version=VERSION,
        status="inconclusive",
        scientifically_validated=False,
        question=(
            "Does native progression identify shot-followed recorded buildup "
            "beyond completed-move volume for the nominated player?"
        ),
        selection=(
            f"Provider player {player_id}, selected for an illustrative audit, "
            "not a preregistered discovery or population screen"
        ),
        player=player,
        player_moves=own,
        player_baselines=summary(own),
        shot_context_moves_excluded_by_gain10=[
            r["event_id"] for r in own if r["later_shot_ids"] and r["event_id"] not in ten
        ],
        gain10_moves_without_later_shot=[
            r["event_id"] for r in own if not r["later_shot_ids"] and r["event_id"] in ten
        ],
        team_baselines=summary(moves),
        period_comparison=phase,
        pre_event_state_comparison=states,
        distinct_progression_vs_forwardness_ids=sorted(set(positive) - set(ten)),
        source_xg=math.fsum(
            r["shot_xg"]
            for r in original.values()
            if r["event_type"] == "Shot" and r["period"] in (1, 2, 3, 4)
        ),
        evaluation_status=(
            "No independent match holdout or football review; descriptive comparisons only"
        ),
        uncertainty=(
            "One match; period/state strata share players and team. No event "
            "bootstrap, no cross-match interval."
        ),
        competing_explanations=[
            "role and assigned passing tasks",
            "unequal event opportunities",
            "France score state/opponent response",
            "restarts and native possession segmentation",
            "off-ball actions unobserved",
            "fixed native-frame threshold choice",
        ],
        decision_use=(
            "Retrieve exact buildup action/shot IDs for analyst review beyond the "
            "final-pass list; no recruitment or player-quality decision"
        ),
        model_readiness={
            "xT": (
                "blocked: approved multi-match training/holdout and action-frame validation absent"
            ),
            "VAEP": "blocked: approved training/validation/test and rare-goal calibration absent",
        },
    )
