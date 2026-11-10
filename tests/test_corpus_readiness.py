"""TEST_ONLY adapter and process estimand regressions; no real corpus claims."""

import copy
import json

import pyarrow as pa
import pytest

from fil.ingestion.wyscout_testonly import adapt_test_only
from fil.possessions.extract import ACTION_SCHEMA
from fil.research.process import analyse


def wy_input():
    return dict(
        events=[
            dict(
                id=101,
                matchId=1,
                teamId=10,
                playerId=20,
                matchPeriod="1H",
                eventSec=1.5,
                eventId=8,
                subEventId=85,
                positions=[dict(x=10, y=80), dict(x=50, y=30)],
                tags=[dict(id=1801)],
            )
        ],
        match=dict(
            wyId=1,
            teamsData={
                "10": dict(
                    teamId=10,
                    formation=dict(lineup=[dict(playerId=20)], bench=[], substitutions=[]),
                ),
                "11": dict(
                    teamId=11,
                    formation=dict(lineup=[dict(playerId=21)], bench=[], substitutions=[]),
                ),
            },
        ),
        teams=[dict(wyId=10), dict(wyId=11)],
        players=[dict(wyId=20), dict(wyId=21)],
        provenance=dict(classification="TEST_ONLY"),
    )


def test_wyscout_raw_roundtrip_native_frame_and_no_invented_metrics():
    args = wy_input()
    before = copy.deepcopy(args)
    table, report = adapt_test_only(**args)
    assert args == before
    assert json.loads(table["source_record_json"][0].as_py()) == args["events"][0]
    assert table["original_event_id"].to_pylist() == [101]
    assert table["provisional_pass_tag_status"].to_pylist() == ["accurate_tag"]
    assert report["raw_count"] == report["output_count"] == 1
    assert report["exposure_seconds"] is None and not report["training_eligible"]
    assert not report["production_eligible"] and report["classification"] == "TEST_ONLY"
    args["events"][0]["tags"] = []
    args["events"][0]["playerId"] = 0
    table, report = adapt_test_only(**args)
    assert table["provisional_pass_tag_status"].to_pylist() == ["unknown"]
    assert table["original_player_id"].to_pylist() == [0]
    assert table["actor_player_id"].to_pylist() == [None]
    assert report["missing_actor_count"] == 1
    args["events"][0]["tags"] = [dict(id=1801), dict(id=1802)]
    assert adapt_test_only(**args)[0]["provisional_pass_tag_status"].to_pylist() == [
        "conflicting_tags"
    ]


@pytest.mark.parametrize(
    "bad",
    ["rights", "duplicate", "foreign", "coordinate", "player", "roster", "substitution", "period"],
)
def test_wyscout_rejects_unapproved_or_corrupt_identity(bad):
    args = wy_input()
    if bad == "rights":
        args["provenance"] = dict(classification="REAL")
    if bad == "duplicate":
        args["events"] *= 2
    if bad == "foreign":
        args["events"][0]["matchId"] = 2
    if bad == "coordinate":
        args["events"][0]["positions"][0]["x"] = 101
    if bad == "player":
        args["events"][0]["playerId"] = 999
    if bad == "roster":
        args["match"]["teamsData"]["11"]["formation"]["lineup"] = [dict(playerId=20)]
    if bad == "substitution":
        args["match"]["teamsData"]["10"]["formation"]["substitutions"] = [
            dict(playerIn=999, playerOut=20)
        ]
    if bad == "period":
        args["events"][0]["matchPeriod"] = "unknown"
    with pytest.raises(ValueError):
        adapt_test_only(**args)


def action(i, *, kind="Pass", zone="MID", end="MID", pid=1, period=1, ms=None):
    return dict(
        match_id=1,
        possession_id=pid,
        possession_team_id=10,
        sequence=i,
        provider_index=i,
        period=period,
        period_elapsed_ms=i * 1000 if ms is None else ms,
        team_id=10,
        player_id=20,
        event_id=f"TEST-{i}",
        event_type=kind,
        role="owner_action",
        zone=zone,
        end_zone=end,
        is_owner_action=True,
        action_status="completed" if kind == "Pass" else None,
        coordinate_system="raw_statsbomb_120x80",
        source_manifest_sha256="e" * 64,
    )


def process(rows):
    return analyse(pa.Table.from_pylist(rows, schema=ACTION_SCHEMA))


def test_order_distinguishes_cooccurrence_and_same_event():
    r = process([action(1, kind="Shot", zone="ATT"), action(2, end="BOX")])
    p = r["possessions"][0]
    assert p["same_possession_shot_and_final_third"]
    assert p["order_eligible"] and not p["shot_strictly_after_observed_final_third"]
    assert p["box_strictly_after_observed_final_third"]
    assert p["later_box_event_ids"] == ["TEST-2"]
    r = process([action(1, end="BOX"), action(2, kind="Shot", zone="MID")])
    assert r["possessions"][0]["shot_strictly_after_observed_final_third"]
    assert not r["possessions"][0]["box_strictly_after_observed_final_third"]


@pytest.mark.parametrize("bad", ["period", "clock", "gap"])
def test_unresolved_order_does_not_become_negative(bad):
    rows = [action(1, zone="ATT"), action(3, kind="Shot", zone="BOX")]
    if bad == "period":
        rows[1]["period"] = 2
    if bad == "clock":
        rows[1]["period_elapsed_ms"] = 0
    if bad == "gap":
        rows.insert(1, action(2, pid=None))
    r = process(rows)["possessions"][0]
    assert r["same_possession_shot_and_final_third"]
    assert not r["order_eligible"] and r["ordering_unresolved_reasons"]
    assert r["shot_strictly_after_observed_final_third"] is None


def test_forecast_cutoff_horizon_censoring_and_original_evidence():
    rows = [action(i) for i in range(1, 8)]
    rows[5] = action(6, kind="Shot", zone="ATT")
    result = process(rows)
    windows = result["forecast_windows"]
    assert windows[0]["cutoff_event_id"] == "TEST-1"
    assert windows[0]["outcome_event_ids"] == [f"TEST-{i}" for i in range(2, 7)]
    assert windows[0]["feature_event_ids"] == ["TEST-1"]
    assert windows[0]["outcome"] == 1
    assert windows[2]["outcome"] is None
    assert windows[2]["eligibility"] == "right_censored_short_chain"
    assert result["summary"]["complete_forecast_windows"] == 2
    # A shot known inside a short window is still excluded by the fixed eligibility rule.
    assert all(w["outcome"] is None for w in process(rows[-3:])["forecast_windows"])
    with pytest.raises(ValueError, match="Duplicate"):
        process(rows + [rows[0]])
    rows[0]["coordinate_system"] = "other_provider"
    with pytest.raises(ValueError, match="coordinate"):
        process(rows)


def test_development_fixture_never_holdout_and_no_provider_pooling():
    from fil.research.evaluation import chronological_split

    matches = [
        dict(source="statsbomb_open_data", match_id=i, match_date=d)
        for i, d in [(1, "2000-01-01"), (2, "2001-01-01"), (8658, "2002-01-01")]
    ]
    with pytest.raises(ValueError, match="development-exposed"):
        chronological_split(matches, "2000-12-31", "2001-12-31")
    matches[-1]["source"] = "other_provider"
    with pytest.raises(ValueError, match="Provider-specific"):
        chronological_split(matches, "2000-12-31", "2001-12-31")


def test_wyscout_missingness_and_clock_reversal_are_explicit():
    args = wy_input()
    e = copy.deepcopy(args["events"][0])
    e.update(id=102, eventSec=0, positions=[], eventId=99)
    args["events"].append(e)
    args["match"]["teamsData"]["10"]["formation"] = {}
    table, report = adapt_test_only(**args)
    assert table["ordering_status"].to_pylist() == ["array_order_only", "clock_reversal"]
    assert report["unrostered_actors"] == [(10, 20)]
    assert report["unknown_type_count"] == 1 and report["missing_positions"] == 1


def test_no_owner_actions_is_eligibility_exclusion_not_unresolved_order():
    row = action(1)
    row["is_owner_action"] = False
    r = process([row])["possessions"][0]
    assert not r["order_eligible"]
    assert r["ordering_unresolved_reasons"] == []
    assert r["eligibility_exclusion_reasons"] == ["no_owner_actions", "no_observed_final_third"]
