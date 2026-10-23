"""TEST_ONLY packet guard: provenance, no invented labels and source-only adjudication."""

import csv
import hashlib
import json
import runpy

import pytest

prepare = runpy.run_path("scripts/prepare_reentry_review.py")["prepare"]


def write(path, data):
    path.write_text(json.dumps(data))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(tmp_path):
    study = tmp_path / "study"
    study.mkdir()
    raw = tmp_path / "raw.json"
    event = dict(
        id="TEST_ONLY_A",
        index=1,
        period=1,
        timestamp="00:00:01.000",
        type=dict(name="Pass"),
        team=dict(id=1),
        possession_team=dict(id=1),
        player=dict(id=10),
        location=[60, 20],
        **{"pass": dict(end_location=[85, 20])},
    )
    raw_sha = write(raw, [event])
    row = dict(
        match_id=1,
        possession_id=1,
        feature=True,
        outcome=1,
        source_event_ids=[event["id"]],
        entry_event_id=event["id"],
        landmark_window_ids=[],
        exclusion_reasons=[],
    )
    write(study / "evidence.json", dict(primary=[row]))
    write(
        study / "summary.json",
        dict(variants=dict(primary=dict(team_match_context=dict(shared_strata=[])))),
    )
    write(
        study / "source-inputs.json",
        [dict(match_id=1, events=str(raw), source_manifest_sha256="a" * 64)],
    )
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in study.iterdir()}
    write(study / "manifest.json", dict(files=files, protected_inputs={str(raw): raw_sha}))
    return study, raw


def test_preparation_preserves_raw_and_does_not_create_human_labels(tmp_path):
    study, raw = fixture(tmp_path)
    before = raw.read_bytes()
    dest = prepare(study, tmp_path / "packet")
    manifest = json.loads((dest / "manifest.json").read_text())
    assert manifest["participants"] == manifest["collected_labels"] == 0
    assert manifest["external_review_access_cleared"] is False
    assert raw.read_bytes() == before
    assert (dest / "source-only-adjudication/TASK_01.csv").read_bytes() == (
        dest / "conditions/TASK_01-ledger.csv"
    ).read_bytes()
    with (dest / "judgment-template.csv").open() as f:
        judges = list(csv.DictReader(f))
    assert all(not r["participant_id"] and not r["relevant_event_ids_json"] for r in judges)
    assert (dest / "private-design/case-map.json").exists()
    assert "machine_feature" not in (dest / "source-only-adjudication/TASK_01.csv").read_text()
    with pytest.raises(FileExistsError):
        prepare(study, dest)


def test_corrupt_raw_source_blocks_packet_before_output(tmp_path):
    study, raw = fixture(tmp_path)
    raw.write_text("changed")
    with pytest.raises(ValueError, match="provenance"):
        prepare(study, tmp_path / "absent")
    assert not (tmp_path / "absent").exists()
