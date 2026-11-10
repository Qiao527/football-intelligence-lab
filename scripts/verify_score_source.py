"""Independent offline fixture check from original records, without calling score reconstruction.

Usage: uv run --frozen python scripts/verify_score_source.py RAW CANONICAL CLOCK SCORE
Requires the locally licensed/verified match bundle; never fetches or edits provider data.
"""

import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

from fil.ingestion.statsbomb import verify_bundle
from fil.time.clock import CLOCK_SCHEMA


def verify(raw: Path, canonical: Path, clock: Path, score: Path) -> dict:
    source = verify_bundle(raw)
    identity = source["quality"]["identity"]
    match_id = identity["match_id"]
    original = json.loads((raw / f"data/events/{match_id}.json").read_bytes())
    matches = json.loads(
        (
            raw / (f"data/matches/{identity['competition_id']}/{identity['season_id']}.json")
        ).read_bytes()
    )
    metadata = next(m for m in matches if m["match_id"] == match_id)
    teams = (metadata["home_team"]["home_team_id"], metadata["away_team"]["away_team_id"])
    official = [metadata["home_score"], metadata["away_score"]]
    by_id = {e["id"]: e for e in original}
    assert len(by_id) == len(original), "Duplicate original IDs"
    awarded: dict[str, tuple[int, str, list[str], int | None]] = {}
    counted: set[str] = set()
    penalties = 0
    own_goals = 0
    for e in original:
        if e["id"] in counted:
            continue
        kind = e["type"]["name"]
        if kind == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            awarded[e["id"]] = (
                e["team"]["id"],
                "shootout" if e["period"] == 5 else "score",
                [e["id"]],
                e.get("player", {}).get("id"),
            )
            penalties += e["period"] < 5 and e["shot"]["type"]["name"] == "Penalty"
        elif kind in {"Own Goal For", "Own Goal Against"}:
            # Independent two-record rule: inspect the original reciprocal partner directly.
            opposite = "Own Goal Against" if kind == "Own Goal For" else "Own Goal For"
            partners = [
                by_id[i]
                for i in e.get("related_events", [])
                if by_id[i]["type"]["name"] == opposite
            ]
            assert len(partners) <= 1, "Ambiguous own goal"
            pair = sorted([e, *partners], key=lambda x: x["index"])
            assert pair[0]["id"] == e["id"]
            if partners:
                other = partners[0]
                assert e["id"] in other["related_events"]
                assert e["period"] == other["period"] and e["timestamp"] == other["timestamp"]
                assert e["team"]["id"] != other["team"]["id"]
            defender = next((x for x in pair if x["type"]["name"] == "Own Goal Against"), None)
            credit = next((x for x in pair if x["type"]["name"] == "Own Goal For"), None)
            beneficiary = (
                credit["team"]["id"]
                if credit
                else next(t for t in teams if t != defender["team"]["id"])
            )
            ids = [x["id"] for x in pair]
            awarded[e["id"]] = (
                beneficiary,
                "score",
                ids,
                defender.get("player", {}).get("id") if defender else None,
            )
            counted.update(ids)
            own_goals += 1
    states = pq.ParquetFile(score / "score_events.parquet").read()
    clock_table = pq.ParquetFile(clock / "clock_events.parquet").read()
    assert (
        states.select(CLOCK_SCHEMA.names)
        .replace_schema_metadata(CLOCK_SCHEMA.metadata)
        .equals(clock_table, check_metadata=True)
    ), "Clock/canonical fields changed"
    canonical_table = pq.ParquetFile(canonical / "events.parquet").read()
    assert (
        clock_table.select(canonical_table.column_names)
        .replace_schema_metadata(canonical_table.schema.metadata)
        .equals(canonical_table, check_metadata=True)
    )
    assert states.num_rows == len(original)
    ledger = pq.ParquetFile(score / "decisions.parquet").read().to_pylist()
    goals = {d["decision_id"]: d for d in ledger if d["scored"]}
    assert set(goals) == set(awarded)
    counters = {"score": [0, 0], "shootout": [0, 0]}
    for e, row in zip(original, states.to_pylist(), strict=True):
        assert row["event_id"] == e["id"] and row["provider_index"] == e["index"]
        assert row["period"] == e["period"] and row["period_timestamp"] == e["timestamp"]
        assert json.loads(row["source_record_json"]) == e
        for domain in counters:
            assert [row[f"{domain}_{t}_before"] for t in ("home", "away")] == counters[domain]
        if e["id"] in awarded:
            team, domain, ids, player = awarded[e["id"]]
            counters[domain][teams.index(team)] += 1
            decision = goals[e["id"]]
            assert decision["source_event_ids"] == ids
            assert decision["beneficiary_team_id"] == team and decision["actor_player_id"] == player
            for original_id in ids:
                assert by_id[original_id]["id"] == original_id
        for domain in counters:
            assert [row[f"{domain}_{t}_after"] for t in ("home", "away")] == counters[domain]
    assert counters["score"] == official, "Official final-score reconciliation failed"
    return {
        "match_id": match_id,
        "verified_event_states": len(original),
        "official_score": official,
        "independently_reconstructed_score": counters["score"],
        "match_play_goal_awards": sum(v[1] == "score" for v in awarded.values()),
        "own_goal_awards": own_goals,
        "match_play_penalty_goals": penalties,
        "clock_manifest_sha256": hashlib.sha256((clock / "manifest.json").read_bytes()).hexdigest(),
        "score_manifest_sha256": hashlib.sha256((score / "manifest.json").read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("Expected RAW CANONICAL CLOCK SCORE paths")
    print(json.dumps(verify(*(Path(p) for p in sys.argv[1:])), indent=2))
