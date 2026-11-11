"""Run the league increment test on the frozen development set.

Rankings use window A only; the criterion is window-B xG per appearance. No player
label or shortlist is written, and the held-out league is not touched.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from fil.research.league_increment import DEFAULT_SETTINGS, run
from fil.research.league_scouting import (
    DEFAULT_THRESHOLDS,
    build_rows,
    included_players,
    team_windows,
)
from fil.research.scouting_raw import project_event, project_lineups, project_matches

REVISION = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
LEAGUES = ((2, 27, "Premier League"), (11, 27, "La Liga"), (12, 27, "Serie A"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/statsbomb-league"))
    parser.add_argument("--output", type=Path,
                        default=Path("data/interim/scouting/league-increment.json"))
    parser.add_argument("--repetitions", type=int, default=10000)
    args = parser.parse_args()

    base = args.root / REVISION
    rows = []
    for competition, season, name in LEAGUES:
        meta = project_matches(
            json.loads((base / "meta" / f"{competition}-{season}.json").read_bytes())
        )
        windows = team_windows(meta)
        for match in meta:
            match_id = match["match_id"]
            folder = base / str(match_id)
            events = [project_event(e, match_id)
                      for e in json.loads((folder / f"{match_id}.json.events").read_bytes())]
            lineups = project_lineups(
                json.loads((folder / f"{match_id}.json.lineups").read_bytes()), match_id
            )
            rows.extend(build_rows(events, lineups, windows, league=name))

    players = included_players(rows, DEFAULT_THRESHOLDS)["players"]
    report = run(rows, players, DEFAULT_SETTINGS, repetitions=args.repetitions)

    by_league: dict[str, list] = defaultdict(list)
    for row in rows:
        key = (row["player_id"], row["team_id"])
        if key in set(players):
            by_league[row["league"]].append(row)
    per_league = {}
    for league, league_rows in by_league.items():
        league_players = sorted({(r["player_id"], r["team_id"]) for r in league_rows})
        script = run(league_rows, league_players, DEFAULT_SETTINGS, repetitions=200)
        per_league[league] = {
            "players": script["players"],
            "rank_correlation": script["rank_correlation"],
            "delta_c1_c0": script["deltas"]["c1_minus_c0"],
        }

    output = {"per_league": per_league, "stage_a_settings": DEFAULT_THRESHOLDS,
              "increment": report}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, default=str) + "\n")
    print(json.dumps({
        "players": report["players"],
        "rank_correlation": report["rank_correlation"],
        "deltas": report["deltas"],
        "intervals": report["intervals"],
        "labels": {k: v["label"] for k, v in report["labels"].items()},
        "top_overlap": report["top_overlap"],
        "per_league": {k: {kk: v[kk] for kk in ("players", "delta_c1_c0")}
                       for k, v in per_league.items()},
    }, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
