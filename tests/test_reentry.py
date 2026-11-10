"""TEST_ONLY records; no fabricated participant judgments or empirical football claims."""

from copy import deepcopy

import pytest

from fil.research import reentry


def event(i, start=50, end=60, kind="Pass", pid=1, team=1):
    e = dict(
        id=f"TEST_ONLY_{i}",
        index=i,
        period=1,
        timestamp=f"00:00:{i:02d}.000",
        type=dict(name=kind),
        team=dict(id=team),
        possession=pid,
        possession_team=dict(id=1),
        player=dict(id=10),
        location=[start, 20],
        play_pattern=dict(name="Regular Play"),
    )
    if kind in ("Pass", "Carry"):
        e[kind.lower()] = dict(end_location=[end, 20])
    if kind == "Shot":
        e["shot"] = dict(outcome=dict(name="Saved"), type=dict(name="Open Play"), statsbomb_xg=0.1)
    return e


def source():
    return dict(
        match_id=1,
        source_manifest_sha256="a" * 64,
        metadata=dict(
            match_id=1,
            home_team=dict(home_team_id=1, home_team_name="TEST_ONLY_A"),
            away_team=dict(away_team_id=2, away_team_name="TEST_ONLY_B"),
            home_score=0,
            away_score=0,
        ),
    )


def pattern():
    return [
        event(1, 60, 85),
        event(2, 85, 70),
        event(3, 70, 85),
        event(4, 85, 90),
        event(5, kind="Shot"),
        event(6, pid=2, team=2),
    ]


def extract(raw, variant="primary"):
    return reentry.extract(raw, source(), variant)[0]


def test_real_record_order_witness_and_future_cutoff():
    r = extract(pattern())
    assert r["feature"] is True and r["outcome"] == 1
    assert r["ordered_witnesses"] == [["TEST_ONLY_2", "TEST_ONLY_3"]]
    assert r["landmark_event_id"] == "TEST_ONLY_4"
    assert r["shot_event_ids"] == ["TEST_ONLY_5"]
    assert not r["exclusion_reasons"]


def test_cooccurrence_without_order_is_not_reentry():
    raw = pattern()
    raw[1] = event(2, 70, 85)
    raw[2] = event(3, 85, 70)
    r = extract(raw)
    assert r["cooccurrence"] and not r["feature"]
    assert r["ordered_witnesses"] == []


@pytest.mark.parametrize("mutation", ["null", "failed", "missing", "nonfinite", "bounds"])
def test_unknown_or_failed_landmark_is_not_negative_feature(mutation):
    raw = pattern()
    if mutation == "null":
        raw[1]["pass"]["outcome"] = None
    elif mutation == "failed":
        raw[1]["pass"]["outcome"] = dict(name="Incomplete")
    elif mutation == "missing":
        raw[1].pop("location")
    elif mutation == "nonfinite":
        raw[1]["location"][0] = float("nan")
    else:
        raw[1]["pass"]["end_location"][0] = 121
    r = extract(raw)
    assert r["feature"] is None
    assert "failed_or_unknown_landmark_geometry" in r["exclusion_reasons"]


def test_failed_earlier_move_prevents_certified_first_entry():
    raw = [event(0)] + pattern()
    raw[0]["pass"]["outcome"] = dict(name="Unknown")
    assert "first_entry_ambiguous_after_failed_or_unknown_move" in extract(raw)["exclusion_reasons"]


def test_shot_before_landmark_is_not_used_to_predict_itself():
    raw = pattern()
    raw.insert(2, event(99, kind="Shot"))
    for i, e in enumerate(raw, 1):
        e["index"] = i
    assert "shot_before_landmark" in extract(raw)["exclusion_reasons"]


def test_horizon_counts_ball_records_not_receipts_or_pressure():
    raw = pattern()[:4] + [event(5, kind="Pressure"), event(6), event(7, kind="Shot")]
    r = extract(raw)
    assert r["outcome"] == 1 and r["future_horizon_ids"] == ["TEST_ONLY_6", "TEST_ONLY_7"]


def test_three_record_negative_and_later_shot_are_different_outcomes():
    raw = pattern()[:4] + [event(i) for i in range(5, 8)] + [event(8, kind="Shot")]
    r = extract(raw)
    assert r["outcome"] == 0 and r["full_segment_outcome"] == 1
    assert r["shot_event_ids"] == [] and r["all_later_shot_ids"] == ["TEST_ONLY_8"]


def test_closed_short_negative_versus_unclosed_censoring():
    raw = pattern()[:4]
    assert extract(raw)["outcome"] is None
    assert extract(raw + [event(5, pid=2, team=2)])["outcome"] == 0
    raw.append(event(5, pid=None))
    assert extract(raw)["feature"] is True and extract(raw)["outcome"] is None


def test_reciprocal_half_end_closes_without_exact_time():
    raw = pattern()[:4]
    a, b = event(5, kind="Half End"), event(6, kind="Half End", team=2)
    a["related_events"], b["related_events"] = [b["id"]], [a["id"]]
    assert extract(raw + [a, b])["outcome"] == 0
    b["half_end"] = dict(early_video_end=True)
    assert extract(raw + [a, b])["outcome"] is None


def test_noncontiguous_id_and_period_change_are_blocked():
    raw = pattern()
    raw[2]["possession"] = None
    assert "noncontiguous_or_unassigned" in extract(raw)["exclusion_reasons"]
    raw = pattern()
    raw[-1]["possession"] = 1
    raw[-1]["period"] = 2
    assert "unsupported_or_cross_period" in extract(raw)["exclusion_reasons"]


def test_failure_to_reconcile_score_or_duplicate_ids_hard_fails():
    raw = pattern()
    raw[0]["id"] = raw[1]["id"]
    with pytest.raises(ValueError, match="Unique"):
        extract(raw)
    s = source()
    s["metadata"]["home_score"] = 1
    with pytest.raises(ValueError, match="score"):
        reentry.extract(pattern(), s, "primary")


def observation(motif, outcome, team=1, match=1):
    return dict(
        feature=motif,
        outcome=outcome,
        team_id=team,
        match_id=match,
        possession_id=f"TEST_ONLY_{motif}_{outcome}_{match}",
        pass_volume_bin="3-5",
        landmark_cell=[2, 0],
        window_passes=3,
        period=1,
        score_state="level",
    )


def test_context_comparison_does_not_pool_unsupported_teams_or_missing_labels():
    rows = [observation(True, 1), observation(False, None), observation(True, 0, team=2)]
    r = reentry.comparison(rows, True)
    assert r["matched_rows"] == 2 and r["excluded_no_arm_overlap"] == 1
    assert r["observed_difference"] is None and r["difference_bounds"] == [0, 1]


def test_conventional_aggregate_can_reverse_after_context_partition():
    # TEST_ONLY Simpson-style support: no football effect is asserted.
    rows = (
        [observation(True, 1)] * 9
        + [observation(True, 0)]
        + [observation(False, 1)]
        + [observation(False, 0)]
    )
    rows += (
        [observation(True, 0, team=2)] * 2
        + [observation(False, 0, team=2)] * 9
        + [observation(False, 1, team=2)]
    )
    adjusted = reentry.comparison(rows, True)
    assert adjusted["observed_difference"] < reentry.comparison(rows, False)["observed_difference"]


def test_repeat_pairs_require_distinct_matches_and_real_five_window_support():
    a = [observation(True, 1, match=1)] * 5
    b = [observation(False, 0, match=2)] * 4
    assert reentry.repeat_support(a + b)["pairs"] == []
    r = reentry.repeat_support(a + b + [deepcopy(b[0])])
    assert len(r["pairs"]) == 1 and r["pairs"][0]["same_team"]
    assert r["pairs_are_independent"] is False


def test_protocol_tampering_stops_before_source_io(tmp_path, monkeypatch):
    p = tmp_path / "protocol.md"
    p.write_text("changed")
    monkeypatch.setattr(reentry, "PROTOCOL", p)
    with pytest.raises(ValueError, match="protocol"):
        reentry.run(tmp_path / "absent", tmp_path, "a" * 40)
