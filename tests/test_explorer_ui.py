"""Offline TEST-ONLY Streamlit render and shared-filter interactions, no provider dataset."""

import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from fil.explorer import data
from fil.ingestion.statsbomb_score import scoring_signals
from fil.metrics.score import OfficialScore, reconstruct_score
from tests import test_score
from tests.test_score import clock

score_events = test_score.events


def test_shared_ui_filter_reset_and_empty_state(score_events, tmp_path, monkeypatch):
    for e in score_events:
        if e["type"]["name"] == "Shot":
            e["shot"]["statsbomb_xg"] = 0.2
            e["location"] = [110, 40]
    table, _, _ = reconstruct_score(
        clock(score_events),
        scoring_signals(score_events),
        OfficialScore(1, 1, 2, 2, 1),
        "a" * 40,
        "b" * 64,
    )
    meta = {
        "match_id": 1,
        "home_team_id": 1,
        "away_team_id": 2,
        "home_team_name": "TEST HOME",
        "away_team_name": "TEST AWAY",
        "home_score": 2,
        "away_score": 1,
        "competition_name": "TEST ONLY",
        "season_name": "TEST",
        "match_date": "2000-01-01",
        "source_revision": "a" * 40,
    }
    monkeypatch.setattr(data, "load_match", lambda c: (table, meta))
    config = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for path in config.values():
        Path(path).mkdir()
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("FIL_EXPLORER_CONFIG", str(path))
    app = AppTest.from_file(str(Path(data.__file__).with_name("app.py")), default_timeout=30).run()
    assert not app.exception
    assert [m.value for m in app.metric][:2] == ["9", "3"]
    app.selectbox(key="period_choice").select("Period 2").run()
    assert not app.exception and app.metric[0].value == "5"
    app.selectbox(key="team_choice").select(1).run()
    assert app.metric[1].value == "1"
    app.selectbox(key="type_choice").select("Own Goal Against").run()
    assert app.metric[0].value == "0" and app.metric[2].value == "0.000"
    assert any("No events in this selection" in msg.value for msg in app.info)
    app.button[0].click().run()
    assert not app.exception
    assert [m.value for m in app.metric][:2] == ["9", "3"]
    assert app.selectbox(key="event_choice").value == score_events[0]["id"]
    app.run()  # A later interaction/rerun must not resurrect the old frontend filters.
    assert [m.value for m in app.metric][:2] == ["9", "3"]
    assert app.selectbox(key="period_choice").value == "Full match"
    assert app.selectbox(key="team_choice").value is None
    assert app.selectbox(key="type_choice").value is None
