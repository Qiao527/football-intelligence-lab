"""Verified native lineup metadata; no inferred minutes or playing role."""

import hashlib
import json
from pathlib import Path

from fil.ingestion.statsbomb import verify_bundle


def load_roster(raw: Path, match_id: int, manifest_sha: str) -> list[dict]:
    manifest = verify_bundle(raw)
    if hashlib.sha256((raw / "manifest.json").read_bytes()).hexdigest() != manifest_sha:
        raise ValueError("Roster/source manifest mismatch")
    name = f"data/lineups/{match_id}.json"
    entry = next(e for e in manifest["files"] if e["path"] == name)
    body = (raw / name).read_bytes()
    if hashlib.sha256(body).hexdigest() != entry["sha256"]:
        raise ValueError("Roster changed during read")
    output = []
    for team in json.loads(body):
        for player in team["lineup"]:
            output.append(
                {
                    "team_id": team["team_id"],
                    "player_id": player["player_id"],
                    "player_name": player["player_name"],
                    "positions": player.get("positions"),
                    "source_pointer": f"{name}#team={team['team_id']}/player={player['player_id']}",
                }
            )
    return output
