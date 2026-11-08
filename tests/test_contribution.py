"""Each synthetic contribution observation resolves to its authored source action."""

from fil.intelligence.contribution import contribution_report
from fil.intelligence.scout_fixture import scout_fixture


def test_evidence_and_counter_evidence_are_traceable_and_bounded():
    result = contribution_report()
    events, meta, provenance = scout_fixture()
    source = {e["id"]: e for e in events}
    assert result["source"] == provenance
    assert result["fixture"]["score"] == [meta["home_score"], meta["away_score"]] == [0, 0]
    assert {c["name"] for c in result["candidates"]} == {"Mara Vale", "Tess Rowe"}
    mara = next(c for c in result["candidates"] if c["name"] == "Mara Vale")
    assert mara["transition_actions"]["count"] == 2
    assert mara["completed_build_up_passes"]["count"] == 4
    assert mara["incomplete_passes"] == {"count": 1, "event_ids": ["demo-scout-action-010"]}
    assert mara["recorded_goals"] == {"count": 0, "event_ids": []}
    assert mara["assists"] is None
    for candidate in result["candidates"]:
        for fact in ("transition_actions", "completed_build_up_passes", "incomplete_passes",
                     "recorded_goals"):
            assert candidate[fact]["count"] == len(candidate[fact]["event_ids"])
            assert all(source[event_id]["player"]["id"] == candidate["player_id"]
                       for event_id in candidate[fact]["event_ids"])
    assert "cannot support a claim" in result["limitations"][0]


def test_selection_requires_grounded_support_and_counter_evidence():
    import pytest

    from fil.intelligence.contribution import validate_selection

    report = contribution_report()
    valid = {"candidates": [{"player_id": 9101,
                             "support_event_ids": ["demo-scout-action-001",
                                                   "demo-scout-action-002"],
                             "opposing_event_ids": ["demo-scout-action-010"]}]}
    assert validate_selection(report, valid)[0]["player"]["name"] == "Mara Vale"
    assert validate_selection(report, {"candidates": []}) == []
    for item in (
        {**valid["candidates"][0], "support_event_ids": ["invented", "demo-scout-action-002"]},
        {**valid["candidates"][0], "support_event_ids": ["demo-scout-action-004",
                                                         "demo-scout-action-002"]},
        {**valid["candidates"][0], "opposing_event_ids": []},
        {**valid["candidates"][0], "player_id": 9999},
    ):
        with pytest.raises(ValueError):
            validate_selection(report, {"candidates": [item]})


def test_profiles_distinguish_recorded_actions_from_unavailable_off_ball():
    report = contribution_report()
    events, _, _ = scout_fixture()
    source = {e["id"]: e for e in events}
    assert {p["name"] for p in report["player_profiles"]} == {
        "Mara Vale", "Ivo Moss", "Tess Rowe"
    }
    ivo = next(p for p in report["player_profiles"] if p["name"] == "Ivo Moss")
    assert ivo["completed_build_up_passes"]["count"] == 2
    assert ivo["transition_actions"]["count"] == 0
    for p in report["player_profiles"]:
        assert p["attacking_off_ball"] is None and p["defending_off_ball"] is None
        assert p["other_defensive_actions"] is None
        for observation in p["observations"]:
            rows = [source[event_id] for event_id in observation["event_ids"]]
            assert all(e["player"]["id"] == p["player_id"] for e in rows)
            assert len({(e["period"], e["possession"]) for e in rows}) == (
                observation["distinct_recorded_possessions"]
            )


def test_repeated_actions_in_same_possession_do_not_become_multiple_episodes(monkeypatch):
    from copy import deepcopy

    from fil.intelligence import contribution

    events, meta, provenance = scout_fixture()
    events = deepcopy(events)
    events[5]["possession"] = events[0]["possession"]
    monkeypatch.setattr(contribution, "scout_fixture", lambda: (events, meta, provenance))
    report = contribution.contribution_report()
    mara = next(p for p in report["player_profiles"] if p["name"] == "Mara Vale")
    assert not any(o["type"] == "defensive_transition" for o in mara["observations"])


def test_build_up_specialist_can_be_selected_without_inventing_defensive_actions():
    from fil.intelligence.contribution import validate_selection

    choice = {"candidates": [{"player_id": 9102, "support_event_ids": ["demo-scout-action-003"],
                              "opposing_event_ids": []}]}
    result = validate_selection(contribution_report(), choice)
    assert result[0]["player"]["name"] == "Ivo Moss"
    assert result[0]["player"]["transition_actions"]["count"] == 0
