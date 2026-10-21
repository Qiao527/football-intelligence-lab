"""TEST-ONLY shared UI contracts; no provider dataset in CI."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from fil.explorer import data
from tests import test_tactics
from tests.test_tactics import score_table, uid

source_events = test_tactics.source_events


def test_tactical_filters_context_and_exact_edge_drilldown(source_events, tmp_path, monkeypatch):
    table = score_table(source_events)
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
    for path in config.values():
        Path(path).mkdir()
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("FIL_EXPLORER_CONFIG", str(path))
    app = AppTest.from_file(str(Path(data.__file__).with_name("app.py")), default_timeout=30).run()
    app.selectbox(key="view_choice").select("Tactical Dashboard").run()
    assert not app.exception
    assert app.metric[4].value == "5" and app.metric[5].value == "3"
    app.selectbox(key="tactical_entity").select("edge:1:11:12").run()
    assert app.selectbox(key="tactical_event").options[0].endswith(uid(2))
    assert app.code[0].value == uid(2)
    assert len(app.selectbox(key="tactical_event").options) == 3
    app.selectbox(key="team_choice").select(2).run()
    assert not app.exception and app.metric[4].value == "1"
    assert app.selectbox(key="tactical_entity").value == "all"
    app.selectbox(key="score_choice").select("leading").run()
    assert not app.exception and app.metric[4].value == "0"
    assert any("No pass/carry evidence" in x.value for x in app.info)
    app.selectbox(key="score_choice").select("trailing").run()
    assert app.metric[4].value == "1" and app.metric[7].value == "1"
    app.selectbox(key="tactical_comparison").select("Score states").run()
    assert not app.exception
    app.button[0].click().run()
    assert app.selectbox(key="view_choice").value == "Tactical Dashboard"
    assert app.metric[4].value == "5"
    app.selectbox(key="tactical_entity").select("edge:1:11:12").run()
    app.selectbox(key="tactical_event").select(uid(7)).run()
    app.button[0].click().run()
    assert app.selectbox(key="tactical_entity").value == "all"
    assert app.code[0].value == uid(2)
    app.selectbox(key="tactical_comparison").select("Two explicit windows").run()
    assert not app.exception
