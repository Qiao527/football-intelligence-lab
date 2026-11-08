"""The review queue never turns sampled frames into video validation."""

import runpy
from pathlib import Path

import pytest

queue = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/prepare_skillcorner_review.py")
)["review_queue"]


def test_queue_separates_nearby_frames_and_marks_them_unreviewed():
    probe = {
        "status": "EXPLORATORY_NOT_VALIDATED",
        "match_id": "TEST_ONLY",
        "source_revision": "TEST_ONLY",
        "file_sha256": {},
        "observations": [
            {"period": 1, "frame_id": frame, "timestamp": str(frame), "options": [{"player_id": 1}]}
            for frame in (100, 110, 699, 700)
        ],
    }
    result = queue(probe)
    assert [x["frame_id"] for x in result["items"]] == [100, 700]
    assert all(x["visibility"] == "NOT_REVIEWED" for x in result["items"])
    assert all(x["geometric_screen_correct"] is None for x in result["items"])
    probe["status"] = "FAIL"
    with pytest.raises(ValueError):
        queue(probe)
