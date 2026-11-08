"""Compare source interval fields; equality does not prove interval semantics."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def compare_players(players: list[dict]) -> Counter:
    counts: Counter = Counter()
    for player in players:
        info = player.get("playing_time") or {}
        sequences, periods = info.get("sequences"), info.get("by_period")
        if not isinstance(sequences, list):
            counts["players_without_sequences"] += 1
            continue
        counts["players_with_sequences"] += 1
        if not isinstance(periods, list):
            counts["players_without_by_period"] += 1
            continue
        try:
            seq = [(s["period"], s["start_frame"], s["end_frame"]) for s in sequences]
            per = [(p["name"], p["start_frame"], p["end_frame"]) for p in periods]
        except (KeyError, TypeError):
            counts["malformed_players"] += 1
            continue
        counts["sequences"] += len(seq)
        counts["sequence_exact_match"] += sum(x in per for x in seq)
        counts["period_rows"] += len(per)
        counts["period_exact_match"] += sum(x in seq for x in per)
        if len({x[0] for x in seq}) != len(seq) or len({x[0] for x in per}) != len(per):
            counts["duplicate_period_players"] += 1
        counts["same_period_sets" if sorted(seq) == sorted(per) else "different_period_sets"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("interim_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    totals: Counter = Counter()
    matches, excluded = [], []
    for path in sorted(args.interim_root.glob("*/source-manifest.json")):
        mid = path.parent.name
        if not mid.isdecimal():
            continue
        manifest = json.loads(path.read_text())
        qc = json.loads((path.parent / "source-quality.json").read_text())
        if (
            qc["status"] != "WARN"
            or str(qc["match_id"]) != mid
            or str(manifest["match_id"]) != mid
            or qc["source_revision"] != manifest["source_revision"]
        ):
            excluded.append(mid)
            continue
        name = f"{mid}_match.json"
        expected = next(r["sha256"] for r in manifest["files"] if r["name"] == name)
        source = args.raw_root / mid / name
        with source.open("rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() != expected:
                raise ValueError(f"Source metadata hash mismatch: {mid}")
        meta = json.loads(source.read_text())
        if str(meta["id"]) != mid:
            raise ValueError(f"Source metadata match mismatch: {mid}")
        counts = compare_players(meta["players"])
        totals.update(counts)
        matches.append({"match_id": mid, "sha256": expected, "counts": dict(counts)})
    result = {
        "status": "WARN",
        "interpretation": "Equality in this sample does not establish "
        "provider semantics or validate substitution gaps; by_period remains uncertified.",
        "totals": dict(totals),
        "matches": matches,
        "excluded": excluded,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"totals": dict(totals), "matches": len(matches), "excluded": excluded}))


if __name__ == "__main__":
    main()
