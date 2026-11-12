"""TEST_ONLY scouting decision stages: reliability, ceiling and frozen gates."""

import math

import pytest

from fil.research import scouting_task as st
from fil.research.scouting_task import (
    DEFAULT_THRESHOLDS,
    Thresholds,
    bootstrap_pairs,
    candidate_universe,
    ceiling_gate,
    classify_increment,
    criterion_values,
    measurement_ceiling,
    pearson,
    reliability_gate,
    reliability_pairs,
    reliability_stage,
    shrink,
    spearman_brown,
    validate_appearances,
    window_of,
)


def appearance(**overrides):
    row = {
        "source": "statsbomb_open_data",
        "match_id": 1,
        "team_id": 10,
        "player_id": 100,
        "stage": "group",
        "team_matchday": 1,
        "position_label": "Center Forward",
        "shots": 2,
        "goals": 1,
        "xg": 0.6,
        "npxg": 0.0,
    }
    row.update(overrides)
    return row


def pairs_rows(values, metric="xg", **overrides):
    """Two observation appearances per player, in two distinct matches."""
    rows = []
    for index, (first, second) in enumerate(values):
        player = 100 + index
        rows.append(
            appearance(
                player_id=player,
                match_id=index + 1,
                team_matchday=1,
                **{metric: first},
                **overrides,
            )
        )
        rows.append(
            appearance(
                player_id=player,
                match_id=index + 101,
                team_matchday=2,
                **{metric: second},
                **overrides,
            )
        )
    return rows


def strong_pairs():
    return [(0.10, 0.12), (0.20, 0.22), (0.30, 0.31), (0.40, 0.42),
            (0.50, 0.49), (0.70, 0.72), (0.90, 0.88)]


def test_window_mapping_uses_team_matchday_not_calendar():
    assert window_of(appearance(team_matchday=1)) == "observation"
    assert window_of(appearance(team_matchday=2)) == "observation"
    assert window_of(appearance(team_matchday=3)) == "criterion"
    assert window_of(appearance(stage="knockout", team_matchday=None)) == "criterion_knockout"
    with pytest.raises(ValueError):
        window_of(appearance(team_matchday=4))
    with pytest.raises(ValueError):
        window_of(appearance(stage="knockout", team_matchday=3))
    with pytest.raises(ValueError):
        window_of(appearance(stage="friendly"))


def test_missing_source_xg_fails_instead_of_becoming_zero():
    with pytest.raises(ValueError):
        validate_appearances([appearance(xg=None)])
    with pytest.raises(ValueError):
        validate_appearances([appearance(xg=float("nan"))])


def test_impossible_records_are_rejected():
    with pytest.raises(ValueError):
        validate_appearances([appearance(goals=3)])
    with pytest.raises(ValueError):
        validate_appearances([appearance(xg=2.5)])
    with pytest.raises(ValueError):
        validate_appearances([appearance(xg=0.4, npxg=0.5)])
    with pytest.raises(ValueError):
        validate_appearances([appearance(shots=-1)])
    with pytest.raises(ValueError):
        validate_appearances([appearance(shots=True)])


def test_duplicate_appearance_identity_is_rejected():
    with pytest.raises(ValueError):
        validate_appearances([appearance(), appearance()])


def test_candidate_universe_reports_inclusion_and_exclusions():
    rows = [
        appearance(player_id=1, match_id=1, team_matchday=1),
        appearance(player_id=1, match_id=2, team_matchday=2),
        appearance(player_id=2, match_id=3, team_matchday=1, position_label=None),
        appearance(player_id=3, match_id=4, team_matchday=1),
        appearance(player_id=4, match_id=5, team_matchday=3),
    ]
    primary = candidate_universe(rows)
    assert primary["included"] == 2
    assert primary["excluded_unlabelled"] == 1
    assert primary["excluded_insufficient_appearances"] == 0
    sensitivity = candidate_universe(rows, minimum_appearances=2)
    assert sensitivity["included"] == 1
    assert sensitivity["excluded_insufficient_appearances"] == 2
    with pytest.raises(ValueError):
        candidate_universe(rows, minimum_appearances=0)


def test_null_first_label_does_not_hide_later_position_metadata():
    rows = [
        appearance(player_id=7, match_id=1, team_matchday=1, position_label=None),
        appearance(player_id=7, match_id=2, team_matchday=2),
    ]
    universe = candidate_universe(rows)
    assert universe["included"] == 1
    assert universe["excluded_unlabelled"] == 0


def test_pearson_needs_pairs_and_variance():
    assert pearson([(1.0, 2.0), (2.0, 3.0)]) is None
    assert pearson([(1.0, 2.0), (1.0, 3.0), (1.0, 4.0)]) is None
    assert pearson([(1.0, 2.0), (2.0, 4.0), (3.0, 6.0)]) == pytest.approx(1.0)
    assert pearson([(1.0, 6.0), (2.0, 4.0), (3.0, 2.0)]) == pytest.approx(-1.0)


def test_spearman_brown_is_the_two_measurement_composite():
    assert spearman_brown(0.0) == pytest.approx(0.0)
    assert spearman_brown(0.5) == pytest.approx(0.6666666666666666)
    assert spearman_brown(0.3, k=1) == pytest.approx(0.3)
    with pytest.raises(ValueError):
        spearman_brown(1.5)
    with pytest.raises(ValueError):
        spearman_brown(0.0, k=0)


def test_ceiling_is_the_attenuation_bound():
    assert measurement_ceiling(1.0, 1.0) == pytest.approx(1.0)
    assert measurement_ceiling(0.25, 0.25) == pytest.approx(0.25)
    assert measurement_ceiling(0.64, 0.25) == pytest.approx(0.4)
    assert measurement_ceiling(-0.2, 0.5) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        measurement_ceiling(1.2, 0.5)


def test_reliability_pairs_use_first_two_matchdays_only():
    rows = pairs_rows([(0.2, 0.3), (0.4, 0.5), (0.6, 0.7)])
    result = reliability_pairs(rows, "xg")
    assert result["n_pairs"] == 3
    assert result["pairs"][0] == (0.2, 0.3)
    assert result["r_single"] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        reliability_pairs(rows, "height")
    extra = rows + [appearance(player_id=100, team_matchday=1, match_id=9)]
    with pytest.raises(ValueError):
        reliability_pairs(extra, "xg")


def test_single_appearance_players_are_counted_not_imputed():
    rows = pairs_rows([(0.2, 0.3), (0.4, 0.5), (0.6, 0.7)])
    rows.append(appearance(player_id=999, team_matchday=1))
    result = reliability_pairs(rows, "xg")
    assert result["single_appearance_players"] == 1
    assert result["n_pairs"] == 3


def test_reliability_pairs_respect_the_candidate_universe():
    rows = pairs_rows([(0.2, 0.3), (0.4, 0.5), (0.6, 0.7)])
    for row in rows:
        if row["player_id"] == 102:
            row["position_label"] = None
    result = reliability_pairs(rows, "xg")
    assert result["n_pairs"] == 2
    assert result["r_single"] is None


def test_bootstrap_is_deterministic_and_guarded():
    pairs = strong_pairs()
    first = bootstrap_pairs(pairs, seed=7, repetitions=200)
    second = bootstrap_pairs(pairs, seed=7, repetitions=200)
    assert first == second
    assert first[0] <= first[1]
    assert bootstrap_pairs(pairs[:2], repetitions=200) is None
    with pytest.raises(ValueError):
        bootstrap_pairs(pairs, repetitions=10)


def test_reliability_gate_requires_the_lower_bound():
    passing = reliability_gate(0.7, [0.6, 0.8], DEFAULT_THRESHOLDS)
    assert passing["passed"] is True
    assert passing["r_obs"] == pytest.approx(spearman_brown(0.7))
    optimistic = reliability_gate(0.7, [0.1, 0.9], DEFAULT_THRESHOLDS)
    assert optimistic["passed"] is False
    assert optimistic["reason"] == "below_declared_threshold"
    missing = reliability_gate(None, None, DEFAULT_THRESHOLDS)
    assert missing["passed"] is False
    assert missing["reason"] == "insufficient_or_degenerate_pairs"


def test_reliability_gate_applies_the_comparative_margin():
    failed = reliability_gate(0.7, [0.6, 0.8], DEFAULT_THRESHOLDS, comparative=-0.4)
    assert failed["passed"] is False
    assert failed["reason"] == "xG_reliability_below_goals_margin"
    fine = reliability_gate(0.7, [0.6, 0.8], DEFAULT_THRESHOLDS, comparative=-0.05)
    assert fine["passed"] is True


def test_criterion_values_average_per_appearance_and_stay_separate():
    rows = [
        appearance(player_id=1, team_matchday=3, shots=1, xg=0.2, npxg=0.2),
        appearance(player_id=1, team_matchday=3, match_id=2, shots=3, xg=0.9, npxg=0.9),
        appearance(player_id=2, stage="knockout", team_matchday=None, shots=1, xg=0.4),
    ]
    group = criterion_values(rows, "xg")
    assert group[(1, 10)] == pytest.approx(0.55)
    assert (2, 10) not in group
    knockout = criterion_values(rows, "xg", window="criterion_knockout")
    assert knockout[(2, 10)] == pytest.approx(0.4)
    with pytest.raises(ValueError):
        criterion_values(rows, "xg", window="observation")


def test_ceiling_gate_stops_before_scoring():
    passed = ceiling_gate(0.7, 0.6, DEFAULT_THRESHOLDS)
    assert passed["passed"] is True
    stopped = ceiling_gate(0.6, 0.3, DEFAULT_THRESHOLDS)
    assert stopped["passed"] is False
    assert stopped["reason"] == "uninformative_by_ceiling"
    assert stopped["ceiling"] == pytest.approx(math.sqrt(0.18))


def test_increment_labels_are_exhaustive_and_not_interchangeable():
    low = classify_increment([-0.1, 0.1], 0.3, DEFAULT_THRESHOLDS)
    assert low["label"] == "uninformative"
    clear = classify_increment([-0.01, 0.02], 0.8, DEFAULT_THRESHOLDS)
    assert clear["label"] == "no_detectable_increment"
    wide = classify_increment([-0.3, 0.1], 0.8, DEFAULT_THRESHOLDS)
    assert wide["label"] == "inconclusive"
    assert wide["half_width"] == pytest.approx(0.2)
    positive = classify_increment([0.05, 0.2], 0.8, DEFAULT_THRESHOLDS)
    assert positive["label"] == "increment"
    adverse = classify_increment([-0.2, -0.05], 0.8, DEFAULT_THRESHOLDS)
    assert adverse["label"] == "adverse"
    assert classify_increment(None, 0.8, DEFAULT_THRESHOLDS)["label"] == "inconclusive"


def test_increment_boundary_is_closed_at_the_mwd():
    exact = classify_increment([-0.1, 0.1], 0.8, DEFAULT_THRESHOLDS)
    assert exact["label"] == "no_detectable_increment"


def test_shrink_is_the_declared_deterministic_input():
    assert shrink(2.0, 4.0, 0.25, 4.0) == pytest.approx(0.375)
    assert shrink(0.0, 10.0, 0.2, 10.0) == pytest.approx(0.1)
    with pytest.raises(ValueError):
        shrink(1.0, 1.0, 0.2, 0)
    with pytest.raises(ValueError):
        shrink(1.0, 1.0, 1.2, 5)


def test_stage_proceeds_only_when_both_gates_pass():
    report = reliability_stage(pairs_rows(strong_pairs()), DEFAULT_THRESHOLDS, repetitions=200)
    assert report["reliability_gate"]["passed"] is True
    assert report["ceiling_gate"]["passed"] is True
    assert report["stage"] == "proceed"
    assert report["n_pairs"] == len(strong_pairs())
    assert set(report["metrics"]) == set(st.METRICS)
    assert report["metrics"]["xg"]["r_single"] > 0.9
    assert report["metrics"]["goals"]["r_single"] is None


def test_stage_stops_when_reliability_fails():
    noisy = [(0.1, 0.9), (0.9, 0.1), (0.2, 0.8), (0.8, 0.2)]
    report = reliability_stage(pairs_rows(noisy), DEFAULT_THRESHOLDS, repetitions=200)
    assert report["reliability_gate"]["passed"] is False
    assert report["stage"] == "stop_reliability"
    assert report["ceiling_gate"] is None


def test_stage_stops_at_the_ceiling_gate(monkeypatch):
    def fake_pairs(rows, metric, minimum_appearances=1):
        value = 0.355 if metric == "xg" else 0.2
        return {
            "pairs": [(0.1, 0.2), (0.2, 0.3), (0.3, 0.4)],
            "n_pairs": 3,
            "single_appearance_players": 0,
            "r_single": value,
            "metric": metric,
        }

    monkeypatch.setattr(st, "reliability_pairs", fake_pairs)
    monkeypatch.setattr(st, "bootstrap_pairs", lambda *a, **k: [0.3, 0.4])
    report = st.reliability_stage([], DEFAULT_THRESHOLDS, repetitions=200)
    assert report["reliability_gate"]["passed"] is True
    assert report["ceiling_gate"]["passed"] is False
    assert report["stage"] == "stop_ceiling"


def test_thresholds_reject_incoherent_values():
    with pytest.raises(ValueError):
        Thresholds(reliability_point=0.3, reliability_lower=0.4)
    with pytest.raises(ValueError):
        Thresholds(ceiling=0.0)
    with pytest.raises(ValueError):
        Thresholds(reliability_point=2.0)
