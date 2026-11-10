"""TEST ONLY involvement, exposure and native-link provenance contracts."""

import copy

import pyarrow as pa
import pytest

from fil.ingestion.statsbomb_tactics import extract_tactics
from fil.metrics.players import combine_matches, native_shot_links, player_facts
from fil.possessions.extract import reconstruct
from tests import test_possessions, test_tactics
from tests.test_tactics import score_table, uid

source_events = test_tactics.source_events
possession_events = test_possessions.possession_events


def facts(raw, selected_ids=None, roster=None):
    table = score_table(raw)
    selected = (
        table
        if selected_ids is None
        else table.filter(
            pa.array([i in selected_ids for i in table["event_id"].to_pylist()], type=pa.bool_())
        )
    )
    return player_facts(
        table, selected, reconstruct(table, 1, 2), extract_tactics(table, 1, 2), roster or []
    )


def add_link(raw):
    raw[2]["pass"]["assisted_shot_id"] = uid(4)
    raw[3].pop("pass")
    raw[3]["type"] = {"id": 16, "name": "Shot"}
    raw[3]["shot"] = {
        "type": {"id": 87, "name": "Open Play"},
        "outcome": {"id": 98, "name": "Off T"},
        "statsbomb_xg": 0.2,
        "key_pass_id": uid(3),
    }


def test_participation_original_ids(possession_events):
    rows = facts(possession_events).players.to_pylist()
    assert sum(r["selected_events"] for r in rows) == len(possession_events)
    assert sum(r["completed_passes"] for r in rows) == 5
    row = next(r for r in rows if r["player_id"] == 11)
    assert len(row["event_ids"]) == len(set(row["event_ids"]))
    assert row["minutes_played"] is None
    assert (
        row["owner_progressions_per100_actions"]
        == 100 * row["owner_progressive_actions"] / row["owner_actions"]
    )


def test_outside_filter_shot_context(possession_events):
    add_link(possession_events)
    row = next(
        r for r in facts(possession_events, {uid(3)}).players.to_pylist() if r["player_id"] == 11
    )
    assert row["event_ids"] == [uid(3)]
    assert row["native_shot_links"] == 1 and row["native_linked_shot_xg"] == 0.2
    assert row["linked_shot_ids"] == row["context_shot_ids"] == [uid(4)]
    assert row["pre_shot_action_ids"] == [uid(3)] and row["pre_shot_possessions"] == 1


@pytest.mark.parametrize("mode", ["one_sided", "reverse_order", "other_team", "shootout"])
def test_unsupported_links_audited(possession_events, mode):
    add_link(possession_events)
    if mode == "one_sided":
        possession_events[3]["shot"].pop("key_pass_id")
    table = score_table(possession_events)
    rows = table.to_pylist()
    if mode == "reverse_order":
        rows[3]["provider_index"] = 1
    if mode == "other_team":
        rows[3]["team_id"] = 2
    if mode == "shootout":
        rows[3]["period"] = 5
    links = native_shot_links(pa.Table.from_pylist(rows, schema=table.schema)).to_pylist()
    assert links[0]["status"] == "unverified" and links[0]["shot_xg"] is None


def test_empty_and_missing_exposure_nulls(possession_events):
    roster = [{"team_id": 1, "player_id": 99, "player_name": "TEST UNUSED", "positions": []}]
    result = facts(possession_events, set(), roster)
    row = next(r for r in result.players.to_pylist() if r["player_id"] == 99)
    assert row["owner_actions"] == 0 and row["selected_events"] == 0
    assert (
        row["known_pass_completion_fraction"] is None
        and row["owner_progressions_per100_actions"] is None
    )
    assert row["position_metadata"] is None and row["metadata_status"] == "position_unknown"
    assert all(r["minutes_played"] is None for r in result.players.to_pylist())


def test_metadata_and_multi_match_grain(possession_events):
    roster = [
        {
            "team_id": 1,
            "player_id": 11,
            "player_name": "TEST",
            "positions": [{"position": "TEST POSITION"}],
            "source_pointer": "TEST_ONLY.json#11",
        }
    ]
    one = facts(possession_events, roster=roster).players
    row = next(r for r in one.to_pylist() if r["player_id"] == 11)
    assert (
        row["metadata_status"] == "native_positions"
        and row["metadata_source_locator"] == "TEST_ONLY.json#11"
    )
    with pytest.raises(ValueError, match="Duplicate match"):
        combine_matches([one, one])
    rows = copy.deepcopy(one.to_pylist())
    for r in rows:
        r["match_id"] = 2
    two = pa.Table.from_pylist(rows, schema=one.schema)
    assert combine_matches([one, two]).num_rows == 2 * one.num_rows
    assert combine_matches([]).num_rows == 0
    with pytest.raises(ValueError, match="Duplicate roster"):
        facts(possession_events, roster=roster + roster)


def test_player_artifacts_immutable(possession_events, tmp_path, monkeypatch):
    from fil.explorer import player_data

    table = score_table(possession_events)
    meta = dict(
        home_team_id=1,
        away_team_id=2,
        match_id=1,
        source_manifest_sha256="e" * 64,
        score_manifest_sha256="f" * 64,
    )
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for p in config.values():
        from pathlib import Path

        Path(p).mkdir()
    monkeypatch.setattr(player_data, "load_match", lambda _: (table, meta))
    monkeypatch.setattr(player_data, "load_roster", lambda *args: [])
    folder = player_data.prepare(config, tmp_path / "out", "a" * 40)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    assert player_data.prepare(config, tmp_path / "out", "a" * 40) == folder
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    (folder / "players.parquet").write_bytes(b"TEST CORRUPTION")
    with pytest.raises(ValueError, match="recomputed"):
        player_data.prepare(config, tmp_path / "out", "a" * 40)
    with pytest.raises(ValueError, match="outside"):
        player_data.prepare(config, tmp_path / "raw" / "bad", "a" * 40)
