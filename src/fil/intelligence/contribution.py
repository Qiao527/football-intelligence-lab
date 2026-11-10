"""Evidence-first contribution hypotheses from the self-authored scouting fixture."""

from fil.intelligence.scout import search
from fil.intelligence.scout_fixture import scout_fixture


def contribution_report() -> dict:
    """Return auditable, unranked candidates; absence of an event is not absence of impact."""
    events, meta, provenance = scout_fixture()
    answer = search("Find players contributing to defensive transitions and build-up")
    eligible = {(c["team"], c["player_id"]) for c in answer["candidates"]}
    groups: dict[tuple[int, int], list[dict]] = {}
    for event in events:
        key = (event["team"]["id"], event["player"]["id"])
        groups.setdefault(key, []).append(event)
    profiles, candidates = [], []
    for rows in groups.values():
        transition = [e for e in rows if e["demo_phase"] == "defensive_transition"]
        buildup = [e for e in rows if e["demo_phase"] == "build_up"
                   and e["type"]["name"] == "Pass" and not e["pass"].get("outcome")]
        failed = [e for e in rows if e["type"]["name"] == "Pass"
                  and e["pass"].get("outcome", {}).get("name") == "Incomplete"]
        shots = [e for e in rows if e["type"]["name"] == "Shot"]
        goals = [e for e in shots if e["shot"]["outcome"]["name"] == "Goal"]

        def fact(items: list[dict]) -> dict:
            return {"count": len(items), "event_ids": [e["id"] for e in items]}

        observations = []
        for label, items in (("defensive_transition", transition), ("completed_build_up", buildup)):
            episodes = {(e["period"], e["possession"]) for e in items}
            if len(episodes) >= 2:
                observations.append({
                    "type": label, "distinct_recorded_possessions": len(episodes),
                    "event_ids": [e["id"] for e in items],
                    "scope": "Repeated records in this sample; opportunities and independence "
                             "are unknown, so no stable tactical pattern is established.",
                })
        profile = {
            "player_id": rows[0]["player"]["id"], "name": rows[0]["player"]["name"],
            "team": rows[0]["team"]["name"], "match_id": "demo-scout",
            "transition_actions": fact(transition), "completed_build_up_passes": fact(buildup),
            "incomplete_passes": fact(failed), "recorded_shots": fact(shots),
            "recorded_goals": fact(goals), "assists": None,
            "attacking_off_ball": None, "defending_off_ball": None,
            "other_defensive_actions": None, "observations": observations,
            "context_event_ids": [e["id"] for e in rows],
        }
        profiles.append(profile)
        if (profile["team"], profile["player_id"]) in eligible and buildup:
            candidates.append(profile)
    return {
        "version": "synthetic-contribution-1",
        "fixture": {"home": meta["home_team"]["home_team_name"],
                    "away": meta["away_team"]["away_team_name"],
                    "score": [meta["home_score"], meta["away_score"]]},
        "source": provenance,
        "candidates": candidates,
        "player_profiles": profiles,
        "definitions": {
            "domain": "Self-authored fictional event sample from one match; not full tracking.",
            "selection": "At least one authored defensive-transition action and completed "
                         "build-up pass; unranked and not a player-ability score.",
            "transition_actions": "All source actions explicitly labelled defensive_transition.",
            "completed_build_up_passes": "Passes labelled build_up with no incomplete outcome; "
                                         "synthetic fixture convention.",
            "incomplete_passes": "Passes with explicit Incomplete outcome, including build-up.",
            "recorded_goals": "Source Shot events with Goal outcome in this event sample only.",
            "recorded_shots": "All recorded source Shot events for the player in this sample.",
            "observations": "Two or more source actions in distinct (period, possession) pairs; "
                            "no opportunity denominator or generalization is assumed.",
            "off_ball": "Unavailable: no tracking or verified off-ball event data.",
            "other_defensive_actions": "Unavailable: the sample does not establish "
                                       "coverage of defensive actions outside transitions.",
            "assists": "Unavailable: the fixture does not record an assist field.",
        },
        "limitations": [
            "The fictional fixture is 0–0; it cannot support a claim about helping a team win.",
            "Actions and phase labels are authored demonstrations, not tracking or causal proof.",
            "No minutes, positions, opponent context, off-ball runs or calibrated value "
            "are recorded.",
            "A missing or incomplete action is counter-evidence, not proof of low ability.",
            "Different roles, exposure, match state and opponent choices could explain counts; "
            "none can be ruled out from this sample.",
        ],
    }


def validate_selection(report: dict, selection: object) -> list[dict]:
    """Allow only source-backed candidate/action IDs; require contradictory actions."""
    if not isinstance(selection, dict) or set(selection) != {"candidates"}:
        raise ValueError("Expected a candidate selection")
    chosen = selection["candidates"]
    if not isinstance(chosen, list) or len(chosen) > len(report["player_profiles"]):
        raise ValueError("Invalid candidate list")
    players = {c["player_id"]: c for c in report["player_profiles"]}
    result = []
    seen = set()
    for item in chosen:
        if not isinstance(item, dict) or set(item) != {
            "player_id", "support_event_ids", "opposing_event_ids"
        }:
            raise ValueError("Invalid selection fields")
        pid = item["player_id"]
        support, opposing = item["support_event_ids"], item["opposing_event_ids"]
        if type(pid) is not int or pid not in players or pid in seen:
            raise ValueError("Unknown or repeated player")
        if not isinstance(support, list) or not isinstance(opposing, list):
            raise ValueError("Expected event ID lists")
        if not all(isinstance(e, str) for e in support + opposing):
            raise ValueError("Invalid event ID type")
        player = players[pid]
        transition = set(player["transition_actions"]["event_ids"])
        buildup = set(player["completed_build_up_passes"]["event_ids"])
        counter = set(player["incomplete_passes"]["event_ids"])
        if (len(support) != len(set(support)) or len(opposing) != len(set(opposing))
                or not set(support) <= transition | buildup or not support
                or (transition and not set(support) & transition)
                or (buildup and not set(support) & buildup) or set(opposing) != counter):
            raise ValueError("Unsupported or incomplete evidence selection")
        seen.add(pid)
        result.append({
            "player": player, "support_event_ids": support, "opposing_event_ids": opposing,
            "observation": (
                f"{player['name']}在虚构样本中有{len(transition)}次标注为防守转换的动作，"
                f"以及{len(buildup)}次完成的组织传球，值得结合原始事件复核。"
            ),
            "counterpoint": (
                f"样本中记录了{len(counter)}次未完成传球；未记录的动作和无球影响无法判断。"
            ),
            "scope": "这是一场虚构比赛的候选假设，不能证明球员能力或导致球队获胜。",
        })
    return result
