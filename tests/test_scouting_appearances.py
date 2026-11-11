"""TEST_ONLY appearance export from canonical events, xG and lineup metadata."""

import json

import pytest

from fil.research.scouting_appearances import (
    appearance_rows,
    reconcile,
    stage_of,
    team_matchdays,
)


def match(match_id, day, stage="Group Stage", home=10, away=11):
    return {
        "match_id": match_id,
        "match_date": day,
        "competition_stage": stage,
        "home_team_id": home,
        "away_team_id": away,
    }


def group_matches():
    # Dates are deliberately not in match-id order.
    return [
        match(1, "2018-06-20"),
        match(2, "2018-06-14"),
        match(3, "2018-06-26"),
        match(4, "2018-07-01", stage="Round of 16"),
    ]


def ev(**overrides):
    row = {
        "event_id": "E1",
        "match_id": 1,
        "team_id": 10,
        "player_id": 100,
        "event_type": "Pass",
        "period": 1,
        "shot_xg": None,
        "shot_type": None,
        "shot_outcome": None,
        "source": "statsbomb_open_data",
    }
    row.update(overrides)
    return row


def shot(**overrides):
    base = dict(event_type="Shot", shot_xg=0.25, shot_type="Open Play",
                shot_outcome="Saved")
    base.update(overrides)
    return ev(**base)


def lineups():
    return [
        {"match_id": 1, "team_id": 10, "player_id": 100,
         "positions": [{"position": "Center Forward", "from": "00:00"}]},
        {"match_id": 2, "team_id": 10, "player_id": 100, "positions": []},
        {"match_id": 3, "team_id": 10, "player_id": 100,
         "positions": [{"position": "Left Wing", "from": "00:00"}]},
        {"match_id": 1, "team_id": 10, "player_id": 101,
         "positions": [{"position": "Center Forward", "from": "00:00"}]},
        {"match_id": 2, "team_id": 10, "player_id": 101,
         "positions": [{"position": "Center Forward", "from": "00:00"}]},
    ]


def test_stage_names_map_to_the_two_declared_windows():
    assert stage_of("Group Stage") == "group"
    assert stage_of("Round of 16") == "knockout"
    assert stage_of("Final") == "knockout"
    with pytest.raises(ValueError):
        stage_of(None)


def test_team_matchdays_follow_the_team_calendar():
    order = team_matchdays(group_matches())
    assert order[(2, 10)] == 1
    assert order[(1, 10)] == 2
    assert order[(3, 10)] == 3
    assert order[(4, 10)] is None
    assert order[(4, 11)] is None


def test_team_matchdays_reject_incomplete_or_duplicate_metadata():
    with pytest.raises(ValueError):
        team_matchdays(group_matches()[:2])
    with pytest.raises(ValueError):
        team_matchdays([*group_matches(), match(1, "2018-06-20")])
    with pytest.raises(ValueError):
        team_matchdays([{"match_id": 1}])


def test_shots_goals_and_penalty_split_are_source_facts():
    events = [
        shot(event_id="S1", shot_xg=0.4, shot_outcome="Goal"),
        shot(event_id="S2", shot_xg=0.1),
        shot(event_id="S3", shot_xg=0.8, shot_type="Penalty", shot_outcome="Goal"),
    ]
    result = appearance_rows(events, lineups(), group_matches())
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["shots"] == 3
    assert row["goals"] == 2
    assert row["xg"] == pytest.approx(1.3)
    assert row["npxg"] == pytest.approx(0.5)
    assert row["shot_event_ids"] == ["S1", "S2", "S3"]
    assert result["coverage"]["penalty_shots"] == 1


def test_shootout_is_excluded_from_every_total():
    events = [
        shot(event_id="S1", period=2, shot_xg=0.3),
        shot(event_id="S5", period=5, shot_xg=0.9, shot_outcome="Goal"),
    ]
    row = appearance_rows(events, lineups(), group_matches())["rows"][0]
    assert row["shots"] == 1
    assert row["goals"] == 0
    assert row["xg"] == pytest.approx(0.3)


def test_missing_or_invalid_source_xg_fails():
    with pytest.raises(ValueError):
        appearance_rows([shot(shot_xg=None)], lineups(), group_matches())
    with pytest.raises(ValueError):
        appearance_rows([shot(shot_xg=1.4)], lineups(), group_matches())
    with pytest.raises(ValueError):
        appearance_rows([shot(shot_xg=float("nan"))], lineups(), group_matches())


def test_unattributed_shot_blocks_by_default_and_is_reportable():
    events = [shot(event_id="S1", player_id=None)]
    with pytest.raises(ValueError):
        appearance_rows(events, lineups(), group_matches())
    result = appearance_rows(
        events, lineups(), group_matches(), strict_unattributed=False
    )
    assert result["unattributed_shot_ids"] == ["S1"]
    assert result["rows"] == []


def test_zero_shot_appearances_are_kept():
    events = [ev(event_id="P1"), ev(event_id="P2", match_id=2)]
    result = appearance_rows(events, lineups(), group_matches())
    assert len(result["rows"]) == 2
    assert all(row["shots"] == 0 for row in result["rows"])
    assert all(row["xg"] == 0.0 for row in result["rows"])
    assert result["coverage"]["zero_shot_appearances"] == 2


def test_position_metadata_is_verbatim_and_may_be_null():
    events = [ev(match_id=1), ev(match_id=2), ev(match_id=3)]
    rows = appearance_rows(events, lineups(), group_matches())["rows"]
    labels = [row["position_label"] for row in rows]
    assert labels[0] is None
    assert json.loads(labels[1]) == [{"from": "00:00", "position": "Center Forward"}]
    assert json.loads(labels[2]) == [{"from": "00:00", "position": "Left Wing"}]


def test_duplicate_lineup_identity_fails():
    doubled = lineups() + [
        {"match_id": 1, "team_id": 10, "player_id": 100, "positions": None}
    ]
    with pytest.raises(ValueError):
        appearance_rows([ev()], doubled, group_matches())


def test_rows_are_chronological_per_player():
    events = [ev(match_id=3, event_id="A"), ev(match_id=2, event_id="B"),
              ev(match_id=1, event_id="C")]
    rows = appearance_rows(events, lineups(), group_matches())["rows"]
    assert [row["match_id"] for row in rows] == [2, 1, 3]
    assert [row["team_matchday"] for row in rows] == [1, 2, 3]


def test_knockout_appearance_carries_no_group_matchday():
    events = [ev(match_id=4, player_id=100)]
    row = appearance_rows(events, lineups(), group_matches())["rows"][0]
    assert row["stage"] == "knockout"
    assert row["team_matchday"] is None


def test_unknown_match_and_bad_period_fail():
    with pytest.raises(ValueError):
        appearance_rows([ev(match_id=99)], lineups(), group_matches())
    with pytest.raises(ValueError):
        appearance_rows([ev(period=6)], lineups(), group_matches())


def test_reconcile_matches_verified_team_totals():
    events = [shot(event_id="S1", shot_xg=0.4, shot_outcome="Goal"),
              shot(event_id="S2", shot_xg=0.1)]
    rows = appearance_rows(events, lineups(), group_matches())["rows"]
    report = reconcile(rows, {(1, 10): {"shots": 2, "goals": 1, "xg": 0.5}})
    assert report["shots"] == 2
    assert report["match_teams"] == 1
    with pytest.raises(ValueError):
        reconcile(rows, {(1, 10): {"shots": 3, "goals": 1, "xg": 0.5}})
    with pytest.raises(ValueError):
        reconcile(rows, {(1, 10): {"shots": 2, "goals": 1, "xg": 0.9}})
    with pytest.raises(ValueError):
        reconcile(rows, {})


def test_rows_feed_the_reliability_stage_contract():
    from fil.research.scouting_task import reliability_pairs

    events = [
        shot(event_id="S1", match_id=1, shot_xg=0.2),
        shot(event_id="S2", match_id=2, shot_xg=0.3),
        shot(event_id="S3", match_id=1, player_id=101, shot_xg=0.6),
        shot(event_id="S4", match_id=2, player_id=101, shot_xg=0.7),
        shot(event_id="S5", match_id=3, player_id=101, shot_xg=0.9),
    ]
    rows = appearance_rows(events, lineups(), group_matches())["rows"]
    pairs = reliability_pairs(rows, "xg")
    assert pairs["n_pairs"] == 2
    assert pairs["single_appearance_players"] == 0
    # Chronological within player: matchday 1 value first, matchday 2 second.
    assert pairs["pairs"] == [(0.3, 0.2), (0.7, 0.6)]
    # Two pairs cannot support a correlation; the guard is deliberate.
    assert pairs["r_single"] is None
