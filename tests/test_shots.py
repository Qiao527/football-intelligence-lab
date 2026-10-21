"""Independent TEST-ONLY expectations for source xG, domains, bins and shared filters."""

import copy
import json
import math
from pathlib import Path

import pyarrow as pa
import pytest

from fil.explorer import data
from fil.metrics.shots import (
    MatchFilter,
    MetricError,
    apply_filter,
    build_shots,
    cumulative,
    totals,
    window_threat,
)
from fil.time.clock import PeriodRange
from tests.test_score import clock, event


@pytest.fixture
def match():
    events = [
        event(1, 1, "00:00:00", "Half Start"),
        event(2, 1, "00:14:59.999", "Shot", 1),
        event(3, 1, "00:15:00", "Shot", 1, penalty=True),
        event(4, 1, "00:48:00", "Own Goal For", 1),
        event(5, 1, "00:48:00", "Half End"),
        event(6, 2, "00:00:00", "Half Start"),
        event(7, 2, "00:00:00", "Shot", 2),
        event(8, 2, "00:46:00", "Shot", 2, outcome="Saved"),
        event(9, 2, "00:46:00", "Half End"),
        event(10, 5, "00:00:00", "Shot", 1, penalty=True),
    ]
    for e, v in zip(
        [e for e in events if e["type"]["name"] == "Shot"], [0.1, 0.7, 0.2, 0.3, 0.9], strict=True
    ):
        e["shot"]["statsbomb_xg"] = v
        e["location"] = [110, 40]
    return clock(events)


def test_source_totals_penalties_shootout_and_own_goals(match):
    before = match.to_pylist()
    shots = build_shots(match)
    assert shots.num_rows == 4
    assert totals(shots, 1)["xg"] == math.fsum([0.1, 0.7])
    assert totals(shots, 1)["non_penalty_xg"] == 0.1
    assert totals(shots, 2)["xg"] == 0.5
    assert match.to_pylist() == before
    points = cumulative(shots)
    assert [r["cumulative_xg"] for r in points] == pytest.approx([0.1, 0.8, 0.2, 0.5], abs=1e-12)
    assert [r["event_id"] for r in points] == shots["event_id"].to_pylist()


@pytest.mark.parametrize("value", [None, -0.1, 1.1, float("nan"), float("inf")])
def test_missing_or_invalid_xg_blocks_publication(match, value):
    rows = match.to_pylist()
    rows[1]["shot_xg"] = value
    with pytest.raises(MetricError):
        build_shots(pa.Table.from_pylist(rows, schema=match.schema))


@pytest.mark.parametrize("width", [5, 10, 15])
def test_period_bins_partition_each_shot_once(match, width):
    windows = window_threat(match, (1, 2), width * 60000)
    ids = [i for w in windows for i in w["event_ids"]]
    assert len(ids) == len(set(ids)) == 4
    for team in (1, 2):
        assert math.isclose(
            math.fsum(w["xg"] for w in windows if w["team_id"] == team),
            totals(build_shots(match), team)["xg"],
        )
    first = next(
        w for w in windows if w["period"] == 1 and w["start_ms"] == 0 and w["team_id"] == 1
    )
    if width == 15:
        assert len(first["event_ids"]) == 1
    terminal = next(
        w for w in windows if w["period"] == 2 and w["include_terminal"] and w["team_id"] == 2
    )
    assert str(__import__("uuid").UUID(int=8)) in terminal["event_ids"]


def test_shared_filter_boundary_empty_and_null_location(match):
    selected = apply_filter(
        match, MatchFilter((PeriodRange(2, 0, 60000),), team_id=2, event_type="Shot")
    )
    assert selected.num_rows == 1 and selected["period"][0].as_py() == 2
    assert totals(build_shots(selected), 2)["xg"] == 0.2
    empty = build_shots(apply_filter(match, MatchFilter((PeriodRange(1, 0, 1000),))))
    assert totals(empty, 1)["xg"] == 0 and totals(empty, 1)["mean_xg"] is None
    rows = match.to_pylist()
    rows[1]["x"] = None
    assert build_shots(pa.Table.from_pylist(rows, schema=match.schema)).num_rows == 4


def test_duplicate_shot_ids_fail(match):
    with pytest.raises(MetricError):
        build_shots(pa.concat_tables([match, match]))


def test_filter_can_combine_period_team_player_and_outcome(match):
    state = MatchFilter((PeriodRange(1, 0, 2880000, True),), 1, 11, "Shot", "Goal")
    selected = apply_filter(match, state)
    assert selected.num_rows == 2
    assert len(set(selected["event_id"].to_pylist())) == 2


def test_filter_does_not_implicitly_include_shootout(match):
    with pytest.raises(ValueError):
        apply_filter(match, MatchFilter((PeriodRange(5, 0, 0, True),)))


def test_metric_artifact_reuse_and_corruption(match, tmp_path, monkeypatch):
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for p in config.values():
        Path(p).mkdir()
    meta = {
        "home_team_id": 1,
        "away_team_id": 2,
        "source_manifest_sha256": "a" * 64,
        "score_manifest_sha256": "b" * 64,
    }
    # Output adds only metrics; original 66 columns stay untouched.
    match = match.append_column("clock_manifest_sha256", pa.array(["c" * 64] * match.num_rows))
    monkeypatch.setattr(data, "load_match", lambda config: (match, copy.deepcopy(meta)))
    folder = data.prepare(config, tmp_path / "out", "a" * 40)
    snapshot = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    assert data.prepare(config, tmp_path / "out", "a" * 40) == folder
    assert snapshot == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    report = json.loads((folder / "quality.json").read_bytes())
    assert report["shots"] == 4 and report["shootout_excluded"] == 1
    (folder / "shots.parquet").write_bytes(b"BAD TEST DATA")
    with pytest.raises(ValueError):
        data.prepare(config, tmp_path / "out", "a" * 40)


def test_no_shots_has_typed_cumulative_and_null_mean(match):
    selected = apply_filter(match, MatchFilter((PeriodRange(1, 0, 1000),)))
    shots = build_shots(selected)
    assert cumulative(shots) == [] and totals(shots, 1)["mean_xg"] is None
    assert shots.schema.equals(match.schema)


@pytest.mark.parametrize("name,value", [("x", 121), ("y", -1), ("x", float("nan"))])
def test_invalid_coordinate_blocks_map(match, name, value):
    rows = match.to_pylist()
    rows[1][name] = value
    with pytest.raises(MetricError):
        build_shots(pa.Table.from_pylist(rows, schema=match.schema))


@pytest.mark.parametrize("mode", ["manifest", "extra", "symlink"])
def test_metric_bundle_rejects_tampering(match, tmp_path, monkeypatch, mode):
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for p in config.values():
        Path(p).mkdir()
    meta = {
        "home_team_id": 1,
        "away_team_id": 2,
        "source_manifest_sha256": "a" * 64,
        "score_manifest_sha256": "b" * 64,
    }
    match = match.append_column("clock_manifest_sha256", pa.array(["c" * 64] * match.num_rows))
    monkeypatch.setattr(data, "load_match", lambda config: (match, meta))
    folder = data.prepare(config, tmp_path / "out", "a" * 40)
    if mode == "manifest":
        path = folder / "manifest.json"
        body = json.loads(path.read_bytes())
        body["rights"] = "UNAPPROVED"
        path.write_text(json.dumps(body))
    elif mode == "extra":
        (folder / "unexpected").touch()
    else:
        path = folder / "quality.json"
        body = path.read_bytes()
        path.unlink()
        target = tmp_path / "outside"
        target.write_bytes(body)
        path.symlink_to(target)
    with pytest.raises(ValueError):
        data.prepare(config, tmp_path / "out", "a" * 40)


def test_metrics_cannot_write_inside_raw_bundle(match, tmp_path, monkeypatch):
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for p in config.values():
        Path(p).mkdir()
    monkeypatch.setattr(data, "load_match", lambda c: (match, {}))
    with pytest.raises(ValueError, match="immutable"):
        data.prepare(config, Path(config["raw"]) / "child", "a" * 40)
