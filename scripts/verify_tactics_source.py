"""Independent original-source reconciliation of FIL-012 artifacts and window queries.

CONFIG TACTICS: provider bytes stay local. Expected pass sets, edge counts, position
samples, progression and score contexts are recomputed from raw JSON, not candidate facts.
"""

import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from fil.explorer.data import load_match
from fil.metrics.shots import MatchFilter, apply_filter
from fil.metrics.tactics import passing_network, select_actions
from fil.time.clock import PeriodRange


def elapsed(e):
    h, m, s = e["timestamp"].split(":")
    whole, fraction = s.split(".")
    return (int(h) * 3600 + int(m) * 60 + int(whole)) * 1000 + int(fraction)


def main():
    config = json.loads(Path(sys.argv[1]).read_bytes())
    folder = Path(sys.argv[2])
    table, meta = load_match(config)
    raw = json.loads((Path(config["raw"]) / "data/events/8658.json").read_bytes())
    assert len(raw) == table.num_rows == 2978
    manifest = json.loads((folder / "manifest.json").read_bytes())
    assert set(p.name for p in folder.iterdir()) == set(manifest["files"]) | {"manifest.json"}
    for name, entry in manifest["files"].items():
        body = (folder / name).read_bytes()
        assert (
            len(body) == entry["size_bytes"] and hashlib.sha256(body).hexdigest() == entry["sha256"]
        )
    by_id = {e["id"]: e for e in raw}
    assert len(by_id) == len(raw)
    home, away = meta["home_team_id"], meta["away_team_id"]
    scores = {home: 0, away: 0}
    counted = set()
    contexts = {}
    for e in raw:
        difference = scores[e["team"]["id"]] - scores[away if e["team"]["id"] == home else home]
        contexts[e["id"]] = (
            "level" if difference == 0 else "leading" if difference > 0 else "trailing"
        )
        if (
            e["type"]["name"] == "Shot"
            and e["period"] < 5
            and e["shot"]["outcome"]["name"] == "Goal"
        ):
            scores[e["team"]["id"]] += 1
        if e["type"]["name"] in ("Own Goal For", "Own Goal Against") and e["id"] not in counted:
            pair = [e] + [
                by_id[i]
                for i in e.get("related_events", [])
                if by_id[i]["type"]["name"] in ("Own Goal For", "Own Goal Against")
            ]
            credit = next(
                (p["team"]["id"] for p in pair if p["type"]["name"] == "Own Goal For"), None
            )
            if credit is None:
                credit = away if e["team"]["id"] == home else home
            scores[credit] += 1
            counted.update(p["id"] for p in pair)
    assert [scores[home], scores[away]] == [meta["home_score"], meta["away_score"]] == [4, 2]
    original = [e for e in raw if e["type"]["name"] in ("Pass", "Carry")]
    complete = [
        e
        for e in original
        if e["type"]["name"] == "Pass"
        and "outcome" not in e["pass"]
        and isinstance(e["pass"].get("recipient", {}).get("id"), int)
        and e["period"] < 5
    ]
    assert len(complete) == 650
    expected_pairs = defaultdict(list)
    for e in complete:
        expected_pairs[e["team"]["id"], e["player"]["id"], e["pass"]["recipient"]["id"]].append(
            e["id"]
        )

    def check_edges(actual, expected):
        keys = {(e["team_id"], e["passer_id"], e["recipient_id"]): e for e in actual}
        assert set(keys) == set(expected)
        for key, ids in expected.items():
            assert keys[key]["event_ids"] == ids
            assert keys[key]["weight"] == len(ids) == len(set(ids))

    check_edges(pq.read_table(folder / "edges.parquet").to_pylist(), expected_pairs)
    actual = pq.read_table(folder / "actions.parquet")
    actions = {r["event_id"]: r for r in actual.to_pylist()}
    assert list(actions) == [e["id"] for e in original]
    expected_progress = {}
    for e in original:
        kind = e["type"]["name"]
        detail = e[kind.lower()]
        r = actions[e["id"]]
        assert r["score_state"] == contexts[e["id"]]
        assert r["period"] == e["period"] and r["provider_index"] == e["index"]
        for names, values in (
            (("x", "y"), e.get("location") or []),
            (("end_x", "end_y"), detail.get("end_location") or []),
        ):
            for i, name in enumerate(names):
                assert r[name] == (values[i] if i < len(values) else None)
        completed = kind == "Pass" and e["id"] in {p["id"] for p in complete}
        assert (r["status"] == "completed") == completed
        eligible = completed or kind == "Carry"
        start = e.get("location")
        end = detail.get("end_location")
        if (
            eligible
            and start
            and end
            and all(
                0 <= v <= bound
                for v, bound in zip(start[:2] + end[:2], [120, 80, 120, 80], strict=True)
            )
        ):
            gain = math.hypot(120 - start[0], 40 - start[1]) - math.hypot(120 - end[0], 40 - end[1])
            progressive = end[0] > start[0] and gain >= 10
            assert r["progressive"] is progressive
            assert math.isclose(r["distance_gain"], gain, abs_tol=1e-12)
            assert r["final_third_entry"] is (start[0] < 80 <= end[0])

            def inside(xy):
                return xy[0] >= 102 and 18 <= xy[1] <= 62

            assert r["box_entry"] is (not inside(start) and inside(end))
            expected_progress[e["id"]] = progressive
        else:
            assert r["progressive"] is None
            expected_progress[e["id"]] = None
    actual_complete = pq.read_table(folder / "completed_passes.parquet")
    assert actual_complete["event_id"].to_pylist() == [e["id"] for e in complete]
    for n in pq.read_table(folder / "nodes.parquet").to_pylist():
        sent = [
            e
            for e in complete
            if (e["team"]["id"], e["player"]["id"]) == (n["team_id"], n["player_id"])
        ]
        received = [
            e
            for e in complete
            if (e["team"]["id"], e["pass"]["recipient"]["id"]) == (n["team_id"], n["player_id"])
        ]
        positioned = [e for e in sent if e.get("location") is not None]
        assert n["sent"] == len(sent) and n["received"] == len(received)
        assert set(n["event_ids"]) == {e["id"] for e in sent + received}
        assert n["position_event_ids"] == [e["id"] for e in positioned]
        assert n["sample_count"] == len(positioned)
        if positioned:
            assert n["x"] == math.fsum(e["location"][0] for e in positioned) / len(positioned)
            assert n["y"] == math.fsum(e["location"][1] for e in positioned) / len(positioned)
            for index, axis in enumerate(("x", "y")):
                assert n[f"{axis}_min"] == min(e["location"][index] for e in positioned)
                assert n[f"{axis}_max"] == max(e["location"][index] for e in positioned)
        else:
            assert n["x"] is n["y"] is None
    queries = 0
    durations = {
        p: max(elapsed(e) for e in raw if e["period"] == p and e["type"]["name"] == "Half End")
        for p in (1, 2)
    }
    for width in (300000, 600000, 900000):
        seen = []
        for period, duration in durations.items():
            for start in range(0, duration, width):
                end = min(start + width, duration)
                terminal = end == duration
                segment = PeriodRange(period, start, end, terminal)
                for context in (None, "level", "leading", "trailing"):
                    chosen = apply_filter(
                        table,
                        MatchFilter(
                            (segment,), score_state=context, home_team_id=home, away_team_id=away
                        ),
                    )
                    edges, _ = passing_network(select_actions(actual, chosen))
                    expected = defaultdict(list)
                    for e in complete:
                        if (
                            e["period"] == period
                            and (start <= elapsed(e) < end or terminal and elapsed(e) == end)
                            and (context is None or contexts[e["id"]] == context)
                        ):
                            expected[
                                e["team"]["id"], e["player"]["id"], e["pass"]["recipient"]["id"]
                            ].append(e["id"])
                            if context is None:
                                seen.append(e["id"])
                    check_edges(edges.to_pylist(), expected)
                    queries += 1
        assert sorted(seen) == sorted(e["id"] for e in complete) and len(seen) == len(set(seen))
    for r in pq.read_table(folder / "comparisons.parquet").to_pylist():
        subset = [
            e
            for e in original
            if e["team"]["id"] == r["team_id"]
            and (
                e["period"] == int(r["selection"].split()[-1])
                if r["selection"].startswith("Period")
                else contexts[e["id"]] == r["selection"].split()[-1]
            )
        ]
        ids = {e["id"] for e in subset}
        passes = [e for e in complete if e["id"] in ids]
        assert r["selected_events"] == len(subset)
        assert r["completed_passes"] == len(passes)
        assert r["directed_pairs"] == len(
            {(e["player"]["id"], e["pass"]["recipient"]["id"]) for e in passes}
        )
        assert r["observed_carries"] == sum(e["type"]["name"] == "Carry" for e in subset)
        assert r["progressive_passes"] == sum(expected_progress[e["id"]] is True for e in passes)
        assert r["progressive_carries"] == sum(
            e["type"]["name"] == "Carry" and expected_progress[e["id"]] is True for e in subset
        )
    print(
        json.dumps(
            {
                "source_events": len(raw),
                "official_score": [4, 2],
                "audited_actions": len(original),
                "completed_passes": len(complete),
                "directed_pairs": len(expected_pairs),
                "verified_window_context_queries": queries,
                "progressive_passes": sum(
                    e["type"]["name"] == "Pass" and expected_progress[e["id"]] is True
                    for e in original
                ),
                "progressive_carries": sum(
                    e["type"]["name"] == "Carry" and expected_progress[e["id"]] is True
                    for e in original
                ),
                "physical_directions": "unknown",
                "status": "PASS",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
