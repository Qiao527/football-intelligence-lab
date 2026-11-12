"""TEST_ONLY projection of raw provider records into the scouting contract."""

import json

import pytest

from fil.research.scouting_raw import (
    load_corpus,
    project_event,
    project_lineups,
    project_matches,
)


def raw_shot(**overrides):
    row = {
        "id": "E1",
        "index": 5,
        "period": 1,
        "type": {"id": 16, "name": "Shot"},
        "team": {"id": 10},
        "player": {"id": 100},
        "shot": {
            "statsbomb_xg": 0.31,
            "type": {"name": "Open Play"},
            "outcome": {"name": "Goal"},
        },
    }
    row.update(overrides)
    return row


def test_shot_projection_keeps_only_named_source_fields():
    row = project_event(raw_shot(), 7)
    assert row["event_id"] == "E1"
    assert row["match_id"] == 7
    assert row["team_id"] == 10
    assert row["player_id"] == 100
    assert row["shot_xg"] == 0.31
    assert row["shot_type"] == "Open Play"
    assert row["shot_outcome"] == "Goal"
    assert row["provider_index"] == 5


def test_non_shot_keeps_null_shot_fields():
    raw = {"id": "P1", "period": 2, "type": {"name": "Pass"}, "team": {"id": 10}}
    row = project_event(raw, 8)
    assert row["event_type"] == "Pass"
    assert row["shot_xg"] is None
    assert row["player_id"] is None


def test_missing_shot_xg_stays_null_for_the_exporter_to_reject():
    raw = raw_shot(shot={"type": {"name": "Open Play"}, "outcome": {"name": "Saved"}})
    assert project_event(raw, 7)["shot_xg"] is None


def test_event_identity_and_period_are_required():
    with pytest.raises(ValueError):
        project_event({"period": 1}, 7)
    with pytest.raises(ValueError):
        project_event({"id": "E1", "period": "1"}, 7)


def test_lineups_keep_provider_position_intervals_verbatim():
    raw = [
        {
            "team_id": 10,
            "lineup": [
                {
                    "player_id": 100,
                    "positions": [
                        {"position": "Center Forward", "from": "00:00", "to": None}
                    ],
                },
                {"player_id": 101, "positions": []},
            ],
        }
    ]
    rows = project_lineups(raw, 7)
    assert [(r["team_id"], r["player_id"]) for r in rows] == [(10, 100), (10, 101)]
    assert rows[0]["positions"][0]["position"] == "Center Forward"
    assert rows[1]["positions"] == []


def test_match_projection_reads_provider_stage_and_teams():
    raw = [
        {
            "match_id": 1,
            "match_date": "2018-06-14",
            "competition_stage": {"name": "Group Stage"},
            "home_team": {"home_team_id": 10},
            "away_team": {"away_team_id": 11},
            "home_score": 2,
            "away_score": 1,
        }
    ]
    row = project_matches(raw)[0]
    assert row == {
        "match_id": 1,
        "match_date": "2018-06-14",
        "competition_stage": "Group Stage",
        "home_team_id": 10,
        "away_team_id": 11,
        "home_score": 2,
        "away_score": 1,
    }


def write_corpus(tmp_path, revision="rev"):
    base = tmp_path / revision
    folder = base / "1"
    folder.mkdir(parents=True)
    matches = [
        {
            "match_id": 1,
            "match_date": "2018-06-14",
            "competition_stage": {"name": "Group Stage"},
            "home_team": {"home_team_id": 10},
            "away_team": {"away_team_id": 11},
        }
    ]
    (base / "competition-matches.json").write_text(json.dumps(matches))
    (folder / "1.json.events").write_text(json.dumps([raw_shot()]))
    (folder / "1.json.lineups").write_text(
        json.dumps([{"team_id": 10, "lineup": [{"player_id": 100, "positions": []}]}])
    )
    return tmp_path


def test_load_corpus_reads_and_counts(tmp_path):
    root = write_corpus(tmp_path)
    corpus = load_corpus(root, "rev")
    assert corpus["match_count"] == 1
    assert corpus["raw_event_count"] == 1
    assert corpus["events"][0]["shot_xg"] == 0.31
    assert corpus["lineups"][0]["player_id"] == 100


def test_load_corpus_rejects_missing_metadata_and_unknown_matches(tmp_path):
    root = write_corpus(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_corpus(tmp_path, "absent")
    (root / "rev" / "competition-matches.json").write_text("[]")
    with pytest.raises(ValueError):
        load_corpus(root, "rev")
