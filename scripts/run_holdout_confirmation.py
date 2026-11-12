"""One-shot confirmatory run on the held-out league, using the frozen analysis.

No knob may be changed here: arms, prior, criterion, seed and thresholds are the
constants imported from the analysis modules. The only arguments are paths.
"""

import argparse
import json
from pathlib import Path

from fil.research.league_increment import DEFAULT_SETTINGS, run
from fil.research.league_scouting import (
    DEFAULT_THRESHOLDS,
    build_rows,
    included_players,
    stage_a,
    team_windows,
)
from fil.research.scouting_raw import project_event, project_lineups, project_matches

REVISION = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
LEAGUE = (7, 27, "Ligue 1")
SEED = 1729
REPETITIONS = 10000


def verdict(interval: list[float]) -> str:
    if interval[0] > 0:
        return "replicated"
    if interval[1] < 0:
        return "reversed"
    return "inconclusive"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path,
                        default=Path("data/raw/statsbomb-league-holdout"))
    parser.add_argument("--output", type=Path,
                        default=Path("data/interim/scouting/holdout-confirmation.json"))
    parser.add_argument("--implementation", default="")
    args = parser.parse_args()

    competition, season, name = LEAGUE
    base = args.root / REVISION
    meta = project_matches(
        json.loads((base / "meta" / f"{competition}-{season}.json").read_bytes())
    )
    windows = team_windows(meta)
    rows = []
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
    stage = stage_a(rows, DEFAULT_THRESHOLDS, seed=SEED, repetitions=REPETITIONS)
    increment = run(rows, players, DEFAULT_SETTINGS, seed=SEED, repetitions=REPETITIONS)
    primary = increment["intervals"]["c1_minus_c0"]
    output = {
        "league": name,
        "revision": REVISION,
        "implementation_sha": args.implementation,
        "matches": len(meta),
        "appearances": len(rows),
        "stage_a": stage,
        "increment": increment,
        "verdict": {
            "reliability_gate": stage["reliability_gate"]["passed"],
            "ceiling_gate": stage["ceiling_gate"]["passed"],
            "primary_delta": increment["deltas"]["c1_minus_c0"],
            "primary_interval": primary,
            "replication": verdict(primary),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, default=str) + "\n")
    print(json.dumps({
        "league": name,
        "matches": output["matches"],
        "players": stage["universe"]["players"],
        "stage": stage["stage"],
        "ceiling": stage["ceiling_gate"]["ceiling"],
        "rank_correlation": increment["rank_correlation"],
        "delta_c1_c0": increment["deltas"]["c1_minus_c0"],
        "interval": primary,
        "verdict": output["verdict"]["replication"],
    }, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
