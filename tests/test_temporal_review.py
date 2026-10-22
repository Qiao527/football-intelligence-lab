"""TEST_ONLY uncertainty hypotheses and development/test separation."""

import copy

import pytest

from fil.research.baseline_audit import DEVELOPMENT, shrinkage_development
from fil.time.uncertainty import envelopes, exposure_sensitivity


def example(end=10200):
    records = []

    def add(kind, ms, team=1, player=None, **detail):
        i = len(records) + 1
        records.append(
            dict(
                id=f"TEST-{i}",
                index=i,
                period=1,
                timestamp=f"00:00:{ms // 1000:02}.{ms % 1000:03}",
                type={"name": kind},
                team={"id": team},
                **({"player": {"id": player}} if player else {}),
                **detail,
            )
        )

    for team, first in [(1, 1), (2, 21)]:
        add(
            "Starting XI",
            0,
            team,
            tactics=dict(lineup=[dict(player=dict(id=p)) for p in range(first, first + 11)]),
        )
    add("Half Start", 0)
    add("Half Start", 0, 2)
    records[2]["related_events"] = [records[3]["id"]]
    records[3]["related_events"] = [records[2]["id"]]
    add("Player Off", 5000, player=1)
    add("Player On", 8000, player=1)
    add("Pass", 9000, player=1, duration=0.5)
    add("Half End", 10000)
    add("Half End", end, 2)
    records[-2]["related_events"] = [records[-1]["id"]]
    records[-1]["related_events"] = [records[-2]["id"]]
    roster = [
        dict(team_id=t, player_id=p)
        for t, first in [(1, 1), (2, 21)]
        for p in range(first, first + 11)
    ] + [dict(team_id=1, player_id=12)]
    return records, roster


def test_conditional_envelope_never_selects_physical_boundary_or_changes_source():
    raw, roster = example()
    before = copy.deepcopy(raw)
    model = envelopes(raw, {1, 2})
    assert raw == before
    p = model["periods"][0]
    assert p["observed_end_envelope_ms"] == [10000, 10200]
    assert p["exact_physical_end_ms"] is None and not p["physical_end_certified"]
    assert not model["expansion_authorized"] and model["status"] == "PROPOSED_NOT_ACCEPTED"
    x = exposure_sensitivity(raw, roster, model)
    assert not x["issues"]
    assert next(p for p in x["players"] if p["player_id"] == 1)[
        "conditional_recorded_exposure_ms"
    ] == [7000, 7200]
    assert (
        next(p for p in x["players"] if p["player_id"] == 12)["conditional_recorded_exposure_ms"]
        is None
    )
    assert all(p["official_minutes"] is None and not p["per90_eligible"] for p in x["players"])


@pytest.mark.parametrize("bad", ["unlinked", "missing", "video", "clock", "edge", "period"])
def test_invalid_or_boundary_sensitive_evidence_remains_unresolved(bad):
    raw, roster = example()
    if bad == "unlinked":
        raw[-1]["related_events"] = []
    if bad == "missing":
        raw.pop()
    if bad == "video":
        raw[-1]["half_end"] = {"early_video_end": True}
    if bad == "clock":
        raw[6]["timestamp"] = "00:00:04.000"
    if bad == "edge":
        raw[6]["timestamp"] = "00:00:10.000"
    if bad == "period":
        for e in raw:
            e["period"] = 2
    m = envelopes(raw, {1, 2})
    assert not m["periods"][0]["conditional_eligible"]
    assert m["conditional_recorded_match_duration_ms"] is None
    assert exposure_sensitivity(raw, roster, m)["status"] == "unresolved"


def test_equal_markers_and_fractional_duration_are_not_rounded():
    raw, _ = example(10000)
    assert envelopes(raw, {1, 2})["conditional_recorded_match_duration_ms"] == [10000, 10000]
    raw[6]["timestamp"] = "00:00:09.999"
    raw[6]["duration"] = 0.0015
    assert envelopes(raw, {1, 2})["periods"][0]["known_duration_overlap_ids"] == [raw[6]["id"]]
    raw[-1]["index"] = raw[-2]["index"]
    with pytest.raises(ValueError, match="index"):
        envelopes(raw, {1, 2})


def test_census_contradictions_do_not_produce_exposure_ranges():
    raw, roster = example()
    raw[5]["player"]["id"] = 2
    x = exposure_sensitivity(raw, roster, envelopes(raw, {1, 2}))
    assert x["issues"] and all(p["conditional_recorded_exposure_ms"] is None for p in x["players"])


def test_development_shrinkage_never_accepts_reported_test_or_exposed_fixture():
    rows = [
        dict(match_id=m, outcome=y, features=dict(context="TEST", location="0:0"))
        for m in sorted(DEVELOPMENT)
        for y in (0, 1, 0)
    ]
    before = copy.deepcopy(rows)
    result = shrinkage_development(rows)
    assert rows == before and not result["test_scored"] and not result["scientifically_validated"]
    assert all(v["alpha_match_equivalent_mass"] == 4 for v in result["families"].values())
    for mid in (8655, 8658):
        with pytest.raises(ValueError, match="forbidden"):
            shrinkage_development(rows + [dict(rows[0], match_id=mid)])
