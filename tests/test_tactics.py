"""TEST-ONLY tactical contracts; synthetic events are never real-match evidence."""

import copy
from uuid import UUID

import pyarrow as pa
import pytest

from fil.explorer import tactical_data
from fil.ingestion.statsbomb_adapter import to_canonical
from fil.ingestion.statsbomb_score import scoring_signals
from fil.ingestion.statsbomb_tactics import extract_tactics
from fil.metrics.score import OfficialScore, reconstruct_score
from fil.metrics.shots import MatchFilter, apply_filter, event_score_state
from fil.metrics.tactics import (
    ACTION_SCHEMA,
    EDGE_SCHEMA,
    NODE_SCHEMA,
    TacticalError,
    compare,
    completed_passes,
    passing_network,
    select_actions,
)
from fil.schema import SourceContext
from fil.time.clock import PeriodRange, derive_clock
from tests.test_score import event


def uid(n):
    return str(UUID(int=n))


def action(n, period, stamp, team=1, kind="Pass"):
    row = event(n, period, stamp, kind, team)
    row["type"]["id"] = 30 if kind == "Pass" else 43
    row["location"] = [30, 40]
    row[kind.lower()] = {"end_location": [50, 40]}
    if kind == "Pass":
        row["pass"].update(
            {
                "recipient": {"id": 12 if team == 1 else 22, "name": "TEST RECEIVER"},
                "length": 20,
                "angle": 0,
                "height": {"id": 1, "name": "Ground Pass"},
            }
        )
    return row


@pytest.fixture
def source_events():
    rows = [
        event(1, 1, "00:00:00", "Half Start"),
        action(2, 1, "00:14:59.999"),
        action(3, 1, "00:15:00"),
        action(4, 1, "00:15:00"),
        event(5, 1, "00:18:00", "Own Goal Against", 2),
        event(6, 1, "00:18:00", "Own Goal For", 1),
        action(7, 1, "00:48:00"),
        event(8, 1, "00:48:00", "Half End"),
        event(9, 2, "00:00:00", "Half Start"),
        action(10, 2, "00:00:00", 2, "Carry"),
        action(11, 2, "00:00:00", 2),
        action(12, 2, "00:01:00"),
        action(13, 2, "00:02:00"),
        action(14, 2, "00:03:00"),
        action(15, 2, "00:04:00"),
        action(16, 2, "00:05:00", 2),
        event(17, 2, "00:46:00", "Half End"),
    ]
    rows[3]["player"]["id"] = 12
    rows[3]["pass"]["recipient"]["id"] = 11
    rows[4]["related_events"] = [uid(6)]
    rows[5]["related_events"] = [uid(5)]
    rows[10]["pass"]["outcome"] = {"id": 9, "name": "Incomplete"}
    rows[11]["pass"].pop("recipient")
    rows[12]["pass"]["outcome"] = None
    rows[13]["pass"]["outcome"] = {"id": 77, "name": "Unknown"}
    rows[14]["pass"].pop("length")
    rows[15].pop("location")
    rows[15]["pass"].pop("end_location")
    return rows


def score_table(rows):
    context = SourceContext(
        "statsbomb_open_data", "c" * 64, "d" * 40, "e" * 64, "a" * 40, 1, 2, 3, "data/events/1.json"
    )
    canonical = to_canonical(rows, context)
    clock = derive_clock(canonical, "a" * 40, "b" * 64)[0]
    return reconstruct_score(
        clock, scoring_signals(rows), OfficialScore(1, 1, 2, 1, 0), "a" * 40, "b" * 64
    )[0]


def test_completed_definition_audit_and_directed_unique_edges(source_events):
    table = score_table(source_events)
    original = table.to_pylist()
    facts = extract_tactics(table, 1, 2)
    assert table.to_pylist() == original
    assert set(completed_passes(facts.actions)["event_id"].to_pylist()) == {
        uid(n) for n in (2, 3, 4, 7, 16)
    }
    audit = {r["event_id"]: r for r in facts.actions.to_pylist()}
    assert audit[uid(12)]["reason"] == "missing_or_invalid_recipient"
    assert audit[uid(13)]["status"] == "unknown"  # Explicit null is not absent.
    assert audit[uid(14)]["status"] == "unknown"
    assert audit[uid(15)]["reason"] == "unsupported_pass_contract"
    assert audit[uid(11)]["status"] == "failed"
    edges = {(e["team_id"], e["passer_id"], e["recipient_id"]): e for e in facts.edges.to_pylist()}
    assert edges[1, 11, 12]["event_ids"] == [uid(2), uid(3), uid(7)]
    assert edges[1, 12, 11]["weight"] == 1
    assert sum(e["weight"] for e in edges.values()) == 5
    assert facts.actions.schema.equals(ACTION_SCHEMA)


def test_period_ties_stoppage_and_empty_windows(source_events):
    table = score_table(source_events)
    facts = extract_tactics(table, 1, 2)
    first = apply_filter(table, MatchFilter((PeriodRange(1, 0, 900000),)))
    assert completed_passes(select_actions(facts.actions, first))["event_id"].to_pylist() == [
        uid(2)
    ]
    ties = apply_filter(table, MatchFilter((PeriodRange(1, 900000, 900001),)))
    assert completed_passes(select_actions(facts.actions, ties))["event_id"].to_pylist() == [
        uid(3),
        uid(4),
    ]
    last = apply_filter(table, MatchFilter((PeriodRange(1, 2880000, 2880000, True),)))
    assert completed_passes(select_actions(facts.actions, last))["event_id"].to_pylist() == [uid(7)]
    empty = apply_filter(table, MatchFilter((PeriodRange(2, 1, 2),)))
    edges, nodes = passing_network(select_actions(facts.actions, empty))
    assert edges.num_rows == nodes.num_rows == 0
    assert edges.schema.equals(EDGE_SCHEMA) and nodes.schema.equals(NODE_SCHEMA)


def test_positions_are_pass_origins_only_and_unplaced_receivers_remain(source_events):
    facts = extract_tactics(score_table(source_events), 1, 2)
    nodes = {(r["team_id"], r["player_id"]): r for r in facts.nodes.to_pylist()}
    assert nodes[1, 11]["position_event_ids"] == [uid(2), uid(3), uid(7)]
    assert nodes[1, 11]["x"] == 30
    assert nodes[2, 12]["x"] is None and nodes[2, 22]["x"] is None
    assert nodes[2, 22]["received"] == 1


@pytest.mark.parametrize(
    "outcome", [None, {}, {"id": 8, "name": "Complete"}, {"id": 9, "name": "Unknown"}]
)
def test_only_native_absence_means_completion(source_events, outcome):
    source_events[1]["pass"]["outcome"] = outcome
    if outcome == {}:
        with pytest.raises(ValueError, match="outcome.id"):
            score_table(source_events)  # The upstream schema already rejects malformed objects.
        return
    facts = extract_tactics(score_table(source_events), 1, 2)
    assert uid(2) not in completed_passes(facts.actions)["event_id"].to_pylist()


@pytest.mark.parametrize("field", ["recipient", "length", "angle", "height"])
def test_missing_contract_fields_never_create_edges(source_events, field):
    source_events[1]["pass"].pop(field)
    facts = extract_tactics(score_table(source_events), 1, 2)
    assert uid(2) not in completed_passes(facts.actions)["event_id"].to_pylist()


@pytest.mark.parametrize(
    "start,end,expected",
    [
        ([30, 40], [40, 40], True),
        ([30, 40], [39.999, 40], False),
        ([30, 40], [20, 40], False),
        ([30, 40], [30, 60], False),
        (None, [50, 40], None),
        ([30, 40], None, None),
        ([30, 40], [121, 40], None),
    ],
)
def test_progression_boundaries_and_unsupported_endpoints(source_events, start, end, expected):
    source_events[1]["location"] = start
    source_events[1]["pass"]["end_location"] = end
    facts = extract_tactics(score_table(source_events), 1, 2)
    row = next(r for r in facts.actions.to_pylist() if r["event_id"] == uid(2))
    assert row["progressive"] is expected


def test_native_pi_rounding_keeps_a_supported_pass(source_events):
    source_events[1]["pass"]["angle"] = 3.1415927
    assert (
        uid(2)
        in completed_passes(extract_tactics(score_table(source_events), 1, 2).actions)[
            "event_id"
        ].to_pylist()
    )


def test_score_states_use_acting_team_and_pre_event_own_goal_state(source_events):
    table = score_table(source_events)
    by_id = {r["event_id"]: r for r in table.to_pylist()}
    assert event_score_state(by_id[uid(5)], 1, 2) == "level"
    assert event_score_state(by_id[uid(6)], 1, 2) == "leading"
    assert event_score_state(by_id[uid(10)], 1, 2) == "trailing"
    state = MatchFilter(
        (PeriodRange(1, 0, 2880000, True), PeriodRange(2, 0, 2760000, True)),
        score_state="trailing",
        home_team_id=1,
        away_team_id=2,
    )
    selected = apply_filter(table, state)
    assert uid(10) in selected["event_id"].to_pylist()
    assert uid(2) not in selected["event_id"].to_pylist()
    facts = extract_tactics(table, 1, 2)
    rows = compare(table, facts.actions, (1, 2), [("trailing", state)]).to_pylist()
    assert next(r for r in rows if r["team_id"] == 1)["completed_passes"] == 0


def test_duplicate_ids_and_source_tampering_fail(source_events):
    table = score_table(source_events)
    with pytest.raises(TacticalError, match="Duplicate"):
        extract_tactics(pa.concat_tables([table, table]), 1, 2)
    rows = table.to_pylist()
    rows[1]["recipient_player_id"] = 999
    with pytest.raises(TacticalError, match="Recipient"):
        extract_tactics(pa.Table.from_pylist(rows, schema=table.schema), 1, 2)


def test_artifacts_reuse_corruption_and_input_protection(source_events, tmp_path, monkeypatch):
    table = score_table(source_events)
    meta = {
        "home_team_id": 1,
        "away_team_id": 2,
        "source_manifest_sha256": "e" * 64,
        "score_manifest_sha256": "f" * 64,
    }
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for path in config.values():
        from pathlib import Path

        Path(path).mkdir()
    monkeypatch.setattr(tactical_data, "load_match", lambda _: (table, copy.deepcopy(meta)))
    output = tactical_data.prepare(config, tmp_path / "out", "a" * 40)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()}
    assert tactical_data.prepare(config, tmp_path / "out", "a" * 40) == output
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in output.iterdir()}
    (output / "edges.parquet").write_bytes(b"CORRUPT TEST ONLY")
    with pytest.raises(ValueError, match="recomputed"):
        tactical_data.prepare(config, tmp_path / "out", "a" * 40)
    with pytest.raises(ValueError, match="outside immutable"):
        tactical_data.prepare(config, tmp_path / "raw" / "bad", "a" * 40)


def test_invalid_score_filter_rejected(source_events):
    with pytest.raises(ValueError, match="official teams"):
        apply_filter(
            score_table(source_events),
            MatchFilter((PeriodRange(1, 0, 1000),), score_state="leading"),
        )


@pytest.mark.parametrize("actor", [None, {"id": 0, "name": "TEST INVALID"}])
def test_null_or_invalid_actor_remains_auditable_but_excluded(source_events, actor):
    source_events[1]["player"] = actor
    facts = extract_tactics(score_table(source_events), 1, 2)
    row = next(r for r in facts.actions.to_pylist() if r["event_id"] == uid(2))
    assert row["status"] == "excluded"
    assert row["reason"] == "missing_or_invalid_actor"
    assert uid(2) not in completed_passes(facts.actions)["event_id"].to_pylist()


def test_shootout_pass_excluded_and_unsupported_carry_outcome_is_unknown(source_events):
    source_events.append(action(18, 5, "00:00:00"))
    source_events[9]["carry"]["outcome"] = {"id": 999, "name": "Unsupported"}
    facts = extract_tactics(score_table(source_events), 1, 2)
    rows = {r["event_id"]: r for r in facts.actions.to_pylist()}
    assert rows[uid(18)]["reason"] == "outside_match_play"
    assert rows[uid(10)]["status"] == "unknown"
    assert rows[uid(10)]["progressive"] is None


@pytest.mark.parametrize("mode", ["manifest", "extra", "symlink"])
def test_tactical_artifact_rejects_tampering(source_events, tmp_path, monkeypatch, mode):
    import json
    from pathlib import Path

    table = score_table(source_events)
    meta = {
        "home_team_id": 1,
        "away_team_id": 2,
        "source_manifest_sha256": "e" * 64,
        "score_manifest_sha256": "f" * 64,
    }
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for p in config.values():
        Path(p).mkdir()
    monkeypatch.setattr(tactical_data, "load_match", lambda _: (table, meta))
    folder = tactical_data.prepare(config, tmp_path / "out", "a" * 40)
    if mode == "extra":
        (folder / "unexpected").mkdir()
    elif mode == "manifest":
        path = folder / "manifest.json"
        body = json.loads(path.read_bytes())
        body["rights"] = "BAD"
        path.write_text(json.dumps(body))
    else:
        path = folder / "quality.json"
        target = tmp_path / "outside"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
    with pytest.raises(ValueError):
        tactical_data.prepare(config, tmp_path / "out", "a" * 40)
