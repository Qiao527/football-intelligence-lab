"""Synthetic joins check lineage and review masking; provider labels are weak references."""

import runpy
from pathlib import Path

module = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/compare_provider_labels.py")
)
overlaps = module["overlapping_labels"]
review_sample = module["review_sample"]


def test_same_player_period_and_inclusive_overlap_are_required():
    events = [
        {
            "event_type": "off_ball_run",
            "event_id": str(i),
            "player_id": player,
            "period": period,
            "frame_start": start,
            "frame_end": end,
        }
        for i, player, period, start, end in [
            (1, "7", "1", "70", "80"),
            (2, "7", "1", "101", "110"),
            (3, "8", "1", "80", "100"),
            (4, "7", "2", "80", "100"),
        ]
    ]
    assert overlaps(events, 7, 1, 80, 100) == {"off_ball_run": ["1"], "passing_option": []}


def test_sample_covers_strata_and_avoids_nearby_windows():
    rows = []
    for index, (status, ref) in enumerate(
        [
            ("candidate", True),
            ("candidate", False),
            ("not_candidate", True),
            ("not_candidate", False),
        ]
    ):
        rows.append(
            {
                "match_id": str(index),
                "frame": 600,
                "screen_status": status,
                "provider_event_ids": {"off_ball_run": ["x"] if ref else [], "passing_option": []},
            }
        )
    assert len(review_sample({"rows": rows})) == 4
