"""Independent original-JSON verification of accepted metric reports. REPORT_LIST ORIGINAL_RAW."""

import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_labels(raw, labels):
    by = {e["id"]: e for e in raw}
    position = {e["id"]: n for n, e in enumerate(raw)}
    ends_by_period = defaultdict(list)
    for e in raw:
        if e["type"]["name"] == "Half End":
            ends_by_period[e["period"]].append(e)
    expected_cutoffs = {
        e["id"]
        for e in raw
        if e.get("possession") is not None
        and e["team"]["id"] == e.get("possession_team", {}).get("id")
        and (
            e["type"]["name"] == "Carry"
            or e["type"]["name"] == "Pass"
            and "outcome" not in e["pass"]
        )
    }
    assert len(labels) == len({r["cutoff_event_id"] for r in labels})
    assert {r["cutoff_event_id"] for r in labels} == expected_cutoffs
    groups = defaultdict(list)
    for e in raw:
        groups[e.get("possession")].append(e)
    labelled = defaultdict(list)
    for row in labels:
        cutoff = by[row["cutoff_event_id"]]
        records = groups[cutoff["possession"]]
        indices = [position[records[0]["id"]], position[records[-1]["id"]]]
        owners = {e.get("possession_team", {}).get("id") for e in records}
        valid = (
            len({e["period"] for e in records}) == 1
            and records[0]["period"] < 5
            and len(owners) == 1
            and None not in owners
            and indices[-1] - indices[0] + 1 == len(records)
        )
        shots = [
            e
            for e in records
            if e["type"]["name"] == "Shot"
            and e["team"]["id"] == row["owner_team_id"]
            and e["index"] > cutoff["index"]
        ]
        assert row["later_shot_event_ids"] == [e["id"] for e in shots]
        assert row["feature_event_ids"] == [cutoff["id"]]
        ends = ends_by_period[cutoff["period"]]
        incomplete = any(
            (e.get("half_end") or {}).get(k)
            for e in ends
            for k in ("early_video_end", "match_suspended")
        )
        after = raw[indices[-1] + 1] if indices[-1] + 1 < len(raw) else None
        change = bool(
            after and after["period"] == cutoff["period"] and after.get("possession") is not None
        )
        content = [
            e for e in records if e["type"]["name"] not in ("Half Start", "Half End", "Starting XI")
        ]
        terminal = bool(
            len(ends) == 2
            and len({e["team"]["id"] for e in ends}) == 2
            and content
            and ends[1]["id"] in ends[0].get("related_events", [])
            and ends[0]["id"] in ends[1].get("related_events", [])
            and min(e["index"] for e in ends) > content[-1]["index"]
        )
        if terminal:
            terminal = all(
                e.get("possession") == cutoff["possession"] or e["type"]["name"] == "Half End"
                for e in raw
                if content[-1]["index"] < e["index"] <= ends[-1]["index"]
            )
        closed = valid and not incomplete and (change or terminal)
        y = None if not valid else 1 if shots else 0 if closed else None
        assert row["outcome"] == y, cutoff["id"]
        assert row["complete_terminal_chance_evidence"] == closed
        assert bool(row["closure_evidence_ids"]) == closed
        missing = [e["id"] for e in shots if e["shot"].get("statsbomb_xg") is None]
        assert row["missing_shot_xg_event_ids"] == missing
        total = sum(e["shot"]["statsbomb_xg"] for e in shots if e["id"] not in missing)
        assert row["observed_known_source_xg_sum"] == total
        assert row["complete_later_shot_xg_sum"] == (total if closed and not missing else None)
        if y is not None:
            labelled[cutoff["possession"]].append(row)
        else:
            assert row["within_match_possession_weight"] is None
    for values in labelled.values():
        assert all(
            r["within_match_possession_weight"] == 1 / (len(labelled) * len(values)) for r in values
        )


def check_report(folder, metadata, proposal):
    manifest = json.loads((folder / "manifest.json").read_bytes())
    assert {p.name for p in folder.iterdir()} == set(manifest["files"]) | {"manifest.json"}
    for name, h in manifest["files"].items():
        assert not (folder / name).is_symlink() and sha(folder / name) == h
    q = json.loads((folder / "quality.json").read_bytes())
    mid = q["match_id"]
    rawmanifest = Path(q["raw_manifest_path"])
    assert sha(rawmanifest) == q["source_manifest_sha256"]
    src = json.loads(rawmanifest.read_bytes())
    assert src["upstream_revision"] == proposal["revision"]
    assert src["proposal_sha256"] == sha(Path("docs/research/statsbomb_corpus_proposal.json"))
    files = [f for f in proposal["files"] if f["path"].endswith(f"/{mid}.json")]
    assert set(src["files"]) == {f["path"] for f in files} and len(files) == 2
    for f in files:
        p = rawmanifest.parent / (f"{mid}.json." + f["path"].split("/")[1])
        body = p.read_bytes()
        assert len(body) == f["size_bytes"]
        assert (
            hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            == f["upstream_git_blob_sha1"]
        )
        assert sha(p) == src["files"][f["path"]]["sha256"]
        assert src["files"][f["path"]]["source_url"] == (
            f"https://raw.githubusercontent.com/hudl/open-data/{proposal['revision']}/{f['path']}"
        )
    raw = json.loads((rawmanifest.parent / f"{mid}.json.events").read_bytes())
    projected = pq.read_table(folder / "canonical.parquet").to_pylist()
    assert [json.loads(r["source_record_json"]) for r in projected] == raw
    assert len(raw) == len(projected) == q["raw_count"] == q["canonical_count"]
    assert len({e["id"] for e in raw}) == len(raw)
    for n, (e, r) in enumerate(zip(raw, projected, strict=True)):
        assert (
            r["event_id"],
            r["provider_index"],
            r["period"],
            r["period_timestamp"],
            r["raw_event_row"],
        ) == (e["id"], e["index"], e["period"], e["timestamp"], n)
        assert r["match_id"] == mid and r["source_manifest_sha256"] == q["source_manifest_sha256"]
        assert (r["team_id"], r["player_id"], r["possession_id"], r["possession_team_id"]) == (
            e["team"]["id"],
            e.get("player", {}).get("id"),
            e.get("possession"),
            e.get("possession_team", {}).get("id"),
        )
        assert [r["x"], r["y"]] == (e.get("location") or [None, None])[:2]
        if e["type"]["name"] in ("Pass", "Carry"):
            assert [r["end_x"], r["end_y"]] == (
                e[e["type"]["name"].lower()].get("end_location") or [None, None]
            )[:2]
        if e["type"]["name"] == "Shot":
            assert r["shot_xg"] == e["shot"].get("statsbomb_xg")
    assert q["canonical_null_counts"] == {
        name: sum(r[name] is None for r in projected) for name in projected[0]
    }
    meta = metadata[mid]
    teams = [meta[k][k + "_id"] for k in ("home_team", "away_team")]
    lineups = json.loads((rawmanifest.parent / f"{mid}.json.lineups").read_bytes())
    roster = {(t["team_id"], p["player_id"]) for t in lineups for p in t["lineup"]}
    assert roster == {(p["team_id"], p["player_id"]) for p in q["roster"]}
    assert q["original_match_metadata"] == meta
    labels = json.loads((folder / "labels.json").read_bytes())
    assert (
        q["official_minutes"] is None
        and not q["per90_eligible"]
        and not q["physical_timing_certified"]
    )
    if q["status"] == "PASS":
        assert not q["material_failures"]
        assert {t["team_id"] for t in lineups} == set(teams)
        assert all(
            (e["team"]["id"], p["id"]) in roster
            for e in raw
            for p in (
                e.get("player"),
                e.get("pass", {}).get("recipient"),
                e.get("substitution", {}).get("replacement"),
            )
            if p
        )
        assert all(
            a["index"] < b["index"] and a["period"] <= b["period"]
            for a, b in zip(raw, raw[1:], strict=False)
        )
        for e in raw:
            if e["type"]["name"] in ("Pass", "Carry", "Shot"):
                points = [e.get("location")]
                if e["type"]["name"] in ("Pass", "Carry"):
                    points.append(e[e["type"]["name"].lower()].get("end_location"))
                assert all(
                    point is None
                    or len(point) >= 2
                    and all(
                        type(v) in (int, float) and math.isfinite(v) and 0 <= v <= limit
                        for v, limit in zip(point[:2], (120, 80), strict=True)
                    )
                    for point in points
                )
        goals = dict.fromkeys(teams, 0)
        by = {e["id"]: e for e in raw}
        for e in raw:
            kind = e["type"]["name"]
            if e["period"] == 5:
                continue
            if kind == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
                goals[e["team"]["id"]] += 1
            if kind == "Own Goal Against":
                goals[next(t for t in teams if t != e["team"]["id"])] += 1
            if kind == "Own Goal For" and not any(
                by[i]["type"]["name"] == "Own Goal Against"
                for i in e.get("related_events", [])
                if i in by
            ):
                # Also honour a link present only on the opposing perspective.
                if not any(
                    e["id"] in other.get("related_events", [])
                    and other["type"]["name"] == "Own Goal Against"
                    for other in raw
                ):
                    goals[e["team"]["id"]] += 1
        assert [goals[t] for t in teams] == [meta["home_score"], meta["away_score"]]
        assert q["metric_eligibility"]["score"]["match_play"] == [goals[t] for t in teams]
        check_labels(raw, labels)
    else:
        assert q["material_failures"] and not labels
    return q, sha(folder / "manifest.json")


def main():
    paths, original = Path(sys.argv[1]), Path(sys.argv[2])
    proposal_path = Path("docs/research/statsbomb_corpus_proposal.json")
    assert sha(proposal_path) == "bd9357a8bf3c87c808477308770f1e798b7f7b1d98f4468c7fc6c56e9ac17787"
    proposal = json.loads(proposal_path.read_bytes())
    assert sha(original / "data/matches/43/3.json") == proposal["metadata_source_sha256"]
    metadata = {
        m["match_id"]: m for m in json.loads((original / "data/matches/43/3.json").read_bytes())
    }
    reports, policy, events, states = {}, None, 0, {}
    for p in json.loads(paths.read_bytes()):
        q, h = check_report(Path(p), metadata, proposal)
        assert str(q["match_id"]) not in reports
        reports[str(q["match_id"])] = h
        states[str(q["match_id"])] = q["status"]
        events += q["raw_count"]
        assert (
            q["policy"]["file_sha256"]
            == sha(Path("docs/research/METRIC_ELIGIBILITY.md"))
            == "bda88c4231376c467dd2be90387d5fdae2139d3b121bfd24a8b414f2ebc68561"
        )
        assert q["policy"]["anchor"] == "a6f64008a352689620971de4887cd48a431d43c9"
        assert policy is None or policy == q["policy"]
        policy = q["policy"]
    print(
        json.dumps(
            dict(
                status="PASS",
                reports=reports,
                quality_statuses=states,
                policy=policy,
                original_event_count=events,
                verifier_sha256=sha(Path(__file__)),
            ),
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
