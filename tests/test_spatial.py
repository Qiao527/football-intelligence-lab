"""TEST-ONLY spatial invariants; synthetic coordinates are not match observations."""

import pyarrow as pa
import pytest

from fil.metrics.shots import MetricError
from fil.metrics.spatial import spatial_report
from tests.test_score import clock, event


def fixture_table():
    records = []
    for period in (1, 2):
        for team in (1, 2):
            row = event(len(records) + 1, period, "00:01:00", "Shot", team)
            row["location"] = [108, 30]
            row["shot"]["end_location"] = [120, 40, 1]
            records.append(row)
    return clock(records)


def test_identity_frame_for_both_teams_in_both_periods_and_unknown_physical_ends():
    table = fixture_table()
    original = table.to_pylist()
    result = spatial_report(table)
    assert result["shot_positive_x_corroborated"]
    assert len(result["team_period_evidence"]) == 4
    assert all(g["physical_attacking_direction"] is None for g in result["team_period_evidence"])
    assert result["y_increases"] == "down" and result["origin"] == "upper_left"
    assert table.to_pylist() == original  # No second-half/team flip and no source mutation.


@pytest.mark.parametrize("value", [None, 0, 119])
def test_unsupported_goal_direction_remains_uncertified(value):
    table = fixture_table()
    rows = table.to_pylist()
    rows[-1]["end_x"] = value
    report = spatial_report(pa.Table.from_pylist(rows, schema=table.schema))
    assert not report["shot_positive_x_corroborated"]
    assert report["team_period_evidence"][-1]["shot_frame"] == "uncertified"


def test_no_shots_or_null_locations_never_establish_direction():
    table = clock(
        [
            event(1, 1, "00:00:00", "Half Start"),
            event(2, 1, "00:01:00", "Half End"),
        ]
    )
    result = spatial_report(table)
    assert not result["shot_positive_x_corroborated"]
    assert result["coordinate_nulls"]["x"] == 2


@pytest.mark.parametrize(
    "column,value",
    [
        ("coordinate_system", "spadl_105x68"),
        ("x", -1),
        ("end_y", 81),
        ("end_x", float("inf")),
        ("y", float("nan")),
    ],
)
def test_invalid_start_end_coordinates_or_frame_fail_closed(column, value):
    table = fixture_table()
    rows = table.to_pylist()
    rows[0][column] = value
    with pytest.raises(MetricError):
        spatial_report(pa.Table.from_pylist(rows, schema=table.schema))
