"""Matchday-3 heterogeneity diagnostic for the borrowed criterion reliability.

Groups each team's third group match by the points it had already earned in
matchdays 1-2, and reports rotation and recorded output. Descriptive only: 32
teams fall into small buckets, so no test, no p-value and no causal reading.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from fil.research.acquisition import REVISION
from fil.research.scouting_raw import load_corpus


def points_table(matches: list[dict], raw_events: dict[int, list[dict]]) -> dict:
    """Per team: chronological group fixtures, points before matchday 3, starters."""
    group = [m for m in matches if m["competition_stage"] == "Group Stage"]
    by_team: dict[int, list[dict]] = defaultdict(list)
    for match in group:
        for team in (match["home_team_id"], match["away_team_id"]):
            by_team[team].append(match)
    table: dict[int, list[dict]] = {}
    for team, fixtures in by_team.items():
        ordered = sorted(fixtures, key=lambda m: (m["match_date"], m["match_id"]))
        if len(ordered) != 3:
            raise ValueError(f"Team {team} does not have three group fixtures")
        rows = []
        for match in ordered:
            home = match["home_team_id"] == team
            scored = match["home_score"] if home else match["away_score"]
            conceded = match["away_score"] if home else match["home_score"]
            rows.append(
                {
                    "match_id": match["match_id"],
                    "match_date": match["match_date"],
                    "scored": scored,
                    "conceded": conceded,
                    "starters": starters_of(raw_events[match["match_id"]], team),
                }
            )
        table[team] = rows
    return table


def starters_of(events: list[dict], team_id: int) -> set[int]:
    for event in events:
        if event["type"]["name"] == "Starting XI" and event.get("team", {}).get("id") == team_id:
            return {
                item["player"]["id"] for item in event["tactics"]["lineup"]
            }
    raise ValueError(f"No Starting XI record for team {team_id}")


def points(rows: list[dict]) -> int:
    return sum(3 if r["scored"] > r["conceded"] else 1 if r["scored"] == r["conceded"] else 0
               for r in rows)


def bucket(value: int) -> str:
    return "0-1" if value <= 1 else "2-3" if value <= 3 else "4-6"


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def summarise(rows: list[dict]) -> dict:
    return {
        "teams": len(rows),
        "median_starters_retained_md1_md2": median(
            [r["starters_retained_md1_md2"] for r in rows]
        ),
        "median_starters_retained_md2_md3": median(
            [r["starters_retained_md2_md3"] for r in rows]
        ),
        "median_appearances": median([r["appearances"] for r in rows]),
        "median_shots": median([r["shots"] for r in rows]),
        "median_xg": median([r["xg"] for r in rows]),
        "median_xg_per_appearance": median(
            [r["xg"] / r["appearances"] for r in rows if r["appearances"]]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/statsbomb-corpus"))
    parser.add_argument("--output", type=Path,
                        default=Path("data/interim/scouting/md3-check.json"))
    args = parser.parse_args()

    raw_events = {}
    base = args.root / REVISION
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        raw_events[int(folder.name)] = json.loads(
            (folder / f"{folder.name}.json.events").read_bytes()
        )
    corpus = load_corpus(args.root, REVISION)
    table = points_table(corpus["matches"], raw_events)

    appearances: dict[tuple, int] = defaultdict(int)
    shots: dict[tuple, int] = defaultdict(int)
    xg: dict[tuple, float] = defaultdict(float)
    seen: set[tuple] = set()
    for event in corpus["events"]:
        if event["period"] == 5 or event["player_id"] is None:
            continue
        key = (event["match_id"], event["team_id"])
        marker = (event["match_id"], event["team_id"], event["player_id"])
        if marker not in seen:
            seen.add(marker)
            appearances[key] += 1
        if event["event_type"] == "Shot":
            shots[key] += 1
            xg[key] += float(event["shot_xg"])

    rows = []
    for team, fixtures in table.items():
        matchday3 = fixtures[2]
        key = (matchday3["match_id"], team)
        before = points(fixtures[:2])
        rows.append(
            {
                "team_id": team,
                "points_before_md3": before,
                "bucket": bucket(before),
                "starters_retained_md1_md2": len(
                    fixtures[1]["starters"] & fixtures[0]["starters"]
                ),
                "starters_retained_md2_md3": len(
                    matchday3["starters"] & fixtures[1]["starters"]
                ),
                "appearances": appearances.get(key, 0),
                "shots": shots.get(key, 0),
                "xg": xg.get(key, 0.0),
            }
        )

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["bucket"]].append(row)
    result = {
        "revision": REVISION,
        "teams": len(rows),
        "buckets": {name: summarise(grouped[name]) for name in ("0-1", "2-3", "4-6")},
        "overall": summarise(rows),
        "rows": sorted(rows, key=lambda r: (r["bucket"], r["team_id"])),
        "limits": (
            "descriptive diagnostic only; 32 teams, no test, no p-value; points are "
            "provider match-play scores and not qualification or tiebreakers"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(
        {k: result[k] for k in ("teams", "buckets", "overall")}, indent=1
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
