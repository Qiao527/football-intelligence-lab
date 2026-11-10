"""Link a sampled snapshot to the current carrier's later provider-recorded action."""

from typing import Any

from fil.time.clock import ClockError, parse_period_timestamp


def valid_action_clock(center: dict, end: dict | None, period: int, max_frames: int = 30) -> bool:
    """Require source frames and clocks to agree at 10 Hz within a bounded window."""
    if not isinstance(end, dict) or center.get("period") != period or end.get("period") != period:
        return False
    first, last = center.get("frame"), end.get("frame")
    if type(first) is not int or type(last) is not int or not 0 < last - first <= max_frames:
        return False
    try:
        return (
            parse_period_timestamp(end.get("timestamp"))
            - parse_period_timestamp(center.get("timestamp"))
        ) == (last - first) * 100
    except ClockError:
        return False


def later_carrier_action(
    events: list[dict[str, str]],
    period: int,
    center: int,
    carrier: int,
    team: int,
    horizon_frames: int = 30,
) -> dict[str, Any]:
    """Use only a unique current player-possession ending strictly after the snapshot."""
    unknown = {
        "status": "insufficient_data",
        "reason": "",
        "event_id": None,
        "start_frame": None,
        "end_frame": None,
        "target_id": None,
        "pass_outcome": None,
    }
    try:
        active = [
            e
            for e in events
            if e["event_type"] == "player_possession"
            and int(e["period"]) == period
            and int(e["player_id"]) == carrier
            and int(e["team_id"]) == team
            and int(e["frame_start"]) <= center
            and center < int(e["frame_end"])
        ]
    except (KeyError, TypeError, ValueError):
        return {**unknown, "reason": "Malformed player-possession event."}
    if len(active) != 1:
        return {**unknown, "reason": "Current carrier possession is missing or ambiguous."}
    event = active[0]
    end = int(event["frame_end"])
    base = {
        **unknown,
        "event_id": event["event_id"],
        "start_frame": int(event["frame_start"]),
        "end_frame": end,
    }
    if end - center > horizon_frames:
        return {**base, "reason": "Carrier action ends outside the follow-up horizon."}
    if event.get("is_player_possession_end_matched") != "True":
        return {**base, "reason": "Provider did not certify tracking match for action end."}
    end_type = event.get("end_type")
    if not end_type or end_type == "unknown":
        return {**base, "reason": "Carrier action type is unknown."}
    if end_type != "pass":
        return {
            **base,
            "status": "non_pass_action",
            "reason": "Recorded carrier action is not a pass.",
        }
    target, outcome = event.get("player_targeted_id"), event.get("pass_outcome")
    if (
        not target
        or not str(target).isdigit()
        or outcome not in ("successful", "unsuccessful", "offside")
    ):
        return {**base, "reason": "Pass target or outcome is unknown."}
    return {
        **base,
        "status": "pass",
        "reason": "Provider-recorded pass after snapshot.",
        "target_id": int(target),
        "pass_outcome": outcome,
    }


def corroborate_reception(
    events: list[dict[str, str]], period: int, action: dict, team: int
) -> dict:
    """Check whether the first following provider possession records the target receiving."""
    result = {"status": "unconfirmed", "event_id": None, "frame_start": None}
    if action.get("status") != "pass" or action.get("pass_outcome") != "successful":
        return result
    end = action["end_frame"]
    try:
        later = [
            e
            for e in events
            if e["event_type"] == "player_possession"
            and int(e["period"]) == period
            and end < int(e["frame_start"]) <= end + 50
        ]
        if not later:
            return result
        earliest = min(int(e["frame_start"]) for e in later)
        first = [e for e in later if int(e["frame_start"]) == earliest]
        if len(first) != 1:
            return result
        event = first[0]
        if (
            int(event["player_id"]) != action["target_id"]
            or int(event["team_id"]) != team
            or event.get("start_type") != "pass_reception"
            or event.get("is_previous_pass_matched") != "True"
        ):
            return result
        return {
            "status": "provider_reception_corroborated",
            "event_id": event["event_id"],
            "frame_start": earliest,
        }
    except (KeyError, TypeError, ValueError):
        return result


def reception_followup(events: list[dict[str, str]], reception: dict) -> dict:
    """Read the corroborated receiver possession's ending action within five seconds."""
    unknown = {"status": "unconfirmed", "event_id": reception.get("event_id"), "end_frame": None}
    if reception.get("status") != "provider_reception_corroborated":
        return unknown
    matching = [e for e in events if e.get("event_id") == reception["event_id"]]
    if len(matching) != 1:
        return unknown
    event = matching[0]
    try:
        start, end = int(event["frame_start"]), int(event["frame_end"])
    except (KeyError, TypeError, ValueError):
        return unknown
    if (
        start != reception["frame_start"]
        or not 0 <= end - start <= 50
        or event.get("is_player_possession_end_matched") != "True"
    ):
        return unknown
    kind = event.get("end_type")
    if kind == "pass":
        outcome = event.get("pass_outcome")
        if outcome not in ("successful", "unsuccessful", "offside"):
            return unknown
        status = f"pass_{outcome}"
    elif kind and kind != "unknown":
        status = f"other_{kind}"
    else:
        return unknown
    return {"status": status, "event_id": event["event_id"], "end_frame": end}
