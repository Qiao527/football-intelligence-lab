"""Test source-audit failures with tiny artificial files; no network or real fixture."""

import hashlib
import json
import runpy
from pathlib import Path

import pytest

audit = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/audit_skillcorner.py"))[
    "audit"
]


def make_bundle(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    meta = {
        "id": 7,
        "date_time": "TEST_ONLY",
        "home_team": {"id": 1, "name": "A"},
        "away_team": {"id": 2, "name": "B"},
        "home_team_score": 1,
        "away_team_score": 0,
        "players": [
            {"id": 101, "team_id": 1, "goal": 1, "own_goal": 0},
            {"id": 202, "team_id": 2, "goal": 0, "own_goal": 0},
        ],
    }
    (raw / "7_match.json").write_text(json.dumps(meta))
    frames = [
        {
            "frame": n,
            "period": 1,
            "timestamp": f"t{n}",
            "ball_data": {"is_detected": True},
            "player_data": [
                {"player_id": 101, "is_detected": True},
                {"player_id": 202, "is_detected": False},
            ],
        }
        for n in (1, 2, 3)
    ]
    (raw / "7_tracking_extrapolated.jsonl").write_text(
        "".join(json.dumps(x) + "\n" for x in frames)
    )
    (raw / "7_dynamic_events.csv").write_text(
        "event_id,match_id,frame_start,frame_end,period,event_type,event_subtype,player_id,"
        "associated_player_possession_event_id\n"
        "e1,7,1,2,1,off_ball_run,support,101,e2\n"
        "e2,7,2,3,1,player_possession,,101,\n"
    )
    (raw / "7_phases_of_play.csv").write_text("index,match_id,period\n0,7,1\n")
    manifest = tmp_path / "manifest.json"

    def update_manifest():
        records = [
            {"name": f.name, "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
            for f in sorted(raw.iterdir())
        ]
        manifest.write_text(
            json.dumps({"match_id": "7", "source_revision": "TEST_ONLY", "files": records})
        )

    update_manifest()
    return raw, manifest, update_manifest


def test_raw_source_audit_and_integrity(tmp_path):
    raw, manifest, _ = make_bundle(tmp_path)
    result = audit(raw, manifest)
    assert result["status"] == "WARN"
    assert result["tracking"]["raw_count"] == 3
    assert result["dynamic_events"]["raw_count"] == 2
    assert result["reverse_lookup_example"]["event_id"] == "e1"
    assert result["dynamic_events"]["unresolved_possession_links"] == 0
    (raw / "7_match.json").write_text("{}")
    with pytest.raises(ValueError, match="SHA-256"):
        audit(raw, manifest)


def test_duplicate_ids_fail_even_when_source_hash_matches(tmp_path):
    raw, manifest, update_manifest = make_bundle(tmp_path)
    path = raw / "7_dynamic_events.csv"
    path.write_text(path.read_text().replace("e2,7,2,3", "e1,7,2,3"))
    update_manifest()
    with pytest.raises(ValueError, match="duplicate event ID"):
        audit(raw, manifest)


def test_own_goal_metadata_stays_unreconciled_when_semantics_unknown(tmp_path):
    raw, manifest, update_manifest = make_bundle(tmp_path)
    path = raw / "7_match.json"
    meta = json.loads(path.read_text())
    meta["players"][1]["own_goal"] = 1
    path.write_text(json.dumps(meta))
    update_manifest()
    result = audit(raw, manifest)
    assert result["scorer_metadata_score"] is None
    assert any("Own-goal attribution" in item for item in result["warnings"])
