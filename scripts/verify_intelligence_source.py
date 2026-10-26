"""Independently reconcile Match Intelligence against authorized original JSON.

No acquisition, modeling or publication. Detailed results remain local/ignored.
The verifier uses Fraction arithmetic and separate grouping/score logic.
"""

import argparse
import copy
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from time import perf_counter

from fil.intelligence.engine import analyze
from fil.intelligence.sources import catalog, load


def verify(raw: list[dict], meta: dict, report: dict, period=None, team=None) -> dict:
    """Recompute from source records without using engine grouping/arithmetic helpers."""
    selected = [
        e
        for e in raw
        if e["period"] < 5
        and (period is None or e["period"] == period)
        and (team is None or e["team"]["id"] == team)
    ]
    shots = [e for e in selected if e["type"]["name"] == "Shot"]
    ids = {e["id"] for e in shots}
    assert report["source_event_count"] == len(raw)
    assert report["selected_event_ids"] == [e["id"] for e in selected]
    assert report["shot_count"] == len(shots)
    assert {s["event_id"] for s in report["shots"]} == ids
    assert not report["missing_shot_weight_ids"]  # This acquired corpus has full support.
    total = sum((Fraction(str(e["shot"]["statsbomb_xg"])) for e in shots), Fraction(0))
    assert Fraction(report["shot_weight"]) == total
    home = meta["home_team"]["home_team_id"]
    away = meta["away_team"]["away_team_id"]
    independent_score = {home: 0, away: 0}
    for e in raw:
        if e["period"] == 5:
            continue
        if e["type"]["name"] == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            independent_score[e["team"]["id"]] += 1
        elif e["type"]["name"] == "Own Goal For":
            independent_score[e["team"]["id"]] += 1
        elif e["type"]["name"] == "Own Goal Against":
            links = set(e.get("related_events", []))
            linked_for = any(f["id"] in links and f["type"]["name"] == "Own Goal For" for f in raw)
            if not linked_for:
                independent_score[away if e["team"]["id"] == home else home] += 1
    assert report["score"] == [independent_score[home], independent_score[away]]
    assert report["score"] == [meta["home_score"], meta["away_score"]]
    grouped = defaultdict(list)
    for e in shots:
        possession = e.get("possession")
        owner = (e.get("possession_team") or {}).get("id")
        if type(possession) is int and owner in (home, away):
            grouped[e["period"], possession, owner, e["team"]["id"]].append(e)
    assert {tuple(u["key"]) for u in report["native_units"]} == set(grouped)
    for unit in report["native_units"]:
        source = grouped[tuple(unit["key"])]
        kept = {e["id"] for e in source}
        assert unit["event_ids"] == [e["id"] for e in source]
        key = tuple(unit["key"])
        assert unit["context_event_ids"] == [
            e["id"]
            for e in raw
            if (e["period"], e.get("possession"), (e.get("possession_team") or {}).get("id"))
            == key[:3]
        ]
        assert Fraction(unit["shot_weight"]) == sum(
            Fraction(str(e["shot"]["statsbomb_xg"])) for e in source
        )
        complement = [e for e in shots if e["id"] not in kept]
        assert unit["complement_event_ids"] == [e["id"] for e in complement]
        assert Fraction(unit["complement_difference"]) == sum(
            (
                Fraction(str(e["shot"]["statsbomb_xg"])) * (1 if e["team"]["id"] == home else -1)
                for e in complement
            ),
            Fraction(0),
        )
    return {
        "events": len(raw),
        "selected": len(selected),
        "shots": len(shots),
        "source_xg": str(total),
        "units": len(grouped),
        "status": "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("data/interim/intelligence/source-verification.json")
    )
    args = parser.parse_args()
    library = json.loads(args.library.read_bytes())
    results = []
    for item in catalog(library):
        if item["mode"] != "local":
            continue
        start = perf_counter()
        raw, meta, identity = load(item["id"], library)
        before = copy.deepcopy(raw)
        report = analyze(raw, meta, identity)
        full = verify(raw, meta, report)
        variants = []
        for period, team in (
            (1, None),
            (2, None),
            (None, meta["home_team"]["home_team_id"]),
            (None, meta["away_team"]["away_team_id"]),
        ):
            variants.append(
                verify(
                    raw, meta, analyze(raw, meta, identity, period=period, team=team), period, team
                )
            )
        assert report == analyze(raw, meta, identity) and raw == before
        results.append(
            {
                "match_id": meta["match_id"],
                "full": full,
                "filters": variants,
                "load_and_verify_seconds": perf_counter() - start,
                "raw_sha256": identity["raw_sha256"],
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "status": "PASS",
        "match_count": len(results),
        "matches": results,
        "original_event_count": sum(r["full"]["events"] for r in results),
        "development_exposed": True,
        "football_usefulness_evaluated": False,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k: v for k, v in output.items() if k != "matches"}))


if __name__ == "__main__":
    main()
