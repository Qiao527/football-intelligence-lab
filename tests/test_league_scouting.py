"""TEST_ONLY league windows, appearance rows and the stage A decision."""

import pytest

from fil.research.league_scouting import (
    build_rows,
    consecutive_pairs,
    included_players,
    position_change_fraction,
    spearman_brown,
    stage_a,
    team_windows,
)


def match(match_id, day, home=10, away=11):
    return {"match_id": match_id, "match_date": day,
            "home_team_id": home, "away_team_id": away}


def fixtures(n=10, team=10, other=11):
    days = [f"2015-08-{d:02d}" for d in range(1, 31, 3)]
    rows = []
    for i in range(n):
        home, away = (team, other) if i % 2 == 0 else (other, team)
        rows.append(match(100 + i, days[i], home, away))
    return rows


def test_windows_split_each_team_fixture_list():
    windows = team_windows(fixtures(10))
    a = [k for k, v in windows.items() if v["window"] == "A"]
    assert len(a) == 10  # five per team
    assert windows[(100, 10)]["fixture_index"] == 0
    assert windows[(109, 10)]["window"] == "B"
    assert windows[(108, 10)]["window"] == "B"


def test_odd_fixture_count_goes_to_the_observation_window():
    windows = team_windows(fixtures(9))
    team_a = [k for k, v in windows.items() if k[1] == 10 and v["window"] == "A"]
    assert len(team_a) == 5


def test_windows_reject_duplicates_and_empty_input():
    with pytest.raises(ValueError):
        team_windows(fixtures(2) + [match(100, "2015-08-01")])
    with pytest.raises(ValueError):
        team_windows([])


def event(**overrides):
    row = {
        "event_id": "E1",
        "match_id": 100,
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
    base = dict(event_type="Shot", shot_xg=0.2, shot_type="Open Play", shot_outcome="Saved")
    base.update(overrides)
    return event(**base)


def test_rows_aggregate_shots_and_keep_windows():
    windows = team_windows(fixtures(10))
    events = [shot(event_id="S1", shot_xg=0.3),
              shot(event_id="S2", shot_xg=0.6, shot_outcome="Goal"),
              shot(event_id="S3", shot_xg=0.9, shot_type="Penalty", shot_outcome="Goal")]
    rows = build_rows(events, [], windows)
    assert len(rows) == 1
    row = rows[0]
    assert (row["shots"], row["goals"]) == (3, 2)
    assert row["xg"] == pytest.approx(1.8)
    assert row["npxg"] == pytest.approx(0.9)
    assert row["window"] == "A"
    assert row["match_date"] == "2015-08-01"


def test_rows_exclude_shootout_and_reject_bad_xg():
    windows = team_windows(fixtures(10))
    rows = build_rows([shot(period=5, shot_xg=0.9)], [], windows)
    assert rows == []
    for bad in (None, 1.5, float("nan")):
        with pytest.raises(ValueError):
            build_rows([shot(shot_xg=bad)], [], windows)


def test_rows_reject_unknown_team():
    windows = team_windows(fixtures(10))
    with pytest.raises(ValueError):
        build_rows([event(team_id=99)], [], windows)


def rows_for(n_players=6, spread=0.05):
    """Five window-A and five window-B appearances per player, adjacent values alike."""
    windows = team_windows(fixtures(10))
    out = []
    for p in range(n_players):
        base = 0.1 + p * 0.2
        for i in range(10):
            mid = 100 + i
            out.append({
                "source": "statsbomb_open_data", "match_id": mid, "team_id": 10,
                "player_id": 100 + p, "match_date": windows[(mid, 10)]["match_date"],
                "window": windows[(mid, 10)]["window"],
                "fixture_index": windows[(mid, 10)]["fixture_index"],
                "position_label": '["Center Forward"]',
                "position_names": ("Center Forward",),
                "shots": 1, "goals": 0,
                "xg": base + (i % 2) * spread, "npxg": base,
            })
    return out


def test_included_players_needs_both_windows():
    rows = rows_for()
    universe = included_players(rows)
    assert universe["players"]
    assert universe["median_appearances_a"] == 5
    rows.append({**rows[0], "match_id": 200, "player_id": 999, "window": "A",
                 "fixture_index": 9})
    assert len(included_players(rows)["players"]) == len(universe["players"])


def test_consecutive_pairs_use_window_a_only():
    rows = rows_for(3)
    players = included_players(rows)["players"]
    pairs = consecutive_pairs(rows, "xg", players)
    assert len(pairs) == 3
    assert all(len(v) == 2 for v in pairs.values())
    with pytest.raises(ValueError):
        consecutive_pairs(rows, "height", players)


def test_spearman_brown_accepts_fractional_counts():
    assert spearman_brown(0.5, 2) == pytest.approx(2 / 3)
    assert spearman_brown(0.36, 19) == pytest.approx(19 * 0.36 / (1 + 18 * 0.36))
    with pytest.raises(ValueError):
        spearman_brown(0.5, 0.5)


def test_position_change_detects_verbatim_difference():
    rows = rows_for(3)
    assert position_change_fraction(rows, included_players(rows)["players"]) == 0.0
    for row in rows:
        if row["player_id"] == 100 and row["window"] == "B":
            row["position_label"] = '["Left Wing"]'
            row["position_names"] = ("Left Wing",)
    assert position_change_fraction(rows, included_players(rows)["players"]) == pytest.approx(
        1 / 3
    )


def test_stage_a_proceeds_on_a_strong_signal():
    report = stage_a(rows_for(6), repetitions=200)
    assert report["reliability_gate"]["passed"] is True
    assert report["ceiling_gate"]["passed"] is True
    assert report["stage"] == "proceed"
    assert report["r_obs"] > 0.9
    assert report["median_appearances_a"] == 5


def test_stage_a_stops_when_signal_is_noise():
    rows = rows_for(6)
    for row in rows:
        if row["window"] == "A":
            player = row["player_id"] - 100
            row["xg"] = 0.05 if (row["fixture_index"] + player) % 2 else 0.9
    report = stage_a(rows, repetitions=200)
    assert report["reliability_gate"]["passed"] is False
    assert report["stage"] == "stop_reliability"


def test_stage_a_requires_enough_players():
    with pytest.raises(ValueError):
        stage_a(rows_for(1), repetitions=200)


def test_stage_a_reports_position_change():
    rows = rows_for(6)
    report = stage_a(rows, repetitions=200)
    assert report["position_change_fraction"] == 0.0
    assert "per-90" in " ".join(report["notes"])
