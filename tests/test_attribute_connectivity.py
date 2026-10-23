"""TEST_ONLY records; no fabricated fixture is represented as empirical research."""

from copy import deepcopy

import pytest

from fil.research.attribute_registry import load, validate
from fil.research.connectivity import correlation, extract, summarize, zone

META = dict(
    match_id=999,
    match_date="2000-01-01",
    home_team={"home_team_id": 1},
    away_team={"away_team_id": 2},
    home_score=0,
    away_score=0,
)
ROSTER = [
    dict(
        team_id=1,
        lineup=[dict(player_id=i, player_name=f"TEST_ONLY_{i}") for i in (10, 11, 12, 13)],
    ),
    dict(team_id=2, lineup=[dict(player_id=20, player_name="TEST_ONLY_20")]),
]


def event(index, kind="Pass", actor=10, recipient=11, start=None, end=None, **kwargs):
    row = dict(
        id=f"TEST_ONLY_{index}",
        index=index,
        period=1,
        timestamp="00:00:00.000",
        team={"id": 1},
        player={"id": actor},
        possession=1,
        possession_team={"id": 1},
        type={"name": kind},
        location=[10, 10] if start is None else start,
    )
    if kind == "Pass":
        row["pass"] = dict(
            recipient={"id": recipient}, end_location=[80, 60] if end is None else end
        )
    row.update(kwargs)
    return row


def sample():
    return [
        event(1),
        event(2, "Ball Receipt*", actor=11),
        event(3, "Carry", actor=11),
        event(4, actor=11, recipient=12),
    ]


def run(raw):
    return extract(raw, ROSTER, META, "a" * 64)


def test_registry_complete_and_rejects_missing_duplicate_and_false_status():
    registry = load()
    assert {a["attribute_id"] for a in registry["attributes"]} == {
        "attacking_connectivity",
        "risk_adjusted_progression",
        "possession_continuity",
    }
    for change in ("missing", "duplicate", "status"):
        bad = deepcopy(registry)
        if change == "missing":
            del bad["attributes"][0]["latent_construct"]
        elif change == "duplicate":
            bad["attributes"].append(bad["attributes"][0])
        else:
            bad["attributes"][0]["research_status"] = "proven_ability"
        with pytest.raises(ValueError):
            validate(bad)


@pytest.mark.parametrize(
    "point,expected",
    [
        ([0, 0], "0:0"),
        ([120, 80], "5:3"),
        ([20, 20], "1:1"),
        (None, None),
        ([0], None),
        ([float("nan"), 3], None),
        ([121, 2], None),
        ([True, 1], None),
    ],
)
def test_native_zone_boundaries_and_missingness(point, expected):
    assert zone(point) == expected


def test_completed_chain_lineage_volume_and_no_minutes():
    result = run(sample())
    (c,) = result["chains"]
    assert c["pass_event_ids"] == ["TEST_ONLY_1", "TEST_ONLY_4"]
    assert c["intervening_event_ids"] == ["TEST_ONLY_2", "TEST_ONLY_3"]
    assert c["nonreturn"] and c["zone_transition"] == {"6x4": True, "3x2": True}
    r = next(p for p in result["players"] if p["player_id"] == 11)
    assert (r["completed_passes"], r["received_passes"], r["in_degree"], r["out_degree"]) == (
        1,
        1,
        1,
        1,
    )
    assert r["conditional_chain_fraction"] == 1
    assert r["official_minutes"] is r["ability_estimate"] is None
    assert r["team_completed_pass_opportunities"] == 2
    assert sum(p["completed_passes"] for p in result["players"]) == 2


@pytest.mark.parametrize(
    "middle",
    [
        event(2, "Pressure", actor=11),
        event(2, "Carry", actor=20, team={"id": 2}),
        event(2, "Ball Receipt*", actor=11, ball_receipt={"outcome": None}),
        event(2, actor=11, **{"pass": {"recipient": {"id": 12}, "outcome": None}}),
        event(
            2, actor=11, **{"pass": {"recipient": {"id": 12}, "outcome": {"name": "Incomplete"}}}
        ),
    ],
)
def test_never_skip_interruption_failed_or_unknown_pass(middle):
    raw = [event(1), middle, event(4, actor=11, recipient=12)]
    assert run(raw)["chains"] == []


def test_cross_period_noncontiguous_and_owner_ambiguity_block_only_sequences():
    for field, value in (("period", 2), ("possession", 2), ("possession_team", {"id": 2})):
        raw = sample()
        raw[1][field] = value
        result = run(raw)
        assert result["chains"] == []
        assert sum(p["completed_passes"] for p in result["players"]) == 2
        assert result["excluded_memberships"]


def test_missing_geometry_keeps_evidence_and_withholds_fraction():
    raw = sample()
    raw[-1]["pass"].pop("end_location")
    result = run(raw)
    (c,) = result["chains"]
    assert c["zone_transition"]["6x4"] is None
    r = next(p for p in result["players"] if p["player_id"] == 11)
    assert r["conditional_chain_fraction"] is None and r["observed_chains"] == 1


def test_return_is_counterexample_not_cross_zone_descriptor():
    raw = sample()
    raw[-1]["pass"]["recipient"]["id"] = 10
    result = run(raw)
    assert not result["chains"][0]["nonreturn"]
    assert not any(p["cross_zone_nonreturn"] for p in result["players"])


def test_exact_subsequent_shot_lineage_and_no_future_score_leakage():
    raw = sample() + [
        event(
            5,
            "Shot",
            actor=12,
            shot={"outcome": {"name": "Goal"}, "type": {"name": "Open Play"}, "statsbomb_xg": 0.1},
        )
    ]
    meta = deepcopy(META)
    meta["home_score"] = 1
    result = extract(raw, ROSTER, meta, "a" * 64)
    assert result["chains"][0]["later_recorded_shot_ids"] == ["TEST_ONLY_5"]
    assert all(
        p["score_state"] == "level" and not p["prior_goal_event_ids"] for p in result["passes"]
    )


def test_identity_corruption_duplicates_and_reorder_stop():
    for change in ("duplicate", "order", "recipient"):
        raw = sample()
        if change == "duplicate":
            raw[-1]["id"] = raw[0]["id"]
        elif change == "order":
            raw[0], raw[1] = raw[1], raw[0]
        else:
            raw[-1]["pass"]["recipient"]["id"] = 20
        with pytest.raises(ValueError):
            run(raw)


def test_undefined_redundancy_and_no_population_certification():
    assert correlation([1, 1], [1, 2]) is None
    summary = summarize([run(sample())], [META])
    assert summary["scientific_verdict"] == "INCONCLUSIVE"
    assert not summary["selected_player_ids"]
    assert summary["population_interval"] is None
    assert not summary["ability_identified"]


def test_alternative_path_is_an_actually_observed_chain():
    raw = [
        event(1),
        event(2, actor=11, recipient=12),
        event(3, actor=12, recipient=10),
        event(4, actor=10, recipient=13),
        event(5, actor=13, recipient=12),
    ]
    result = run(raw)
    first = result["chains"][0]
    assert first["alternative_observed_chain_ids"] == ["TEST_ONLY_4/TEST_ONLY_5"]
