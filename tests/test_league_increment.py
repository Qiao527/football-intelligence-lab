"""TEST_ONLY increment test: rank correlations, shrinkage and labels."""

import pytest

from fil.research.league_increment import (
    IncrementSettings,
    average_ranks,
    run,
    score_players,
    spearman,
    top_overlap,
)


def test_average_ranks_share_ties():
    assert average_ranks([3.0, 1.0, 3.0, 2.0]) == [3.5, 1.0, 3.5, 2.0]
    assert average_ranks([1.0, 2.0, 3.0]) == [1.0, 2.0, 3.0]


def test_spearman_is_monotone_and_guarded():
    assert spearman([1, 2, 3], [10, 20, 30]) == pytest.approx(1.0)
    assert spearman([1, 2, 3], [30, 20, 10]) == pytest.approx(-1.0)
    assert spearman([1, 2], [1, 2]) is None
    assert spearman([1, 1, 1], [1, 2, 3]) is None


def test_shrinkage_moves_toward_the_group_rate():
    aggregated = {
        (1, 10): {"appearances": {"A": 10, "B": 10}, "goals": 5.0, "xg": 2.0,
                  "op_npxg": 2.0, "xg_b": 2.0, "positions": {"Forward": 10}},
        (2, 10): {"appearances": {"A": 10, "B": 10}, "goals": 0.0, "xg": 0.0,
                  "op_npxg": 0.0, "xg_b": 0.0, "positions": {"Forward": 10}},
        (3, 10): {"appearances": {"A": 10, "B": 10}, "goals": 0.0, "xg": 1.0,
                  "op_npxg": 1.0, "xg_b": 1.0, "positions": {"Forward": 10}},
    }
    scored = score_players(aggregated, IncrementSettings(prior_appearances=10.0))
    assert scored[(1, 10)]["c0"] < 0.5
    assert scored[(1, 10)]["c0"] > scored[(2, 10)]["c0"]
    assert scored[(1, 10)]["criterion"] == pytest.approx(0.2)


def synthetic(players=40, stable=True):
    """Window-A xG tracks window-B xG; goals are made noisy on purpose."""
    aggregated = {}
    for i in range(players):
        base = 0.05 + (i % 8) * 0.05
        jitter = 0.0 if stable else ((i * 37) % 11 - 5) * 0.02
        aggregated[(i + 1, 10)] = {
            "appearances": {"A": 12, "B": 12},
            "goals": round(max(0.0, base * 2 + ((i * 13) % 7 - 3) * 0.3), 3),
            "xg": base * 12,
            "op_npxg": base * 12,
            "xg_b": max(0.0, base + jitter) * 12,
            "positions": {"Forward": 12},
        }
    return aggregated


def test_scores_and_criterion_are_window_separated():
    scored = score_players(synthetic())
    assert all(0 <= v["c0"] <= 3 for v in scored.values())
    assert all(0 <= v["criterion"] <= 3 for v in scored.values())


def test_run_reports_paired_difference_and_labels():
    aggregated = synthetic()
    players = sorted(aggregated)
    rows = []
    for key, record in aggregated.items():
        rows.append({"player_id": key[0], "team_id": key[1], "window": "A",
                     "goals": record["goals"], "xg": record["xg"],
                     "op_npxg": record["op_npxg"], "position_names": ("Forward",)})
        rows.append({"player_id": key[0], "team_id": key[1], "window": "B",
                     "goals": 0.0, "xg": record["xg_b"], "op_npxg": record["xg_b"],
                     "position_names": ("Forward",)})
    report = run(rows, players, repetitions=200)
    assert report["players"] == len(players)
    assert report["intervals"]["c1_minus_c0"][0] <= report["intervals"]["c1_minus_c0"][1]
    assert report["labels"]["primary_c1_c0"]["label"] in {
        "increment", "no_detectable_increment", "inconclusive", "uninformative",
        "adverse",
    }
    assert report["top_overlap"]["c1"] is not None


def test_top_overlap_is_bounded():
    scored = score_players(synthetic())
    value = top_overlap(scored, "c1", 5)
    assert 0 <= value <= 1
    assert top_overlap(scored, "c1", 10_000) is None


def test_run_rejects_too_few_players():
    with pytest.raises(ValueError):
        run([], [], repetitions=200)


def test_fewer_appearances_still_score_with_the_prior():
    aggregated = synthetic()
    aggregated[(999, 10)] = {"appearances": {"A": 1, "B": 1}, "goals": 1.0,
                             "xg": 1.0, "op_npxg": 1.0, "xg_b": 0.0,
                             "positions": {"Forward": 1}}
    scored = score_players(aggregated)
    assert (999, 10) in scored
    assert scored[(999, 10)]["c0"] < 1.0
