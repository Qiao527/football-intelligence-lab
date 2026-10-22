"""Independently check process evidence and fixed windows against original 8658 JSON."""

import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from fil.ingestion.statsbomb import verify_bundle

OWNER_TYPES = {
    "Pass",
    "Carry",
    "Ball Receipt*",
    "Dribble",
    "Shot",
    "Miscontrol",
    "Dispossessed",
    "Clearance",
    "Ball Recovery",
    "Interception",
    "Duel",
    "Shield",
    "Goal Keeper",
}


def successful_move(e):
    kind = e["type"]["name"]
    if kind not in {"Pass", "Carry"} or not e.get("player") or e["period"] not in (1, 2, 3, 4):
        return False
    detail = e[kind.lower()]
    if "outcome" in detail:
        return False
    if kind == "Carry":
        return True
    return (
        detail.get("recipient", {}).get("id", 0) > 0
        and all(
            type(detail.get(k)) in (int, float) and math.isfinite(detail[k])
            for k in ("length", "angle")
        )
        and detail["length"] >= 0
        and abs(detail["angle"]) <= math.pi + 1e-6
        and detail.get("height")
        in [dict(id=i, name=n) for i, n in [(1, "Ground Pass"), (2, "Low Pass"), (3, "High Pass")]]
    )


def reached(e, box=False):
    points = [e.get("location")]
    if successful_move(e):
        points.append(e[e["type"]["name"].lower()].get("end_location"))
    for p in points:
        if not p or len(p) < 2 or not (0 <= p[0] <= 120 and 0 <= p[1] <= 80):
            continue
        if (p[0] >= 102 and 18 <= p[1] <= 62) if box else p[0] >= 80:
            return True
    return False


def elapsed(e):
    h, m, s = e["timestamp"].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def main():
    c = json.loads(Path(sys.argv[1]).read_bytes())
    root = Path(sys.argv[2])
    verify_bundle(Path(c["raw"]))
    manifest = json.loads((root / "manifest.json").read_bytes())
    body = (root / "process.json").read_bytes()
    assert hashlib.sha256(body).hexdigest() == manifest["files"]["process.json"]
    reports = json.loads(body)
    assert len(reports) == 1
    report = reports[0]
    raw = json.loads((Path(c["raw"]) / "data/events/8658.json").read_bytes())
    assert len(raw) == 2978
    groups = defaultdict(list)
    for e in raw:
        if e.get("possession") is not None:
            groups[e["possession"]].append(e)
    assert len(report["possessions"]) == len(groups)
    all_windows = {w["cutoff_event_id"]: w for w in report["forecast_windows"]}
    seen_windows = set()
    for r in report["possessions"]:
        group = groups[r["possession_id"]]
        own = [
            e
            for e in group
            if e["team"]["id"] == e["possession_team"]["id"]
            and e["type"]["name"] in OWNER_TYPES
            and e["period"] in (1, 2, 3, 4)
        ]
        ft, box, shot = (
            [e for e in own if predicate(e)]
            for predicate in [
                reached,
                lambda e: reached(e, True),
                lambda e: e["type"]["name"] == "Shot",
            ]
        )
        assert r["source_event_ids"] == [e["id"] for e in group]
        assert r["observed_final_third_event_ids"] == [e["id"] for e in ft]
        assert r["observed_box_event_ids"] == [e["id"] for e in box]
        assert r["shot_event_ids"] == [e["id"] for e in shot]
        assert r["same_possession_shot_and_final_third"] == bool(ft and shot)
        assert r["same_possession_box_and_final_third"] == bool(ft and box)
        unresolved = (
            len({e["period"] for e in group}) != 1
            or not own
            or any(elapsed(a) > elapsed(b) for a, b in zip(group, group[1:], strict=False))
        )
        assert r["order_eligible"] == bool(ft and not unresolved)
        for targets, key in [(shot, "later_shot_event_ids"), (box, "later_box_event_ids")]:
            expected = (
                [e["id"] for e in targets if e["index"] > ft[0]["index"]]
                if r["order_eligible"]
                else []
            )
            assert r[key] == expected
        for i, e in enumerate(own):
            if not successful_move(e):
                continue
            seen_windows.add(e["id"])
            w = all_windows[e["id"]]
            future = own[i + 1 : i + 6]
            complete = not unresolved and len(future) == 5
            assert w["feature_event_ids"] == [e["id"]]
            assert w["cutoff_provider_index"] == e["index"]
            assert w["outcome_event_ids"] == ([x["id"] for x in future] if complete else [])
            assert w["outcome"] == (
                int(any(x["type"]["name"] == "Shot" for x in future)) if complete else None
            )
    assert seen_windows == set(all_windows)
    print(
        json.dumps(
            dict(
                status="PASS",
                original_events=len(raw),
                independent_native_groups=len(groups),
                summary=report["summary"],
                held_out_results="not available; no expanded acquisition authorised",
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
