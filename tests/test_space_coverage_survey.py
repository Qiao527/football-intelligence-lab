"""Synthetic timestamps verify fixed sampling and do not depend on provider files."""

import runpy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
try:
    sampled_windows = runpy.run_path(str(SCRIPTS / "survey_space_coverage.py"))["sampled_windows"]
finally:
    sys.path.remove(str(SCRIPTS))


def test_fixed_frame_sampling_preserves_gaps_for_downstream_abstention():
    frames = [{"frame": i} for i in range(601) if i != 590]
    result = list(sampled_windows(frames))
    assert [center["frame"] for center, _ in result] == [0, 600]
    assert [frame["frame"] for frame in result[-1][1]] == [575, 580, 585, 595, 600]
    assert [f["frame"] for f, _ in sampled_windows(frames, interval=100)] == list(
        range(0, 601, 100)
    )
