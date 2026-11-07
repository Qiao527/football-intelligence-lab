"""Synthetic-only tests for privacy boundaries and product metrics."""

import pytest

from fil.analytics import STAGES, analyze_journeys


def session(n, review=None):
    result = {
        "events": [
            {"stage": stage, "elapsed_ms": i * 1000} for i, stage in enumerate(STAGES[:n])
        ]
    }
    if review is not None:
        result["review"] = review
    return result


def test_funnel_timing_and_reviewed_denominators():
    data = {
        "version": 1,
        "sessions": [
            session(5, {"candidate_correct": True, "unsupported_claim": False}),
            session(3),
            session(5, {"candidate_correct": False, "unsupported_claim": True}),
        ],
    }
    result = analyze_journeys(data)
    assert list(result["funnel"].values()) == [3, 3, 3, 2, 2]
    assert result["median_time_to_user_confirmed_insight_ms"] == 4000
    assert result["reviewed_sessions"] == 2
    assert result["candidate_accuracy"] == result["unsupported_claim_rate"] == 0.5
    assert analyze_journeys({"version": 1, "sessions": [session(1)]})["candidate_accuracy"] is None


def test_rejects_private_fields_and_invalid_journeys():
    bad = session(2)
    bad["events"][1]["prompt"] = "private query"
    with pytest.raises(ValueError):
        analyze_journeys({"version": 1, "sessions": [bad]})
    bad = session(2)
    bad["events"][1]["stage"] = "evidence"
    with pytest.raises(ValueError):
        analyze_journeys({"version": 1, "sessions": [bad]})
    bad = session(2)
    bad["events"][1]["elapsed_ms"] = -1
    with pytest.raises(ValueError):
        analyze_journeys({"version": 1, "sessions": [bad]})
