"""TEST_ONLY proposed metric gates: no acquisition or operational policy changes."""

import copy
import hashlib
import json

import pytest

from fil.research.acquisition import REVISION
from fil.research.eligibility import assess, ordered_score, source_clock_difference


def fixture(periods=2):
    raw = []
    spreads = [107, 160, 280, 40]
    for p in range(1, periods + 1):
        for kind, ms, team in [
            ("Half Start", 0, 1),
            ("Half Start", 0, 2),
            ("Pass", 1000, 1),
            ("Half End", 10000, 1),
            ("Half End", 10000 + spreads[p - 1], 2),
        ]:
            i = len(raw) + 1
            raw.append(
                dict(
                    id=f"TEST-{i}",
                    index=i,
                    period=p,
                    timestamp=f"00:00:{ms // 1000:02}.{ms % 1000:03}",
                    type=dict(name=kind),
                    team=dict(id=team),
                    possession=p,
                    possession_team=dict(id=1),
                    **dict(location=[20, 30], **{"pass": dict(end_location=[40, 30])})
                    if kind == "Pass"
                    else {},
                )
            )
        raw[-5]["related_events"] = [raw[-4]["id"]]
        raw[-4]["related_events"] = [raw[-5]["id"]]
        raw[-2]["related_events"] = [raw[-1]["id"]]
        raw[-1]["related_events"] = [raw[-2]["id"]]
    meta = dict(
        match_id=99,
        home_team=dict(home_team_id=1),
        away_team=dict(away_team_id=2),
        home_score=0,
        away_score=0,
    )
    return raw, meta


def canonical(raw, mid=99):
    return [
        dict(
            event_id=e["id"],
            provider_index=e["index"],
            period=e["period"],
            period_timestamp=e["timestamp"],
            event_type=e["type"]["name"],
            team_id=e["team"]["id"],
            player_id=None,
            possession_id=e.get("possession"),
            possession_team_id=e.get("possession_team", {}).get("id"),
            raw_event_row=n,
            match_id=mid,
            source_record_json=json.dumps(e),
            source="statsbomb_open_data",
            source_revision=hashlib.sha256(json.dumps(raw).encode()).hexdigest(),
            source_manifest_sha256="b" * 64,
            upstream_revision=REVISION,
            x=e.get("location", [None, None])[0],
            y=e.get("location", [None, None])[1],
            end_x=e.get("pass", {}).get("end_location", [None, None])[0],
            end_y=e.get("pass", {}).get("end_location", [None, None])[1],
            coordinate_system="raw_statsbomb_120x80",
            duration_s=e.get("duration"),
            related_event_ids=e.get("related_events"),
        )
        for n, e in enumerate(raw)
    ]


def run(raw, meta, rows=None):
    body = json.dumps(raw).encode()
    return assess(
        body,
        hashlib.sha256(body).hexdigest(),
        canonical(raw) if rows is None else rows,
        meta,
        source_manifest_sha256="b" * 64,
    )


def test_8656_spread_regression_is_conditional_and_prefix_uncertainty_cancels():
    raw, meta = fixture(4)
    before = copy.deepcopy(raw)
    result = run(raw, meta)
    assert raw == before
    e = result["eligibility"]
    assert all(
        e[k]["support"] == "fully_supported"
        for k in (
            "source_identity",
            "event_order",
            "score",
            "native_spatial",
            "within_period_source_clock",
        )
    )
    assert e["cross_period_envelope"]["support"] == "conditionally_supported"
    assert e["exact_time_exposure"]["support"] == "blocked"
    assert e["recorded_census_envelope"]["support"] == "blocked"  # no roster in TEST_ONLY case
    m = e["cross_period_envelope"]["model"]
    assert m["conditional_recorded_match_duration_ms"] == [40000, 40587]
    within = source_clock_difference(raw[5], raw[7], m)
    assert within["source_clock_difference_ms"] == [1000, 1000]
    assert not within["physical_timing_certified"]
    cross = source_clock_difference(raw[2], raw[7], m)
    assert cross["source_clock_difference_ms"] == [10000, 10107]
    assert cross["dependency_periods"] == [1]
    assert not result["expansion_authorized"] and result["expansion_gate"] == "BLOCKED"


@pytest.mark.parametrize(
    "change",
    ["count", "json", "coordinate", "timestamp", "identity", "pass_semantics", "source_namespace"],
)
def test_source_corruption_blocks_all_analytical_outputs(change):
    raw, meta = fixture()
    rows = canonical(raw)
    if change == "count":
        rows.pop()
    elif change == "json":
        rows[2]["source_record_json"] = "{}"
    else:
        rows[2][
            {
                "coordinate": "x",
                "timestamp": "period_timestamp",
                "identity": "event_id",
                "pass_semantics": "pass_outcome",
                "source_namespace": "source",
            }[change]
        ] = 999
    result = run(raw, meta, rows)
    assert all(v["support"] == "blocked" for v in result["eligibility"].values())


def test_native_metric_gates_do_not_infer_physical_direction_or_timing():
    raw, meta = fixture()
    raw[-1]["related_events"] = []
    raw[2].pop("location")
    e = run(raw, meta)["eligibility"]
    assert e["native_spatial"]["support"] == "conditionally_supported"
    assert e["native_spatial"]["missing_geometry"] == [raw[2]["id"]]
    assert e["within_period_source_clock"]["support"] == "fully_supported"
    assert e["cross_period_envelope"]["support"] == "blocked"
    assert not e["native_spatial"]["physical_direction_certified"]
    assert e["score"]["support"] == "fully_supported"
    raw[2]["location"] = [121, 30]
    assert run(raw, meta)["eligibility"]["native_spatial"]["support"] == "blocked"


def test_score_handles_linked_own_goal_without_selecting_period_end():
    raw, meta = fixture()
    a, b = raw[2], raw[7]
    a["type"]["name"], b["type"]["name"] = "Own Goal Against", "Own Goal For"
    a["team"]["id"], b["team"]["id"] = 1, 2
    b["period"], b["timestamp"] = a["period"], a["timestamp"]
    a["related_events"], b["related_events"] = [b["id"]], [a["id"]]
    meta["away_score"] = 1
    r = ordered_score(raw, meta)
    assert r["match_play"] == [0, 1] and len(r["decisions"]) == 1
    b["related_events"] = []
    a["related_events"] = []
    with pytest.raises(ValueError, match="Unlinked"):
        ordered_score(raw, meta)


def test_shootout_goals_do_not_change_match_play_score():
    raw, meta = fixture()
    raw.append(
        dict(
            id="TEST-SHOOTOUT",
            index=len(raw) + 1,
            period=5,
            type=dict(name="Shot"),
            team=dict(id=1),
            timestamp="00:00:01.000",
            shot=dict(outcome=dict(name="Goal"), type=dict(name="Penalty")),
        )
    )
    result = ordered_score(raw, meta)
    assert result["shootout"] == [1, 0] and result["match_play"] == [0, 0]
    assert result["shootout_official_reconciliation"] == "unavailable"
    meta["home_score"] = 1
    with pytest.raises(ValueError, match="official"):
        ordered_score(raw, meta)


def test_source_hash_and_reversing_native_clock_fail_independent_gates():
    raw, meta = fixture()
    result = assess(
        json.dumps(raw).encode(), "0" * 64, canonical(raw), meta, source_manifest_sha256="b" * 64
    )
    assert result["eligibility"]["source_identity"]["support"] == "blocked"
    raw[-1]["timestamp"] = "00:00:00.500"
    e = run(raw, meta)["eligibility"]
    assert e["source_identity"]["support"] == "fully_supported"
    assert e["within_period_source_clock"]["support"] == "blocked"
    assert e["score"]["support"] == "fully_supported"


def test_completion_invariance_is_separate_from_observed_timestamp_arithmetic():
    raw, meta = fixture()
    raw[2]["timestamp"], raw[2]["duration"] = "00:00:09.999", 0.0015
    e = run(raw, meta)["eligibility"]
    assert e["within_period_source_clock"]["support"] == "fully_supported"
    assert e["known_completion_boundary_invariance"]["support"] == "blocked"
    assert e["known_completion_boundary_invariance"]["known_duration_overlap_ids"] == [raw[2]["id"]]
    assert e["physical_spatial"]["support"] == "blocked"
