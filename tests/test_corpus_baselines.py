"""TEST_ONLY primary weighting, source-order features and sealed test acquisition."""

import json
from pathlib import Path

import pytest

from fil.research import corpus_baselines as b
from fil.research import corpus_expansion as expansion
from fil.research.acquisition import REVISION, digest
from fil.research.pilot import encode


def test_possession_weighted_score_is_distinct_from_cutoff_averaging():
    rows = [
        dict(
            match_id=1,
            outcome=y,
            within_match_possession_weight=w,
            cutoff_provider_index=i,
            later_shot_event_ids=["TEST-SHOT"] if y else [],
        )
        for i, (y, w) in enumerate([(1, 0.25), (0, 0.25), (0, 0.5)])
    ]
    s = b.scores(rows, [0.2] * 3)
    assert s["equal_match_possession_brier"] == pytest.approx(0.19)
    assert s["pooled_cutoff_brier"] == pytest.approx(0.24)
    assert s["calibration"][2]["observed"] == 0.25
    assert s["retrieval_at_10"][0]["unique_shot_coverage"] == 1
    impossible = b.scores(rows, [0, 0, 0])
    assert impossible["log_loss"] is None and impossible["infinite_log_predictions"] == 1
    rows[0]["outcome"] = None
    with pytest.raises(ValueError, match="Confirmed"):
        b.scores(rows, [0.2] * 3)


def test_cannot_create_model_freeze_after_any_test_payload_is_opened(tmp_path, monkeypatch):
    monkeypatch.setattr(
        b, "frozen_plan", lambda *a: ({"partitions": {"test": [{"match_id": 999}]}}, "TEST")
    )
    (tmp_path / REVISION / "999").mkdir(parents=True)
    with pytest.raises(ValueError, match="Test payloads already opened"):
        b.freeze(Path("UNREAD"), Path("UNREAD"), tmp_path, tmp_path, "a" * 40)


def test_test_acquisition_requires_independent_development_proof(tmp_path, monkeypatch):
    from fil.research.accepted_corpus import policy

    monkeypatch.setattr(expansion, "verify_gate", lambda *a: {})
    monkeypatch.setattr(
        expansion,
        "frozen_plan",
        lambda *a: (
            {"partitions": {"test": [dict(match_id=999, match_date="2018-07-14")]}},
            "TEST",
        ),
    )
    model = tmp_path / "freeze"
    model.mkdir()
    (model / "freeze.json").write_text(
        encode(
            dict(
                plan_sha256="TEST",
                policy=policy(),
                frozen_before_test_acquisition=True,
                test_match_ids=[999],
            )
        )
    )
    monkeypatch.setattr(expansion, "verify_artifact", lambda *a: {})
    with pytest.raises(ValueError, match="Independent development-model verification"):
        expansion.expand(
            Path("UNREAD"),
            Path("UNREAD"),
            Path("UNREAD"),
            tmp_path,
            tmp_path,
            "a" * 40,
            "test",
            model_freeze=model,
        )
    assert not (tmp_path / REVISION).exists()


def test_immutable_run_json_preserves_bytes_and_modification_time(tmp_path):
    p = tmp_path / "run.json"
    expansion.immutable_json(p, dict(status="PASS"))
    before = (p.read_bytes(), p.stat().st_mtime_ns)
    expansion.immutable_json(p, dict(status="PASS"))
    assert (p.read_bytes(), p.stat().st_mtime_ns) == before
    with pytest.raises(ValueError, match="Immutable"):
        expansion.immutable_json(p, dict(status="BLOCKED"))


def test_score_state_lineage_contains_only_original_past_goals(tmp_path):
    rawdir = tmp_path / "raw"
    rawdir.mkdir()
    raw = [
        dict(id="TEST-GOAL-1", index=1, period=1, team=dict(id=1), type=dict(name="Shot")),
        dict(
            id="TEST-CARRY",
            index=2,
            period=2,
            team=dict(id=2),
            type=dict(name="Carry"),
            location=[10, 20],
            carry=dict(end_location=[20, 30]),
        ),
        dict(id="TEST-GOAL-3", index=3, period=2, team=dict(id=2), type=dict(name="Shot")),
        dict(
            id="TEST-PASS",
            index=4,
            period=2,
            team=dict(id=2),
            type=dict(name="Pass"),
            location=[20, 30],
            **{"pass": dict(end_location=[30, 40])},
        ),
    ]
    (rawdir / "999.json.events").write_text(encode(raw))
    folder = tmp_path / "report"
    folder.mkdir()
    q = dict(
        match_id=999,
        status="PASS",
        raw_manifest_path=str(rawdir / "manifest.json"),
        roster=[dict(player_id=10)],
        original_match_metadata=dict(
            home_team=dict(home_team_id=1), away_team=dict(away_team_id=2)
        ),
        metric_eligibility=dict(
            score=dict(
                decisions=[
                    dict(
                        provider_index=i,
                        scored=True,
                        domain="match_play",
                        beneficiary_team_id=t,
                        source_event_ids=[f"TEST-GOAL-{i}"],
                    )
                    for i, t in [(1, 1), (3, 2)]
                ]
            )
        ),
    )
    labels = [dict(cutoff_event_id=i, outcome=y) for i, y in [("TEST-CARRY", 1), ("TEST-PASS", 0)]]
    (folder / "quality.json").write_text(encode(q))
    (folder / "labels.json").write_text(encode(labels))
    (folder / "manifest.json").write_text(
        encode(dict(files={p.name: digest(p.read_bytes()) for p in folder.iterdir()}))
    )
    rows, _ = b.rows_for_report(folder, "train")
    assert rows[0]["features"]["context"] == "period=2:state=trailing"
    assert rows[0]["context_feature_event_ids"] == ["TEST-CARRY", "TEST-GOAL-1"]
    assert rows[0]["feature_indices"] == [2, 1]
    assert "TEST-GOAL-3" not in rows[0]["context_feature_event_ids"]
    assert rows[1]["features"]["context"] == "period=2:state=level"
    q["match_id"] = 8655
    (folder / "quality.json").write_text(encode(q))
    m = json.loads((folder / "manifest.json").read_bytes())
    m["files"]["quality.json"] = digest((folder / "quality.json").read_bytes())
    (folder / "manifest.json").write_text(encode(m))
    with pytest.raises(ValueError, match="seven exposed"):
        b.rows_for_report(folder, "test")
