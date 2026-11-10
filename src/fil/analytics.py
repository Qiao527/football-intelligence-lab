"""Analyze explicitly recorded local journey exports; never collect or transmit sessions."""

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

STAGES = ("discovery", "candidate", "player_profile", "evidence", "completed_investigation")


def analyze_journeys(data: dict[str, Any]) -> dict[str, Any]:
    """Compute sequential funnel, user-confirmed elapsed times, and reviewed guardrails.

    Sessions have ordered relative milliseconds and allowlisted stages only. Optional manual
    reviews contain boolean ``candidate_correct`` and ``unsupported_claim`` values; unreviewed
    sessions are excluded from those rates, and missing review data is never treated as success.
    """
    if not isinstance(data, dict) or set(data) != {"version", "sessions"}:
        raise ValueError("Expected a versioned session collection")
    if type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("Unsupported version")
    if not isinstance(data["sessions"], list):
        raise ValueError("Unsupported version or sessions")
    funnel = dict.fromkeys(STAGES, 0)
    times = []
    reviewed = []
    for session in data["sessions"]:
        if not isinstance(session, dict) or not {"events"} <= set(session) <= {"events", "review"}:
            raise ValueError("Invalid session fields")
        events = session["events"]
        if not isinstance(events, list) or not events or len(events) > len(STAGES):
            raise ValueError("Invalid journey length")
        last = -1
        for expected, event in zip(STAGES, events, strict=False):
            if not isinstance(event, dict) or set(event) != {"stage", "elapsed_ms"}:
                raise ValueError("Invalid event fields")
            ms = event["elapsed_ms"]
            if (
                event["stage"] != expected
                or isinstance(ms, bool)
                or not isinstance(ms, (int, float))
                or not math.isfinite(ms)
                or ms < last
                or ms < 0
            ):
                raise ValueError("Invalid stage or relative timestamp")
            last = ms
            funnel[expected] += 1
        if events[0]["elapsed_ms"] != 0:
            raise ValueError("Discovery must start at zero")
        if len(events) == len(STAGES):
            times.append(events[-1]["elapsed_ms"])
        if "review" in session:
            if len(events) < 2:
                raise ValueError("A review requires a candidate")
            review = session["review"]
            if (
                not isinstance(review, dict)
                or set(review) != {"candidate_correct", "unsupported_claim"}
                or not all(isinstance(value, bool) for value in review.values())
            ):
                raise ValueError("Invalid manual review")
            reviewed.append(review)
    count = len(reviewed)
    return {
        "sessions": len(data["sessions"]),
        "funnel": funnel,
        "completed_investigations": len(times),
        "median_time_to_user_confirmed_insight_ms": statistics.median(times) if times else None,
        "reviewed_sessions": count,
        "candidate_accuracy": (
            sum(r["candidate_correct"] for r in reviewed) / count if count else None
        ),
        "unsupported_claim_rate": sum(r["unsupported_claim"] for r in reviewed) / count
        if count
        else None,
        "note": "Completion is user-reported; guardrails require manual review.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Local JSON journey export")
    args = parser.parse_args()
    print(json.dumps(analyze_journeys(json.loads(args.input.read_text())), indent=2))


if __name__ == "__main__":
    main()
