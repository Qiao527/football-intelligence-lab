"""TEST-ONLY possession semantics, never observed fixture evidence."""

import copy
import math
from pathlib import Path

import pyarrow as pa
import pytest

from fil.possessions import artifacts
from fil.possessions.extract import process_summary, reconstruct, select_possessions
from tests import test_tactics
from tests.test_tactics import score_table, uid

source_events = test_tactics.source_events


@pytest.fixture
def possession_events(source_events):
    # Preserve TEST ONLY own-goal pair; assign explicit native labels.
    for i, e in enumerate(source_events):
        e["possession"] = 1 if i < 8 else 2 if i < 12 else 3
        e["possession_team"] = {"id": 1 if i < 8 else 2, "name": "TEST OWNER"}
    return source_events


def test_membership_order_opponent_events_and_zero_shot_nulls(possession_events):
    table = score_table(possession_events)
    original = table.to_pylist()
    f = reconstruct(table, 1, 2)
    assert table.to_pylist() == original
    assert f.actions.num_rows == len(possession_events)
    assert f.actions.schema.metadata[b"fil.progression_version"] == b"fil-progression-1"
    assert f.quality["native_action_version"] == "fil-tactics-1"
    rows = f.possessions.to_pylist()
    assert [r["possession_id"] for r in rows] == [1, 2, 3]
    assert rows[0]["event_ids"] == [uid(i) for i in range(1, 9)]
    assert rows[0]["opponent_events"] == 1
    assert rows[0]["end_reason"] == "period_boundary"
    assert rows[0]["shot_xg_sum"] == 0
    assert rows[0]["time_to_first_shot_seconds"] is None
    assert all(r["sequence"] == i + 1 for i, r in enumerate(f.actions.slice(0, 8).to_pylist()))
    assert rows[1]["event_ids"] == [uid(i) for i in range(9, 13)]
    assert uid(12) not in rows[1]["owner_action_ids"]  # acting team != owner


def test_filtered_cohort_keeps_original_chain_and_defensive_event(possession_events):
    table = score_table(possession_events)
    facts = reconstruct(table, 1, 2)
    selected = table.slice(4, 1)  # opponent's own goal record, same native possession
    rows = select_possessions(facts, selected).to_pylist()
    assert len(rows) == 1 and len(rows[0]["event_ids"]) == 8
    assert select_possessions(facts, table.slice(0, 0)).num_rows == 0
    summary = process_summary(facts.possessions.slice(0, 0))
    assert summary["xg_per_possession"] is None
    assert summary["p_shot_given_final_third"] is None
    assert summary["median_elapsed_to_shot_seconds"] is None


def test_backward_revisits_and_repeated_entries_are_not_erased(possession_events):
    possession_events[1]["location"] = [30, 40]
    possession_events[1]["pass"]["end_location"] = [85, 40]
    possession_events[2]["location"] = [85, 40]
    possession_events[2]["pass"]["end_location"] = [25, 40]
    possession_events[3]["location"] = [25, 40]
    possession_events[3]["pass"]["end_location"] = [85, 40]
    r = reconstruct(score_table(possession_events), 1, 2).possessions.to_pylist()[0]
    assert r["zone_path"][:4] == ["DEF", "ATT", "DEF", "ATT"]
    assert r["final_third_entries"] == 2
    assert r["actions_to_first_final_third"] == 1
    assert r["reached_final_third"]


def test_cross_period_native_id_is_not_split_or_given_continuous_time(possession_events):
    for e in possession_events[:10]:
        e["possession"] = 1
        e["possession_team"] = {"id": 1, "name": "TEST OWNER"}
    r = reconstruct(score_table(possession_events), 1, 2).possessions.to_pylist()[0]
    assert r["start_period"] == 1 and r["end_period"] == 2
    assert len(r["event_ids"]) == 10
    assert r["observed_span_seconds"] is None
    assert any("cross_period" in f for f in r["quality_flags"])


@pytest.mark.parametrize(
    "kind", ["missing", "inconsistent", "noncontiguous", "duplicate", "tampered"]
)
def test_integrity_failures_or_explicit_missing_labels(possession_events, kind):
    if kind == "missing":
        possession_events[1].pop("possession")
        f = reconstruct(score_table(possession_events), 1, 2)
        assert f.quality["unassigned_events"] == 1
        assert f.actions.to_pylist()[1]["role"] == "unassigned"
        return
    if kind == "inconsistent":
        possession_events[1]["possession_team"]["id"] = 2
    if kind == "noncontiguous":
        possession_events[9]["possession"] = 3
    table = score_table(possession_events)
    if kind == "duplicate":
        table = pa.concat_tables([table, table])
    if kind == "tampered":
        rows = table.to_pylist()
        rows[1]["possession_id"] = 99
        table = pa.Table.from_pylist(rows, schema=table.schema)
    with pytest.raises(ValueError):
        reconstruct(table, 1, 2)


@pytest.mark.parametrize(
    "outcome,expected,restart",
    [
        (None, False, False),
        ("Incomplete", True, False),
        ("Out", False, False),
        ("Incomplete", False, True),
    ],
)
def test_turnover_needs_explicit_loss_and_next_opponent_control(
    possession_events, outcome, expected, restart
):
    # A final pass with no later owner ball action, followed by opponent native ID.
    rows = possession_events
    rows[6]["possession"] = 2
    rows[6]["possession_team"] = {"id": 2, "name": "TEST OWNER"}
    rows[6]["team"] = {"id": 2, "name": "TEST OWNER"}
    if restart:
        rows[6]["pass"]["type"] = {"id": 67, "name": "Throw-in"}
    for e in rows[7:]:
        e["possession"] += 2
    for e in rows[4:6]:
        e["type"] = {"id": 17, "name": "Pressure"}
        e.pop("related_events", None)
    # Use fresh zero-goal score chain after removing the test own goal pair.
    rows[3]["pass"].pop("outcome", None)
    if outcome:
        rows[3]["pass"]["outcome"] = {"id": 9 if outcome == "Incomplete" else 75, "name": outcome}
    from fil.ingestion.statsbomb_adapter import to_canonical
    from fil.metrics.score import OfficialScore, reconstruct_score
    from fil.schema import SourceContext
    from fil.time.clock import derive_clock

    ctx = SourceContext(
        "statsbomb_open_data", "c" * 64, "d" * 40, "e" * 64, "a" * 40, 1, 2, 3, "data/events/1.json"
    )
    clock = derive_clock(to_canonical(rows, ctx), "a" * 40, "b" * 64)[0]
    table = reconstruct_score(clock, [], OfficialScore(1, 1, 2, 0, 0), "a" * 40, "b" * 64)[0]
    result = reconstruct(table, 1, 2).possessions.to_pylist()[0]
    assert result["turnover"] is expected
    if expected:
        assert result["end_reason"] == "turnover"
        assert uid(4) in result["boundary_evidence_ids"]
    elif outcome == "Out":
        assert result["end_reason"] == "out_of_play"


def test_missing_positions_and_explicit_null_outcomes_remain_unknown(possession_events):
    for i in (1, 2, 3, 6):
        possession_events[i].pop("location", None)
        possession_events[i]["pass"].pop("end_location", None)
    f = reconstruct(score_table(possession_events), 1, 2)
    r = f.possessions.to_pylist()[0]
    assert r["start_zone"] == "UNKNOWN"
    assert "missing_owner_positions" in r["quality_flags"]
    assert r["actions_to_first_final_third"] is None


def test_immutable_artifacts(possession_events, tmp_path, monkeypatch):
    table = score_table(possession_events)
    meta = {
        "home_team_id": 1,
        "away_team_id": 2,
        "source_manifest_sha256": "e" * 64,
        "score_manifest_sha256": "f" * 64,
    }
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for p in config.values():
        Path(p).mkdir()
    monkeypatch.setattr(artifacts, "load_match", lambda _: (table, copy.deepcopy(meta)))
    folder = artifacts.prepare(config, tmp_path / "out", "a" * 40)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    assert artifacts.prepare(config, tmp_path / "out", "a" * 40) == folder
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    (folder / "possessions.parquet").write_bytes(b"TEST CORRUPTION")
    with pytest.raises(ValueError, match="recomputed"):
        artifacts.prepare(config, tmp_path / "out", "a" * 40)
    with pytest.raises(ValueError, match="outside"):
        artifacts.prepare(config, tmp_path / "raw" / "bad", "a" * 40)


def test_shots_rebounds_and_shootout_metrics_are_separate(possession_events):
    # Replace two owner records by shots, keeping TEST ONLY official own-goal award.
    for i in (1, 2):
        possession_events[i]["location"] = [85 if i == 1 else 105, 40]
        possession_events[i]["type"] = {"id": 16, "name": "Shot"}
        possession_events[i].pop("pass", None)
        possession_events[i]["shot"] = {
            "type": {"id": 87, "name": "Open Play"},
            "outcome": {"id": 98, "name": "Off T"},
            "statsbomb_xg": 0.2,
        }
    f = reconstruct(score_table(possession_events), 1, 2)
    r = f.possessions.to_pylist()[0]
    assert r["shot_count"] == 2 and r["shot_xg_sum"] == 0.4
    assert not r["shot_ending"]  # later completed passes retain the sequence
    assert r["time_to_first_shot_seconds"] == 899.999
    assert process_summary(f.possessions)["timed_shot_possessions"] == 1
    summary = process_summary(f.possessions)
    assert summary["eligible_possessions"] == 3
    assert summary["shot_after_final_third_denominator"] == 1
    assert summary["p_shot_given_final_third"] == 1
    assert summary["p_box_given_final_third"] == 1
    assert summary["xg_per_possession"] == pytest.approx(0.4 / 3)


def test_arrow_batch_preserves_directed_geometry(possession_events):
    import plotly.graph_objects as go

    from fil.explorer.tactical import network_figure
    from fil.ingestion.statsbomb_tactics import extract_tactics

    f = extract_tactics(score_table(possession_events), 1, 2)
    fig = network_figure(f.edges, f.nodes, 1, "TEST", "blue", lambda *args: go.Figure())
    nodes = {r["player_id"]: r for r in f.nodes.to_pylist() if r["team_id"] == 1}
    trace = next(t for t in fig.data if t.name == "Directed arrowheads")
    arrows = list(zip(trace.x, trace.y, trace.marker.angle, trace.customdata, strict=True))
    assert not fig.layout.annotations
    assert trace.marker.symbol == "triangle-up"
    expected = [
        e
        for e in f.edges.to_pylist()
        if e["team_id"] == 1
        and all(nodes[e[k]]["x"] is not None for k in ("passer_id", "recipient_id"))
        and (nodes[e["passer_id"]]["x"], nodes[e["passer_id"]]["y"])
        != (nodes[e["recipient_id"]]["x"], nodes[e["recipient_id"]]["y"])
    ]
    assert len(arrows) == len(expected)
    for (x, y, angle, custom), edge in zip(arrows, expected, strict=True):
        a, b = nodes[edge["passer_id"]], nodes[edge["recipient_id"]]
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
        length = math.hypot(dx, dy)
        assert x == pytest.approx(a["x"] - dy / length * 0.7 + 0.8 * dx)
        assert y == pytest.approx(a["y"] + dx / length * 0.7 + 0.8 * dy)
        # Plotly triangle-up angle is clockwise from screen-up; native y is down.
        assert math.sin(math.radians(angle)) * dx - math.cos(math.radians(angle)) * dy > 0
        assert custom[0] == f"edge:1:{edge['passer_id']}:{edge['recipient_id']}"


def test_restart_is_not_open_play_turnover(possession_events):
    # A new native ID for the same team is preserved even with consecutive restarts.
    possession_events[1]["pass"]["type"] = {"id": 67, "name": "Throw-in"}
    r = reconstruct(score_table(possession_events), 1, 2).possessions.to_pylist()[0]
    assert r["start_reason"] == "native_restart:Throw-in"
    assert not r["turnover"]


def test_missing_owner_labels_and_shootout_are_retained_not_imputed(possession_events):
    for e in possession_events:
        e["possession_team"] = None
    facts = reconstruct(score_table(possession_events), 1, 2)
    assert all(
        r["possession_team_id"] is None and r["owner_actions"] == 0
        for r in facts.possessions.to_pylist()
    )
    assert all(r["role"] == "unknown_owner_context" for r in facts.actions.to_pylist())
    assert all(r["shot_xg_sum"] is None for r in facts.possessions.to_pylist())
    assert process_summary(facts.possessions)["eligible_possessions"] == 0


def test_shootout_action_excluded_from_process_counts(possession_events):
    from tests.test_tactics import action

    possession_events.append(action(18, 5, "00:00:00"))
    possession_events[-1]["possession"] = 4
    possession_events[-1]["possession_team"] = {"id": 1, "name": "TEST OWNER"}
    r = reconstruct(score_table(possession_events), 1, 2).possessions.to_pylist()[-1]
    assert r["event_ids"] == [uid(18)] and r["owner_actions"] == 0
    assert r["shot_count"] == r["completed_passes"] == r["carries"] == 0
    assert any("shootout" in flag for flag in r["quality_flags"])


@pytest.mark.parametrize("kind", ["extra", "symlink", "manifest"])
def test_possession_artifact_rejects_tampering(possession_events, tmp_path, monkeypatch, kind):
    table = score_table(possession_events)
    meta = {
        "home_team_id": 1,
        "away_team_id": 2,
        "source_manifest_sha256": "e" * 64,
        "score_manifest_sha256": "f" * 64,
    }
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for p in config.values():
        Path(p).mkdir()
    monkeypatch.setattr(artifacts, "load_match", lambda _: (table, meta))
    folder = artifacts.prepare(config, tmp_path / "out", "b" * 40)
    if kind == "extra":
        (folder / "extra").mkdir()
    elif kind == "manifest":
        (folder / "manifest.json").write_text("{}")
    else:
        (folder / "quality.json").unlink()
        (folder / "quality.json").symlink_to(tmp_path / "missing")
    with pytest.raises((ValueError, KeyError)):
        artifacts.prepare(config, tmp_path / "out", "b" * 40)


def test_own_goal_not_turnover(possession_events):
    possession_events[3].pop("pass")
    possession_events[3]["type"] = {"id": 3, "name": "Dispossessed"}
    possession_events[6]["possession"] = 2
    for e in possession_events[7:]:
        e["possession"] += 2
    possession_events[6]["possession_team"] = {"id": 2, "name": "TEST OWNER"}
    result = reconstruct(score_table(possession_events), 1, 2).possessions.to_pylist()[0]
    assert result["end_reason"] == "own_goal_recorded" and not result["turnover"]
    assert {uid(5), uid(6)} <= set(result["boundary_evidence_ids"])


def test_foul_terminal_evidence_survives_context(possession_events):
    possession_events[6].pop("pass")
    possession_events[6]["type"] = {"id": 21, "name": "Foul Won"}
    possession_events[7]["type"] = {"id": 40, "name": "Camera off"}
    result = reconstruct(score_table(possession_events), 1, 2).possessions.to_pylist()[0]
    assert uid(7) in result["boundary_evidence_ids"]


@pytest.mark.parametrize("dx,dy", [(10, 0), (0, 10), (-10, 0), (0, -10), (10, 10), (-10, -10)])
def test_arrowhead_cardinal_and_diagonal_orientation(dx, dy):
    import plotly.graph_objects as go

    from fil.explorer.tactical import network_figure

    nodes = pa.Table.from_pylist(
        [
            dict(
                team_id=1,
                player_id=i,
                player_name=f"TEST {i}",
                x=x,
                y=y,
                sent=1,
                received=1,
                sample_count=1,
            )
            for i, x, y in [(11, 60.0, 40.0), (12, 60.0 + dx, 40.0 + dy)]
        ]
    )
    edges = pa.Table.from_pylist([dict(team_id=1, passer_id=11, recipient_id=12, weight=1)])
    fig = network_figure(edges, nodes, 1, "TEST", "blue", lambda *args: go.Figure())
    arrow = next(t for t in fig.data if t.name == "Directed arrowheads")
    angle = math.radians(arrow.marker.angle[0])
    assert math.sin(angle) == pytest.approx(dx / math.hypot(dx, dy), abs=1e-12)
    assert -math.cos(angle) == pytest.approx(dy / math.hypot(dx, dy), abs=1e-12)
    assert arrow.customdata[0][0] == "edge:1:11:12"
