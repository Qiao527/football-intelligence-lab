"""Project verified raw provider records into the scouting appearance contract.

Only fields the protocol names are read: source shot xG, shot type/outcome,
period, team/player identity, lineup positions and match date/stage. No
coordinates, no minutes, no derived roles and no inferred availability.
"""

import json
from pathlib import Path
from typing import Any

VERSION = "fil-scouting-raw-projection-1"


def _name(node: Any) -> str | None:
    return node.get("name") if isinstance(node, dict) else None


def project_event(raw: dict[str, Any], match_id: int) -> dict[str, Any]:
    """One raw provider event to the flat projection; nothing is imputed."""
    if not isinstance(raw.get("id"), str) or not isinstance(raw.get("period"), int):
        raise ValueError("Raw event lacks a usable id or period")
    event_type = _name(raw.get("type"))
    row = {
        "source": "statsbomb_open_data",
        "event_id": raw["id"],
        "match_id": match_id,
        "team_id": (raw.get("team") or {}).get("id"),
        "player_id": (raw.get("player") or {}).get("id"),
        "event_type": event_type,
        "period": raw["period"],
        "provider_index": raw.get("index"),
        "shot_xg": None,
        "shot_type": None,
        "shot_outcome": None,
    }
    if event_type == "Shot":
        shot = raw.get("shot") or {}
        row["shot_xg"] = shot.get("statsbomb_xg")
        row["shot_type"] = _name(shot.get("type"))
        row["shot_outcome"] = _name(shot.get("outcome"))
    return row


def project_lineups(raw: list[dict[str, Any]], match_id: int) -> list[dict[str, Any]]:
    """Provider position intervals per rostered player, kept verbatim."""
    rows: list[dict[str, Any]] = []
    for team in raw:
        team_id = team.get("team_id")
        for player in team.get("lineup") or []:
            rows.append(
                {
                    "match_id": match_id,
                    "team_id": team_id,
                    "player_id": player.get("player_id"),
                    "positions": player.get("positions"),
                }
            )
    return rows


def project_matches(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match date, provider stage and both team ids for the window rules."""
    rows = []
    for match in raw:
        stage = _name(match.get("competition_stage"))
        home = (match.get("home_team") or {}).get("home_team_id")
        away = (match.get("away_team") or {}).get("away_team_id")
        rows.append(
            {
                "match_id": match.get("match_id"),
                "match_date": match.get("match_date"),
                "competition_stage": stage,
                "home_team_id": home,
                "away_team_id": away,
                "home_score": match.get("home_score"),
                "away_score": match.get("away_score"),
            }
        )
    return rows


def load_corpus(root: Path, revision: str) -> dict[str, Any]:
    """Read the pinned corpus tree; the caller supplies the verified root."""
    base = Path(root) / revision
    metadata_path = base / "competition-matches.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Missing competition metadata: {metadata_path}")
    matches = project_matches(json.loads(metadata_path.read_bytes()))
    known = {m["match_id"] for m in matches}
    events: list[dict[str, Any]] = []
    lineups: list[dict[str, Any]] = []
    folders = sorted(p for p in base.iterdir() if p.is_dir())
    if not folders:
        raise ValueError("No match folders in the corpus root")
    for folder in folders:
        match_id = int(folder.name)
        if match_id not in known:
            raise ValueError(f"Match {match_id} is absent from competition metadata")
        events.extend(
            project_event(e, match_id)
            for e in json.loads((folder / f"{match_id}.json.events").read_bytes())
        )
        lineups.extend(
            project_lineups(
                json.loads((folder / f"{match_id}.json.lineups").read_bytes()), match_id
            )
        )
    return {
        "version": VERSION,
        "events": events,
        "lineups": lineups,
        "matches": matches,
        "match_count": len(folders),
        "raw_event_count": len(events),
    }
