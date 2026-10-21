"""Audit the provider coordinate frame without constructing physical pitch directions."""

import math
from collections import defaultdict

import pyarrow as pa

from fil.metrics.shots import MetricError

SPATIAL_VERSION = "fil-statsbomb-spatial-1"
COORDINATE_SYSTEM = "raw_statsbomb_120x80"
SPATIAL_REFERENCE = {
    "url": "https://github.com/hudl/open-data/blob/"
    "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/doc/Open%20Data%20Events%20v4.0.0.pdf",
    "sha256": "05de42cc76b0c9cd26213d8e5c72610cac7d4d92c9c2ac878073a565dbb6c44a",
    "section": "Appendix 2, page 23: (0,0) upper left, (120,80) lower right",
}


def spatial_report(events: pa.Table) -> dict:
    """Validate start/end bounds; keep identity mapping and explicit direction uncertainty.

    Goal endpoints can corroborate a shot frame in each observed team/period. They
    cannot certify physical stadium ends or direction conventions for every event type.
    No half/home-away rotation, coordinate repair, or tracking is inferred.
    """
    fields = [
        "event_id",
        "period",
        "team_id",
        "coordinate_system",
        "event_type",
        "x",
        "y",
        "end_x",
        "end_y",
        "shot_outcome",
    ]
    rows = events.select(fields).to_pylist()
    groups = defaultdict(list)
    nulls = dict.fromkeys(("x", "y", "end_x", "end_y"), 0)
    for row in rows:
        if row["coordinate_system"] != COORDINATE_SYSTEM:
            raise MetricError("Unsupported coordinate frame; refusing an implicit conversion")
        for name, bound in (("x", 120), ("y", 80), ("end_x", 120), ("end_y", 80)):
            value = row[name]
            if value is None:
                nulls[name] += 1
            elif not math.isfinite(value) or not 0 <= value <= bound:
                raise MetricError(f"Out-of-bounds provider coordinate {name}: {row['event_id']}")
        if row["period"] in (1, 2, 3, 4) and row["team_id"] is not None:
            groups[row["team_id"], row["period"]].append(row)
    evidence = []
    for (team, period), group in sorted(groups.items()):
        shots = [r for r in group if r["event_type"] == "Shot"]
        goals = [r for r in shots if r["shot_outcome"] == "Goal"]
        consistent = bool(goals) and all(r["end_x"] == 120 for r in goals)
        evidence.append(
            {
                "team_id": team,
                "period": period,
                "shot_count": len(shots),
                "goal_event_ids": [r["event_id"] for r in goals],
                "goal_end_x": [r["end_x"] for r in goals],
                "shot_frame": "positive_x_consistent" if consistent else "uncertified",
                "physical_attacking_direction": None,
            }
        )
    corroborated = bool(evidence) and all(
        g["shot_frame"] == "positive_x_consistent" for g in evidence
    )
    return {
        "version": SPATIAL_VERSION,
        "coordinate_system": COORDINATE_SYSTEM,
        "extent": [120, 80],
        "units": "provider pitch units, not metres",
        "origin": "upper_left",
        "y_increases": "down",
        "display_transform": "identity; original x/y retained",
        "action_attacking_ltr": "identity consistent for fixture shots; not universally certified"
        if corroborated
        else "uncertified; source coordinates retained",
        "shot_positive_x_corroborated": corroborated,
        "world_fixed": "unknown; no certified team/period physical direction available",
        "reference": SPATIAL_REFERENCE,
        "event_count": len(rows),
        "coordinate_nulls": nulls,
        "team_period_evidence": evidence,
        "limits": [
            "Goal endpoint evidence does not establish physical attacking ends",
            "No home/away or period flip; no universal non-shot direction certification",
            "Event coordinates are not continuous player tracking",
        ],
    }
