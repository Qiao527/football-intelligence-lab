"""Execute scouting stage A on the pinned corpus; emits a decision, not a ranking."""

import argparse
import json
from collections import Counter
from pathlib import Path

from fil.research.acquisition import REVISION
from fil.research.scouting_appearances import appearance_rows
from fil.research.scouting_raw import load_corpus
from fil.research.scouting_task import DEFAULT_THRESHOLDS, reliability_stage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/statsbomb-corpus"))
    parser.add_argument("--output", type=Path,
                        default=Path("data/interim/scouting/stage-a.json"))
    parser.add_argument("--repetitions", type=int, default=10000)
    args = parser.parse_args()

    corpus = load_corpus(args.root, REVISION)
    result = appearance_rows(corpus["events"], corpus["lineups"], corpus["matches"])
    rows = result["rows"]

    raw_shots = Counter(
        (e["match_id"], e["team_id"])
        for e in corpus["events"]
        if e["event_type"] == "Shot" and e["period"] != 5
    )
    built_shots = Counter()
    for row in rows:
        built_shots[(row["match_id"], row["team_id"])] += row["shots"]
    mismatches = {}
    for key in set(raw_shots) | set(built_shots):
        if raw_shots[key] != built_shots[key]:
            mismatches[f"{key[0]}/{key[1]}"] = {
                "raw": raw_shots[key],
                "built": built_shots[key],
            }
    if mismatches:
        raise ValueError(f"Projection dropped or duplicated shots: {mismatches}")

    report = reliability_stage(rows, DEFAULT_THRESHOLDS, repetitions=args.repetitions)
    output = {
        "corpus": {
            "matches": corpus["match_count"],
            "raw_events": corpus["raw_event_count"],
            "group_matches": sum(
                m["competition_stage"] == "Group Stage" for m in corpus["matches"]
            ),
            "revision": REVISION,
        },
        "coverage": result["coverage"],
        "unattributed_shot_ids": result["unattributed_shot_ids"],
        "stage": report,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, default=str) + "\n")
    print(json.dumps(
        {
            "corpus": output["corpus"],
            "coverage": result["coverage"],
            "n_pairs": report["n_pairs"],
            "stage": report["stage"],
            "xg": report["metrics"]["xg"],
            "goals": report["metrics"]["goals"],
            "gate": report["reliability_gate"],
            "ceiling": report["ceiling_gate"],
        },
        indent=1,
        default=str,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
