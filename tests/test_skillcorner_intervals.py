"""Artificial intervals cannot establish provider documentation."""

import runpy
from pathlib import Path

compare = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/audit_skillcorner_intervals.py")
)["compare_players"]


def test_interval_comparison_counts_differences_both_ways():
    players = [
        {
            "playing_time": {
                "sequences": [{"period": "period_1", "start_frame": 1, "end_frame": 5}],
                "by_period": [
                    {"name": "period_1", "start_frame": 1, "end_frame": 5},
                    {"name": "period_2", "start_frame": 6, "end_frame": 9},
                ],
            }
        },
        {"playing_time": {"by_period": []}},
    ]
    counts = compare(players)
    assert counts["sequence_exact_match"] == 1
    assert counts["period_rows"] == 2 and counts["period_exact_match"] == 1
    assert counts["different_period_sets"] == 1 and counts["players_without_sequences"] == 1
