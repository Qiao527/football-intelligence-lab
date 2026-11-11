"""Execute league stage A on the frozen development set; emits a decision only."""

import argparse
import json
from pathlib import Path

from fil.research.league_scouting import (
    DEFAULT_THRESHOLDS,
    build_rows,
    included_players,
    stable_position_players,
    stage_a,
    team_windows,
)
from fil.research.scouting_raw import project_event, project_lineups, project_matches

REVISION = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
LEAGUES = ((2, 27, "Premier League"), (11, 27, "La Liga"), (12, 27, "Serie A"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/statsbomb-league"))
    parser.add_argument("--output", type=Path,
                        default=Path("data/interim/scouting/league-stage-a.json"))
    parser.add_argument("--repetitions", type=int, default=10000)
    parser.add_argument("--drop-tail", type=int, default=0,
                        help="End-of-season sensitivity: drop each team's last fixtures")
    parser.add_argument("--unchanged-only", action="store_true",
                        help="Sensitivity: players whose modal position is stable")
    args = parser.parse_args()

    base = args.root / REVISION
    rows = []
    coverage = {}
    for competition, season, name in LEAGUES:
        meta = project_matches(
            json.loads((base / "meta" / f"{competition}-{season}.json").read_bytes())
        )
        windows = team_windows(meta, drop_tail=args.drop_tail)
        ids = [m["match_id"] for m in meta]
        league_rows = []
        for match_id in ids:
            folder = base / str(match_id)
            events = [project_event(e, match_id)
                      for e in json.loads((folder / f"{match_id}.json.events").read_bytes())]
            lineups = project_lineups(
                json.loads((folder / f"{match_id}.json.lineups").read_bytes()), match_id
            )
            league_rows.extend(build_rows(events, lineups, windows))
        coverage[name] = {"matches": len(ids), "appearances": len(league_rows)}
        rows.extend(league_rows)

    restrict = None
    if args.unchanged_only:
        restrict = stable_position_players(rows, included_players(rows)["players"])
    report = stage_a(rows, DEFAULT_THRESHOLDS, repetitions=args.repetitions, restrict=restrict)
    output = {
        "coverage": coverage,
        "appearances": len(rows),
        "variant": {"drop_tail": args.drop_tail, "unchanged_only": args.unchanged_only},
        "stage": report,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, default=str) + "\n")
    print(json.dumps({
        "coverage": coverage,
        "appearances": len(rows),
        "universe": report["universe"],
        "median_appearances": [report.get("median_appearances_a"),
                               report.get("median_appearances_b")],
        "metrics": report["metrics"],
        "r_obs": report.get("r_obs"),
        "r_crit": report.get("r_crit"),
        "ceiling": report["ceiling_gate"],
        "gate": report["reliability_gate"],
        "position_change_fraction": report.get("position_change_fraction"),
        "stage": report["stage"],
    }, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
