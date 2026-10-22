"""TEST ONLY player filter, metadata and exact evidence regression."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from fil.explorer import data, players
from tests import test_possessions, test_tactics
from tests.test_tactics import score_table

source_events = test_tactics.source_events
possession_events = test_possessions.possession_events


def test_player_view_shared_filters_and_evidence(possession_events, tmp_path, monkeypatch):
    table = score_table(possession_events)
    meta = {
        "home_team_id": 1,
        "away_team_id": 2,
        "home_team_name": "TEST HOME",
        "away_team_name": "TEST AWAY",
        "home_score": 1,
        "away_score": 0,
        "competition_name": "TEST",
        "season_name": "TEST",
        "match_date": "2000-01-01",
        "match_id": 1,
        "source_revision": "a" * 40,
        "source_manifest_sha256": "e" * 64,
    }
    monkeypatch.setattr(data, "load_match", lambda _: (table, meta))
    monkeypatch.setattr(players, "roster", lambda *args: [])
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for p in config.values():
        Path(p).mkdir()
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("FIL_EXPLORER_CONFIG", str(path))
    app = AppTest.from_file(str(Path(data.__file__).with_name("app.py")), default_timeout=30).run()
    app.selectbox(key="view_choice").select("Player Evidence").run()
    assert not app.exception and app.metric[6].value == "5"
    app.selectbox(key="player_evidence_choice").select("1:11").run()
    assert app.code[0].value == table["event_id"][0].as_py()
    app.selectbox(key="player_evidence_type").select("Progressive passes/carries").run()
    assert not app.exception and app.code[0].value in table["event_id"].to_pylist()
    app.selectbox(key="team_choice").select(2).run()
    assert not app.exception and app.selectbox(key="player_evidence_choice").value.startswith("2:")
    app.selectbox(key="type_choice").select("Own Goal For").run()
    assert any("No player actor" in i.value for i in app.info)
    app.button[0].click().run()
    assert not app.exception and app.metric[6].value == "5"
