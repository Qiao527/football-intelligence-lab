"""A self-authored scouting fixture, separate from the existing demonstration matches."""

import hashlib
import json


def scout_fixture() -> tuple[list[dict], dict, dict]:
    """Return fictional source actions, match metadata and immutable source identity."""
    # The phase labels are authored fixture annotations, not inferred player abilities.
    specs = [
        (901, 9101, "Mara Vale", "Interception", "defensive_transition", [37, 30], None),
        (901, 9101, "Mara Vale", "Pass", "build_up", [37, 30], [57, 35]),
        (901, 9102, "Ivo Moss", "Pass", "build_up", [57, 35], [76, 43]),
        (902, 9201, "Tess Rowe", "Interception", "defensive_transition", [39, 50], None),
        (902, 9201, "Tess Rowe", "Pass", "build_up", [39, 50], [60, 44]),
        (901, 9101, "Mara Vale", "Interception", "defensive_transition", [44, 25], None),
        (901, 9101, "Mara Vale", "Pass", "build_up", [44, 25], [65, 34]),
        (901, 9101, "Mara Vale", "Pass", "build_up", [50, 40], [70, 40]),
        (901, 9101, "Mara Vale", "Pass", "build_up", [32, 48], [55, 41]),
        (901, 9101, "Mara Vale", "Pass", "build_up", [48, 36], [67, 30]),
        (901, 9101, "Mara Vale", "Shot", "attack", [100, 35], None),
        (901, 9102, "Ivo Moss", "Shot", "attack", [95, 43], None),
        (902, 9201, "Tess Rowe", "Shot", "attack", [98, 38], None),
        (901, 9102, "Ivo Moss", "Pass", "build_up", [40, 33], [61, 37]),
        (902, 9201, "Tess Rowe", "Pass", "build_up", [44, 47], [61, 39]),
    ]
    teams = {901: "Linden Rovers", 902: "Orchard Athletic"}
    events = []
    for i, (team, pid, name, kind, phase, location, end) in enumerate(specs, 1):
        event = {
            "id": f"demo-scout-action-{i:03d}",
            "index": i,
            "period": 1 if i <= 8 else 2,
            "timestamp": f"00:{i * 2:02d}:00.000",
            "team": {"id": team, "name": teams[team]},
            "possession_team": {"id": team, "name": teams[team]},
            "possession": i,
            "player": {"id": pid, "name": name},
            "type": {"name": kind},
            "location": location,
            "demo_phase": phase,
        }
        if kind == "Pass":
            event["pass"] = {"end_location": end}
            if i == 10:
                event["pass"]["outcome"] = {"name": "Incomplete"}
        if kind == "Shot":
            event["shot"] = {"outcome": {"name": "Saved"}, "type": {"name": "Open Play"}}
        events.append(event)
    metadata = {
        "match_id": "demo-scout",
        "home_team": {"home_team_id": 901, "home_team_name": teams[901]},
        "away_team": {"away_team_id": 902, "away_team_name": teams[902]},
        "home_score": 0,
        "away_score": 0,
    }
    identity = {
        "mode": "synthetic",
        "source": "Self-authored fictional scouting fixture",
        "source_revision": "fil-scout-fixture-1",
        "raw_sha256": hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest(),
        "rights": "Self-authored fictional events; no provider records.",
        "coordinate_frame": (
            "Fictional native coordinates, 120 by 80; physical direction not certified."
        ),
    }
    return events, metadata, identity
