"""TEST-ONLY shared-filter context, exact evidence and reset regression checks."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from fil.explorer import data
from tests import test_possessions, test_tactics
from tests.test_tactics import score_table, uid

source_events = test_tactics.source_events
possession_events = test_possessions.possession_events


def test_possession_context_drilldown_empty_and_reset(possession_events, tmp_path, monkeypatch):
    table = score_table(possession_events)
    meta = {
        "home_team_id": 1,
        "away_team_id": 2,
        "home_team_name": "TEST HOME",
        "away_team_name": "TEST AWAY",
        "home_score": 1,
        "away_score": 0,
        "competition_name": "TEST ONLY",
        "season_name": "TEST",
        "match_date": "2000-01-01",
        "match_id": 1,
        "source_revision": "a" * 40,
    }
    monkeypatch.setattr(data, "load_match", lambda _: (table, meta))
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for p in config.values():
        Path(p).mkdir()
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("FIL_EXPLORER_CONFIG", str(path))
    app = AppTest.from_file(str(Path(data.__file__).with_name("app.py")), default_timeout=30).run()
    app.selectbox(key="view_choice").select("Possession Flow").run()
    assert not app.exception and app.metric[4].value == "3"
    app.selectbox(key="possession_choice").select(2).run()
    app.selectbox(key="possession_event").select(uid(12)).run()
    assert app.code[0].value == uid(12)
    # A single matching opponent record selects its full native chain.
    app.selectbox(key="type_choice").select("Own Goal Against").run()
    assert not app.exception and app.metric[0].value == "1" and app.metric[4].value == "1"
    assert app.selectbox(key="possession_choice").value == 1
    assert len(app.selectbox(key="possession_event").options) == 8
    assert app.code[0].value == uid(1)
    app.selectbox(key="score_choice").select("leading").run()
    assert any("No native possession matches" in i.value for i in app.info)
    app.button[0].click().run()
    assert not app.exception and app.metric[4].value == "3"
    assert app.selectbox(key="view_choice").value == "Possession Flow"
    assert app.selectbox(key="possession_choice").value == 1
    app.selectbox(key="view_choice").select("Match Explorer").run()
    assert not app.exception and app.metric[0].value == "17"
