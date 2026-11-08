"""Fictional provider rows check chronology, ambiguity and missing outcomes."""

from copy import deepcopy

from fil.research.future_action import (
    corroborate_reception,
    later_carrier_action,
    reception_followup,
    valid_action_clock,
)


def event():
    return {
        "event_type": "player_possession",
        "event_id": "TEST_ONLY",
        "period": "1",
        "player_id": "1",
        "team_id": "10",
        "frame_start": "90",
        "frame_end": "110",
        "end_type": "pass",
        "player_targeted_id": "2",
        "pass_outcome": "successful",
        "is_player_possession_end_matched": "True",
    }


def test_only_unique_future_action_is_used():
    e = event()
    out = later_carrier_action([e], 1, 100, 1, 10)
    assert out["status"] == "pass" and out["event_id"] == "TEST_ONLY" and out["target_id"] == 2
    assert later_carrier_action([e, deepcopy(e)], 1, 100, 1, 10)["status"] == "insufficient_data"
    assert later_carrier_action([e], 1, 110, 1, 10)["status"] == "insufficient_data"
    e["frame_end"] = "131"
    assert later_carrier_action([e], 1, 100, 1, 10)["status"] == "insufficient_data"


def test_unknown_target_or_unmatched_event_never_becomes_negative():
    e = event()
    e["player_targeted_id"] = ""
    assert later_carrier_action([e], 1, 100, 1, 10)["status"] == "insufficient_data"
    e = event()
    e["is_player_possession_end_matched"] = "False"
    assert later_carrier_action([e], 1, 100, 1, 10)["status"] == "insufficient_data"
    e = event()
    e["end_type"] = "shot"
    assert later_carrier_action([e], 1, 100, 1, 10)["status"] == "non_pass_action"
    e["end_type"] = ""
    assert later_carrier_action([e], 1, 100, 1, 10)["status"] == "insufficient_data"


def test_action_clock_requires_source_period_and_exact_frame_time():
    center = {"frame": 100, "period": 1, "timestamp": "00:00:10.000"}
    end = {"frame": 110, "period": 1, "timestamp": "00:00:11.000"}
    assert valid_action_clock(center, end, 1)
    end["timestamp"] = "00:00:11.100"
    assert not valid_action_clock(center, end, 1)
    end["timestamp"] = "00:00:11.000"
    end["period"] = 2
    assert not valid_action_clock(center, end, 1)


def test_reception_requires_first_event_target_team_and_provider_match():
    action = {"status": "pass", "pass_outcome": "successful", "end_frame": 110, "target_id": 2}
    reception = {
        **event(),
        "event_id": "RECEPTION_TEST",
        "frame_start": "120",
        "player_id": "2",
        "start_type": "pass_reception",
        "is_previous_pass_matched": "True",
    }
    assert (
        corroborate_reception([reception], 1, action, 10)["status"]
        == "provider_reception_corroborated"
    )
    reception["is_previous_pass_matched"] = "False"
    assert corroborate_reception([reception], 1, action, 10)["status"] == "unconfirmed"
    reception["is_previous_pass_matched"] = "True"
    assert (
        corroborate_reception([reception, deepcopy(reception)], 1, action, 10)["status"]
        == "unconfirmed"
    )


def test_receiver_followup_requires_known_and_matched_later_action():
    reception = {"status": "provider_reception_corroborated", "event_id": "R", "frame_start": 120}
    row = {**event(), "event_id": "R", "frame_start": "120", "frame_end": "140"}
    assert reception_followup([row], reception)["status"] == "pass_successful"
    row["frame_end"] = "171"
    assert reception_followup([row], reception)["status"] == "unconfirmed"
    row["frame_end"] = "140"
    row["pass_outcome"] = ""
    assert reception_followup([row], reception)["status"] == "unconfirmed"
