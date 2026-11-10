"""Independent streaming source reconciliation. BUNDLE CONFIG."""

import hashlib
import itertools
import json
import math
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pyarrow.parquet as pq
from verify_temporal_review import census


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(root, config):
    c = json.loads(config.read_bytes())
    original = Path(c["raw"])
    m = json.loads((root / "manifest.json").read_bytes())
    for name, h in m["files"].items():
        assert sha(root / name) == h
    for name, h in m["protected_inputs"].items():
        assert sha(Path(name)) == h
    q = json.loads((root / "quality.json").read_bytes())
    metadata = {
        r["match_id"]: r for r in json.loads((original / "data/matches/43/3.json").read_bytes())
    }
    new = {r["match_id"]: r for r in q["matches"]}
    seen = set()
    counts = {}
    known_xg = {}
    compound_ids = set()
    table = pq.ParquetFile(root / "canonical.parquet")
    for n in range(table.num_row_groups):
        rows = table.read_row_group(n).to_pylist()
        mid = rows[0]["match_id"]
        assert mid not in seen
        seen.add(mid)
        if mid == 8658:
            p = original / "data/events/8658.json"
        else:
            source = Path(
                json.loads((Path(new[mid]["quality_path"]) / "quality.json").read_bytes())[
                    "raw_manifest_path"
                ]
            )
            p = source.parent / f"{mid}.json.events"
        raw = json.loads(p.read_bytes())
        assert [json.loads(r["source_record_json"]) for r in rows] == raw
        assert len(rows) == len(raw)
        for i, (r, e) in enumerate(zip(rows, raw, strict=True)):
            key = (r["source"], mid, r["event_id"])
            assert key not in compound_ids
            compound_ids.add(key)
            assert (
                r["event_id"],
                r["provider_index"],
                r["period"],
                r["period_timestamp"],
                r["raw_event_row"],
            ) == (e["id"], e["index"], e["period"], e["timestamp"], i)
        counts[mid] = len(raw)
        shot = [e for e in raw if e["type"]["name"] == "Shot" and e["period"] < 5]
        missing = [e["id"] for e in shot if e["shot"].get("statsbomb_xg") is None]
        invalid = [
            e["id"]
            for e in shot
            if e["shot"].get("statsbomb_xg") is not None and not 0 <= e["shot"]["statsbomb_xg"] <= 1
        ]
        total = math.fsum(e["shot"]["statsbomb_xg"] for e in shot if e["id"] not in missing)
        known_xg[mid] = total
        if mid != 8658:
            assert new[mid]["source_xg"] == dict(
                match_play_shots=len(shot),
                known_sum=total,
                missing_event_ids=missing,
                invalid_event_ids=invalid,
            )
            assert new[mid]["canonical_null_counts"] == dict(
                Counter({k: sum(r[k] is None for r in rows) for k in rows[0]})
            )
            detail = json.loads((Path(new[mid]["quality_path"]) / "quality.json").read_bytes())
            model = detail["metric_eligibility"]["cross_period_envelope"]["model"]

            def ms(e):
                h, m, s = e["timestamp"].split(":")
                return (int(h) * 3600 + int(m) * 60 + Fraction(s)) * 1000

            bounds = []
            for period in model["periods"]:
                native = [e for e in raw if e["period"] == period["period"]]
                ends = [ms(e) for e in native if e["type"]["name"] == "Half End"]
                assert period["observed_end_envelope_ms"] == [min(ends), max(ends)]
                assert (
                    period["exact_physical_end_ms"] is None and not period["physical_end_certified"]
                )
                bounds.append([int(min(ends)), int(max(ends))])
                for e in native:
                    if e["type"]["name"] not in ("Half Start", "Half End"):
                        assert ms(e) < min(ends)
                        if e.get("duration") is not None:
                            assert ms(e) + Fraction(str(e["duration"])) * 1000 <= min(ends)
            scenarios = [
                census(raw, list(ends) + [0] * (4 - len(ends)))
                for ends in set(itertools.product(*bounds))
            ]
            exposure = detail["metric_eligibility"]["recorded_census_envelope"]["census"]
            assert not exposure["issues"]
            for player in exposure["players"]:
                key = player["team_id"], player["player_id"]
                expected = (
                    [min(v[key] for v in scenarios), max(v[key] for v in scenarios)]
                    if key in scenarios[0]
                    else None
                )
                assert player["conditional_recorded_exposure_ms"] == expected
                assert player["official_minutes"] is None and not player["per90_eligible"]
    assert seen == set(metadata) and len(seen) == q["match_count"] == 64
    assert sum(counts.values()) == q["original_event_count"]
    assert counts[8658] == 2978 and math.isclose(known_xg[8658], 2.5782512977, abs_tol=1e-12)
    assert [metadata[8658]["home_score"], metadata[8658]["away_score"]] == [4, 2]
    assert q["official_minutes"] is None and not q["per90_eligible"]
    return dict(
        status="PASS",
        matches=64,
        original_events=sum(counts.values()),
        original_fixture_events=2978,
        original_fixture_score=[4, 2],
        original_fixture_source_xg=known_xg[8658],
        compound_source_ids=len(compound_ids),
        provider_data_redistributed=False,
    )


if __name__ == "__main__":
    print(json.dumps(verify(*map(Path, sys.argv[1:])), sort_keys=True, indent=2))
