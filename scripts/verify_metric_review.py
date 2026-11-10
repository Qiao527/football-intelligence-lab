"""Independent raw-array verification of diagnostic eligibility and proposed labels.

Usage: REVIEW_BUNDLE ORIGINAL_RAW CONFIG. No future payloads acquired or evaluated.
"""

import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(folder, original, config):
    manifest = json.loads((folder / "manifest.json").read_bytes())
    assert not manifest["gate_changed"] and not manifest["acquisition_performed"]
    assert not manifest["predictive_evaluation_performed"]
    for name, sha in manifest["files"].items():
        assert digest(folder / name) == sha
    for name, sha in manifest["protected_inputs"].items():
        assert digest(Path(name)) == sha, name
    labels = json.loads((folder / "labels.json").read_bytes())
    matrices = {r["match_id"]: r for r in json.loads((folder / "eligibility.json").read_bytes())}
    counts, seen = {}, set()
    metadata = {
        m["match_id"]: m for m in json.loads((original / "data/matches/43/3.json").read_bytes())
    }
    for mid, matrix in matrices.items():
        if mid == 8658:
            path = original / "data/events/8658.json"
        else:
            matches = list(Path("data/raw/statsbomb-corpus").glob(f"*/{mid}/{mid}.json.events"))
            assert len(matches) == 1
            path = matches[0]
        raw = json.loads(path.read_bytes())
        by = {e["id"]: e for e in raw}
        assert len(by) == len(raw)
        e = matrix["eligibility"]
        assert e["source_identity"]["support"] == "fully_supported", (mid, e["source_identity"])
        assert e["source_identity"]["original_event_count"] == len(raw)
        assert e["source_identity"]["payload_sha256"] == digest(path)
        assert e["score"]["support"] == "fully_supported", (mid, e["score"])
        assert e["score"]["match_play"] == [
            metadata[mid]["home_score"],
            metadata[mid]["away_score"],
        ]
        assert {i for d in e["score"]["decisions"] for i in d["source_event_ids"]} == {
            r["id"]
            for r in raw
            if r["type"]["name"] in ("Shot", "Own Goal For", "Own Goal Against")
        }
        overlaps, unknown = [], []
        for period in sorted({r["period"] for r in raw if r["period"] < 5}):
            period_rows = [r for r in raw if r["period"] == period]

            def ms(r):
                h, m, s = r["timestamp"].split(":")
                return (Fraction(h) * 3600 + Fraction(m) * 60 + Fraction(s)) * 1000

            earliest = min(ms(r) for r in period_rows if r["type"]["name"] == "Half End")
            for r in period_rows:
                if r["type"]["name"] in ("Half Start", "Half End"):
                    continue
                if r.get("duration") is None:
                    unknown.append(r["id"])
                elif ms(r) + Fraction(str(r["duration"])) * 1000 > earliest:
                    overlaps.append(r["id"])
        assert e["known_completion_boundary_invariance"]["known_duration_overlap_ids"] == overlaps
        assert e["known_completion_boundary_invariance"]["unknown_duration_event_ids"] == unknown
        assert e["exact_time_exposure"]["official_minutes"] is None
        assert not e["exact_time_exposure"]["per90_eligible"]
        expected_cutoffs = {
            r["id"]
            for r in raw
            if r["team"]["id"] == r.get("possession_team", {}).get("id")
            and r.get("possession") is not None
            and (
                r["type"]["name"] == "Carry"
                or r["type"]["name"] == "Pass"
                and "outcome" not in r["pass"]
            )
        }
        actual = [r for r in labels if r["match_id"] == mid]
        assert {r["cutoff_event_id"] for r in actual} == expected_cutoffs
        for row in actual:
            uid = mid, row["cutoff_event_id"]
            assert uid not in seen
            seen.add(uid)
            cutoff = by[row["cutoff_event_id"]]
            pid = cutoff["possession"]
            positions = [i for i, r in enumerate(raw) if r.get("possession") == pid]
            records = [raw[i] for i in positions]
            unambiguous = (
                len({r["period"] for r in records}) == 1
                and records[0]["period"] in (1, 2, 3, 4)
                and len({r.get("possession_team", {}).get("id") for r in records}) == 1
                and records[0].get("possession_team", {}).get("id") is not None
                and positions[-1] - positions[0] + 1 == len(positions)
            )
            shot_ids = [
                r["id"]
                for r in records
                if r["index"] > cutoff["index"]
                and r["type"]["name"] == "Shot"
                and r["team"]["id"] == row["owner_team_id"]
            ]
            assert row["later_shot_event_ids"] == shot_ids
            assert row["feature_event_ids"] == [cutoff["id"]]
            ends = [
                r
                for r in raw
                if r["period"] == cutoff["period"] and r["type"]["name"] == "Half End"
            ]
            truncated = any(
                (r.get("half_end") or {}).get(k)
                for r in ends
                for k in ("early_video_end", "match_suspended")
            )
            after = raw[positions[-1] + 1] if positions[-1] + 1 < len(raw) else None
            closed_by_change = bool(
                after
                and after["period"] == cutoff["period"]
                and after.get("possession") is not None
            )
            # Independent scan: a terminal segment must have no intervening foreign/
            # unassigned content before its reciprocal opposing-team end markers.
            content = [
                r
                for r in records
                if r["type"]["name"] not in ("Half Start", "Half End", "Starting XI")
            ]
            closed_by_end = bool(
                len(ends) == 2
                and len({r["team"]["id"] for r in ends}) == 2
                and ends[1]["id"] in ends[0].get("related_events", [])
                and ends[0]["id"] in ends[1].get("related_events", [])
                and content
                and min(r["index"] for r in ends) > content[-1]["index"]
            )
            if closed_by_end:
                intervening = [
                    r for r in raw if content[-1]["index"] < r["index"] <= ends[-1]["index"]
                ]
                closed_by_end = all(
                    r.get("possession") == pid or r["type"]["name"] == "Half End"
                    for r in intervening
                )
            closed = unambiguous and not truncated and (closed_by_change or closed_by_end)
            expected = None if not unambiguous else 1 if shot_ids else 0 if closed else None
            assert row["outcome"] == expected, uid
            assert row["complete_terminal_chance_evidence"] == closed
            assert bool(row["closure_evidence_ids"]) == closed
            missing = [i for i in shot_ids if by[i]["shot"].get("statsbomb_xg") is None]
            assert row["missing_shot_xg_event_ids"] == missing
            xg = sum(by[i]["shot"]["statsbomb_xg"] for i in shot_ids if i not in missing)
            assert row["observed_known_source_xg_sum"] == xg
            assert row["complete_later_shot_xg_sum"] == (xg if closed and not missing else None)
        counts[mid] = dict(Counter(r["observation_state"] for r in actual))
        by_pid = defaultdict(list)
        for r in actual:
            if r["outcome"] is not None:
                by_pid[r["possession_id"]].append(r)
            else:
                assert r["within_match_possession_weight"] is None
        for rows in by_pid.values():
            assert all(
                r["within_match_possession_weight"] == 1 / (len(by_pid) * len(rows)) for r in rows
            )
    assert (
        sum(r["eligibility"]["source_identity"]["original_event_count"] for r in matrices.values())
        == 24805
    )
    assert matrices[8658]["eligibility"]["score"]["match_play"] == [4, 2]
    assert matrices[8656]["eligibility"]["score"]["match_play"] == [2, 1]
    future = json.loads((folder / "future_partitions.json").read_bytes())
    proposal = json.loads(Path("docs/research/statsbomb_corpus_proposal.json").read_bytes())
    ids = [r["match_id"] for rows in future["partitions"].values() for r in rows]
    assert len(ids) == len(set(ids)) == 57 and set(ids) == set(proposal["expansion_new_match_ids"])
    assert not set(ids) & set(matrices)
    for name, rows in future["partitions"].items():
        for r in rows:
            expected = (
                "train"
                if r["match_date"] <= "2018-06-26"
                else ("validation" if r["match_date"] <= "2018-07-01" else "test")
            )
            assert name == expected and len(r["expected_files"]) == 2
            assert not list(Path("data/raw/statsbomb-corpus").glob(f"*/{r['match_id']}"))
    parent = Path(manifest["parent_review"])
    old = subprocess.run(
        [sys.executable, "scripts/verify_temporal_review.py", str(parent), str(config)],
        capture_output=True,
        text=True,
    )
    assert old.returncode == 0, (old.stdout, old.stderr)
    for name, sha in manifest["protected_inputs"].items():
        assert digest(Path(name)) == sha
    return dict(
        status="PASS",
        original_events=24805,
        new_target_cutoffs=len(labels),
        per_match=counts,
        old_independent_reconciliation="PASS",
        expansion_gate="BLOCKED",
        acquisition_performed=False,
        predictive_evaluation_performed=False,
    )


if __name__ == "__main__":
    print(json.dumps(verify(*map(Path, sys.argv[1:])), sort_keys=True, indent=2))
