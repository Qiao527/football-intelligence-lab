"""Synthetic-only scouting tools with validated interpretation and source-linked facts.

The default interpreter is a limited rule-based baseline, not an AI model. A model
adapter returns a structured query, but its text is never used as evidence
or displayed as an explanation. No service is contacted by this module.
"""

import re
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fil.intelligence.scout_fixture import scout_fixture

INTENTS = {
    "transition_buildup", "transition", "passes", "shots", "player", "comparison", "unsupported"
}
KEYS = {"intent", "team", "player", "min_passes", "max_shots"}
TEAMS = {"Linden Rovers", "Orchard Athletic"}
PLAYERS = {"Mara Vale", "Ivo Moss", "Tess Rowe"}
LIMIT = 1000
# Unrecognized words cause abstention so that an unknown constraint is never silently dropped.
WORDS = set("""a an and are actions action all any at least minimum min most maximum max no
more than me the who which with whose have has had show find list get search look for players
player fictional recorded records record evidence events event source original supporting
contradictory opposing context their them in on from of to by one match fixture game
linden rovers orchard athletic mara vale ivo moss tess rowe passes pass passing shots shot
build up buildup defensive defense defence transitions transition interceptions interception
contribute contributing contribution even when conventional attacking statistics stats
unremarkable few low i want need looking scout scouting please candidates candidate identify
what is how many does do did as well as""".split())


def interpret(text: str) -> dict[str, Any]:
    """Interpret a deliberately bounded set of requests without claiming model use."""
    t = text.lower().strip()
    # These phrases request the counter-evidence already included in every result.
    t = re.sub(r"\bincluding (?:the )?(?:failed|incomplete) pass(?:es)?\b", "", t).strip()
    query: dict[str, Any] = {
        "intent": "unsupported",
        "team": next((v for v in TEAMS if v.lower() in t), None),
        "player": next((v for v in PLAYERS if v.lower() in t), None),
        "min_passes": None,
        "max_shots": None,
    }
    # Requests for unobservable or comparative capability cannot be rescued by a subset.
    if re.search(r"\b(rating|rate|rank|best|better|compare|comparison|versus|vs\.?|ability|"
                 r"potential|speed|pace|pressures?|pressure|salary|age|height|nationality|"
                 r"transfer|market value|per.?90|invent|fabricate|guess|predict)\b", t):
        query["intent"] = (
            "comparison" if re.search(r"\b(compare|comparison|versus|vs\.?)\b", t)
            else "unsupported"
        )
        return query
    matching_teams = [name for name in TEAMS if name.lower() in t]
    matching_players = [name for name in PLAYERS if name.lower() in t]
    if len(matching_teams) > 1 or len(matching_players) > 1:
        return query
    remaining = t
    for name in matching_teams + matching_players:
        remaining = remaining.replace(name.lower(), "")
    entity_words = {part.lower() for name in TEAMS | PLAYERS for part in name.split()}
    if entity_words.intersection(re.findall(r"[a-z]+", remaining)):
        return query
    if re.search(r"\bno\b(?!\s+more\s+than)", t):
        return query
    tokens = re.findall(r"[a-z]+|\d+", t)
    if any(token not in WORDS and not token.isdigit() for token in tokens):
        return query
    recognized_numbers = re.findall(
        r"(?:at least|minimum|min)\s+(\d+)\s+pass(?:es)?|"
        r"(?:at most|no more than|maximum|max)\s+(\d+)\s+shots?", t
    )
    numbers = re.findall(r"\b\d+\b", t)
    if sorted(numbers) != sorted(n for pair in recognized_numbers for n in pair if n):
        return query
    if re.search(r"defen[cs](?:e|ive)|transition|interception", t):
        query["intent"] = (
            "transition_buildup" if re.search(r"pass|build[ -]?up", t) else "transition"
        )
    elif re.search(r"pass|build[ -]?up", t):
        query["intent"] = "passes"
    elif re.search(r"shot", t):
        query["intent"] = "shots"
    elif query["player"] and (t == query["player"].lower() or
                              re.search(r"player|action|evidence|record|show|find", t)):
        query["intent"] = "player"
    if re.search(r"unremarkable|few shots|low shots", t):
        query["max_shots"] = 1
    for field, pattern in (
        ("min_passes", r"(?:at least|minimum|min)\s+(\d+)\s+pass(?:es)?"),
        ("max_shots", r"(?:at most|no more than|maximum|max)\s+(\d+)\s+shots?"),
    ):
        match = re.search(pattern, t)
        if match:
            query[field] = int(match.group(1))
    # A second positive event condition cannot be silently discarded.
    if (query["intent"] in {"passes", "transition", "transition_buildup"}
            and re.search(r"\bshots?\b", t) and query["max_shots"] is None):
        query["intent"] = "unsupported"
    return query


def validate_query(value: Any) -> dict[str, Any]:
    """Reject unknown fields, types and identifiers at the model/tool boundary."""
    if not isinstance(value, dict) or set(value) != KEYS:
        raise ValueError("Interpretation must contain exactly the supported query fields")
    if not isinstance(value["intent"], str) or value["intent"] not in INTENTS:
        raise ValueError("Unsupported intent")
    if value["team"] is not None and (
        not isinstance(value["team"], str) or value["team"] not in TEAMS
    ):
        raise ValueError("Unknown team")
    if value["player"] is not None and (
        not isinstance(value["player"], str) or value["player"] not in PLAYERS
    ):
        raise ValueError("Unknown player")
    for field in ("min_passes", "max_shots"):
        v = value[field]
        if v is not None and (type(v) is not int or not 0 <= v <= 100):
            raise ValueError("Invalid numeric filter")
    return dict(value)


def check_interpretation(text: str, proposed: Any) -> dict[str, Any]:
    """Independently check a narrow set of supported paraphrases and all constraints.

    Anything outside this vocabulary abstains. This cannot prove general semantic equivalence.
    """
    query = validate_query(proposed)
    canonical = text.lower()
    for pattern, replacement in (
        (r"\bfootballers?\b", "players"),
        (r"\bat least three\b", "at least 3"),
        (r"\bat most one\b", "at most 1"),
        (r"\bwithin\b", "in"),
        (r"\bdisplay\b", "show"),
        (r"\bprovide\b", "show"),
    ):
        canonical = re.sub(pattern, replacement, canonical)
    checked = validate_query(interpret(canonical))
    if checked["intent"] in {"unsupported", "comparison"}:
        return checked
    if query != checked:
        raise ValueError("Interpretation conflicts with independently checked constraints")
    return query


def search(text: str, interpreter: Callable[[str], dict] | None = None) -> dict:
    """Execute an independently checked query against authored event facts."""
    if not isinstance(text, str) or not text.strip() or len(text) > LIMIT:
        raise ValueError("A nonempty request of at most 1000 characters is required")
    error = None
    if interpreter:
        try:
            query = check_interpretation(text, interpreter(text))
        except (ValueError, OSError, TimeoutError):
            error = "Provider interpretation failed validation or was unavailable."
            query = {"intent": "unsupported", "team": None, "player": None,
                     "min_passes": None, "max_shots": None}
        mode = "provider"
    else:
        query = validate_query(interpret(text))
        mode = "rules"
    result = execute_query(query, mode)
    if error:
        result["interpretation_error"] = error
    return result


def execute_query(query: dict, mode: str = "structured") -> dict:
    """Run an explicit validated query against the synthetic fixture."""
    query = validate_query(query)
    result: dict[str, Any] = {
        "query": query,
        "interpretation_mode": mode,
        "source_mode": "synthetic",
        "candidates": [],
        "abstention": None,
        "limitations": [
            "One fictional match; counts describe authored records, not player ability.",
            "Unremarkable or few shots is operationalized as at most one recorded shot; "
            "this is a demo filter, not a population baseline.",
            "Transition and build-up are self-authored event labels, not inferred tactics.",
            "No tracking, exposure minutes, calibrated xG or independent evaluation is available.",
        ],
    }
    if query["intent"] in {"comparison", "unsupported"}:
        result["abstention"] = (
            "The fictional sample cannot support that comparison or requested attribute. "
            "Try recorded passes, shots or transition and build-up actions."
        )
        return result
    events, metadata, identity = scout_fixture()
    if identity["mode"] != "synthetic":
        raise ValueError("Only synthetic events are permitted")
    grouped: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for e in events:
        grouped[(e["team"]["id"], e["player"]["id"])].append(e)
    for (_, pid), rows in grouped.items():
        team, name = rows[0]["team"]["name"], rows[0]["player"]["name"]
        if query["team"] and team != query["team"] or query["player"] and name != query["player"]:
            continue
        passes = [e for e in rows if e["type"]["name"] == "Pass"]
        shots = [e for e in rows if e["type"]["name"] == "Shot"]
        interventions = [e for e in rows if e["demo_phase"] == "defensive_transition"]
        buildup = [e for e in passes if e["demo_phase"] == "build_up"]
        failed = [e for e in passes if e["pass"].get("outcome", {}).get("name") == "Incomplete"]
        if query["min_passes"] is not None and len(passes) < query["min_passes"]:
            continue
        if query["max_shots"] is not None and len(shots) > query["max_shots"]:
            continue
        intent = query["intent"]
        if intent == "transition_buildup" and not (interventions and buildup):
            continue
        supporting = {
            "transition_buildup": interventions + [e for e in buildup if e not in failed],
            "transition": interventions,
            "passes": [e for e in passes if e not in failed],
            "shots": shots,
            "player": rows,
        }[intent]
        if not supporting:
            continue
        supporting = sorted(supporting, key=lambda e: e["index"])
        result["candidates"].append({
            "match_id": "demo-scout", "player_id": pid, "name": name, "team": team,
            "fixture": "Linden Rovers vs Orchard Athletic",
            "counts": {"passes": len(passes), "shots": len(shots),
                       "defensive_transitions": len(interventions),
                       "build_up_passes": len(buildup)},
            "supporting_event_ids": [e["id"] for e in supporting],
            "opposing_event_ids": [e["id"] for e in failed],
            "context_event_ids": [e["id"] for e in rows],
            "explanation": f"{name} has {len(interventions)} authored defensive-transition "
                           f"interception(s), {len(buildup)} build-up pass(es), and "
                           f"{len(shots)} recorded shot(s) in this fictional fixture. "
                           "This is a source-record description, not a player rating.",
        })
    if not result["candidates"]:
        result["abstention"] = "No fictional player-match records satisfy all supported conditions."
    result["provenance"] = identity
    return result
