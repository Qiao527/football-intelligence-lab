"""TEST_ONLY falsification counterexamples; none represents actual football evidence."""

from copy import deepcopy

import pytest

from fil.research.connectivity import extract
from fil.research.connectivity_falsification import (
    GRIDS,
    analyze_match,
    cell,
    changed,
    distance,
    distribution,
    strata,
    summarize,
)

META = dict(
    match_id=999,
    home_team={"home_team_id": 1},
    away_team={"away_team_id": 2},
    home_score=0,
    away_score=0,
)
ROSTER = [
    dict(team_id=t, lineup=[dict(player_id=i, player_name=f"TEST_ONLY_{i}") for i in ids])
    for t, ids in ((1, [10, 11, 12]), (2, [20]))
]


def event(n, actor=11, kind="Pass", recipient=12, **kw):
    e = dict(
        id=f"TEST_ONLY_{n}",
        index=n,
        period=1,
        timestamp="00:00:00.000",
        team={"id": 1},
        player={"id": actor},
        possession=1,
        possession_team={"id": 1},
        type={"name": kind},
        location=[25, 1],
    )
    if kind == "Pass":
        e["pass"] = dict(recipient={"id": recipient}, end_location=[1, 1])
    e.update(kw)
    return e


def sample(middle=None):
    return [
        event(
            1,
            actor=10,
            recipient=11,
            location=[1, 1],
            **{"pass": dict(recipient={"id": 11}, end_location=[25, 1])},
        ),
        *(middle or []),
        event(9),
    ]


def audit(raw):
    parent = extract(raw, ROSTER, META, "a" * 64)
    before = deepcopy(parent)
    result = analyze_match(parent, raw)
    assert parent == before
    return parent, result


def test_intermediary_crossing_can_cancel_original_net_crossing():
    _, result = audit(sample())
    (r,) = result["rows"]
    assert r["outcomes"]["original"]["6x4"] is False
    assert r["outcomes"]["incoming"]["6x4"] is True
    assert r["outcomes"]["b_outgoing"]["6x4"] is True
    assert r["outcomes"]["b_relocation_proxy"]["6x4"] is False
    assert r["b_observed_receipt_release"] is None
    assert r["vector_identity_residual"] == [0, 0]


def test_incoming_crossing_does_not_establish_b_outgoing_crossing():
    raw = sample()
    raw[-1]["pass"]["end_location"] = [26, 1]
    _, result = audit(raw)
    (r,) = result["rows"]
    assert r["outcomes"]["original"]["6x4"] is True
    assert r["outcomes"]["b_outgoing"]["6x4"] is False
    assert r["separation"]["b_outgoing"] == 1


@pytest.mark.parametrize("point", [None, [float("nan"), 1], [121, 1], [True, 1], [1]])
def test_missing_invalid_coordinates_remain_unknown(point):
    assert cell(point) is None
    assert changed(point, [1, 1], GRIDS["6x4"]) is None
    assert distance(point, [1, 1]) is None


def test_nested_grid_reduction_is_mechanical_and_edges_are_inclusive():
    assert cell([120, 80]) == (5, 3)
    assert cell([0, 0]) == (0, 0)
    for x in range(121):
        for y in (0, 19, 20, 39, 40, 79, 80):
            fine, coarse = cell([x, y]), cell([x, y], 3, 2)
            assert coarse == tuple(v // 2 for v in fine)
    assert changed([19, 1], [21, 1], GRIDS["6x4"])
    assert not changed([19, 1], [21, 1], GRIDS["3x2"])
    assert not changed([19, 1], [21, 1], GRIDS["shift5"])


def test_receipt_is_identifiable_only_with_one_successful_record():
    raw = sample([event(3, kind="Ball Receipt*", location=[24, 1])])
    _, result = audit(raw)
    (r,) = result["rows"]
    assert r["receipt_event_ids"] == ["TEST_ONLY_3"]
    assert r["receipt_proxy_separation"] == 1
    assert r["b_observed_receipt_release"] is False
    assert r["eligibility"]["receipt_required"]
    assert r["eligibility"]["no_carry"] and not r["eligibility"]["no_intervening"]
    _, result = audit(sample([event(3, kind="Ball Receipt*"), event(4, kind="Ball Receipt*")]))
    (r,) = result["rows"]
    assert r["b_observed_receipt_release"] is None
    assert not r["eligibility"]["receipt_required"]


@pytest.mark.parametrize(
    "outcome,expected", [("Complete", True), ("Incomplete", False), (None, False)]
)
def test_relaxed_dribble_is_separate_and_never_repairs_original(outcome, expected):
    raw = sample([event(3, kind="Dribble", dribble={"outcome": {"name": outcome}})])
    parent, result = audit(raw)
    assert not parent["chains"]
    (candidate,) = result["candidates"]
    assert not candidate["eligibility"]["original"]
    assert candidate["eligibility"]["permit_complete_dribble"] == expected
    assert len(result["rows"]) == int(expected)


@pytest.mark.parametrize(
    "middle",
    [
        event(3, kind="Pressure"),
        event(3, actor=20, kind="Carry", team={"id": 2}),
        event(3, kind="Ball Receipt*", ball_receipt={"outcome": None}),
        event(3, **{"pass": {"recipient": {"id": 12}, "outcome": None}}),
    ],
)
def test_no_variant_skips_unapproved_or_ambiguous_interruption(middle):
    _, result = audit(sample([middle]))
    assert not result["rows"]
    assert not result["candidates"][0]["eligibility"]["permit_complete_dribble"]


def test_component_unknown_does_not_change_original_endpoint_metric():
    raw = sample()
    raw[0]["pass"].pop("end_location")
    _, result = audit(raw)
    (r,) = result["rows"]
    assert r["outcomes"]["original"]["6x4"] is False
    assert r["outcomes"]["incoming"]["6x4"] is None
    assert r["outcomes"]["b_relocation_proxy"]["6x4"] is None
    assert r["vector_identity_residual"] is None


def test_retrospective_endpoint_strata_are_tautological_and_sparse_support_visible():
    parent, result = audit(sample())
    summary = summarize([result], [parent])
    assert summary["partition_summary"]["endpoint_pair_nonreturn"]["within_stratum_sse"] == 0
    assert (
        summary["partition_summary"]["team_period_score_start"]["strata_with_two_players_at_least5"]
        == 0
    )
    assert summary["opportunity_bins"]["1-4"] == 1
    assert summary["opportunity_bins"]["0"] == 2
    b = next(d for d in summary["decomposition"] if d["player_id"] == 11)
    assert b["N"] == b["M"] == 1 and b["K"] == 0
    assert b["ability_estimate"] is b["official_minutes"] is None
    assert summary["recommendation"] == "PENDING_SCIENTIFIC_REVIEW"
    assert not summary["independent_confirmation"]
    assert strata(result["rows"])


def test_no_carry_variant_retains_zero_and_receipt_ambiguity():
    _, result = audit(sample([event(3, kind="Carry")]))
    (r,) = result["rows"]
    assert r["eligibility"]["original"] and not r["eligibility"]["no_carry"]
    assert r["b_observed_receipt_release"] is None


def test_distribution_does_not_zero_fill_missingness():
    assert distribution([None, 1, 3]) == dict(
        known=2, missing=1, min=1, q25=1.5, median=2, q75=2.5, max=3
    )
    assert distribution([None])["median"] is None
