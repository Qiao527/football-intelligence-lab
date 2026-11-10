"""Pinned StatsBomb Pass/Carry adapter; missing outcomes have a narrow native meaning."""

import json
import math
from collections import Counter

import pyarrow as pa

from fil.metrics.shots import event_score_state
from fil.metrics.tactics import (
    ACTION_SCHEMA,
    TacticalError,
    TacticalFacts,
    passing_network,
    progression,
)

FAILURES = {9: "Incomplete", 74: "Injury Clearance", 75: "Out", 76: "Pass Offside"}


def extract_tactics(events: pa.Table, home: int, away: int) -> TacticalFacts:
    """Keep an audit row for every pass/carry; never coerce null/unknown to completion."""
    ids = events["event_id"].to_pylist()
    if len(ids) != len(set(ids)):
        raise TacticalError("Duplicate original IDs")
    fields = [
        "event_id",
        "event_type",
        "source",
        "source_record_json",
        "team_id",
        "player_id",
        "recipient_player_id",
        "period",
        "provider_index",
        "period_elapsed_ms",
        "display_clock",
        "period_timestamp",
        "match_id",
        "x",
        "y",
        "end_x",
        "end_y",
        "coordinate_system",
        "source_manifest_sha256",
        "score_home_before",
        "score_away_before",
    ]
    candidates = events.filter(
        pa.array([v in ("Pass", "Carry") for v in events["event_type"].to_pylist()])
    )
    output = []
    for row in candidates.select(fields).to_pylist():
        if (
            row["source"] != "statsbomb_open_data"
            or row["coordinate_system"] != "raw_statsbomb_120x80"
        ):
            raise TacticalError("Unsupported provider/coordinate contract")
        source = json.loads(row["source_record_json"])
        if (
            source.get("id") != row["event_id"]
            or source.get("type", {}).get("name") != row["event_type"]
            or (source.get("team") or {}).get("id") != row["team_id"]
            or (source.get("player") or {}).get("id") != row["player_id"]
            or source.get("index") != row["provider_index"]
            or source.get("period") != row["period"]
            or source.get("timestamp") != row["period_timestamp"]
        ):
            raise TacticalError("Action identity differs from original source")
        detail = source.get("pass" if row["event_type"] == "Pass" else "carry")
        if not isinstance(detail, dict):
            raise TacticalError("Missing native action object")
        for cols, values in (
            (("x", "y"), source.get("location") or []),
            (("end_x", "end_y"), detail.get("end_location") or []),
        ):
            for index, name in enumerate(cols):
                if row[name] != (values[index] if len(values) > index else None):
                    raise TacticalError("Canonical endpoint differs from source")
        recipient = detail.get("recipient")
        recipient_id = recipient.get("id") if isinstance(recipient, dict) else None
        status, reason = "observed_carry", "native_carry; no retained_possession_claim"
        if row["event_type"] == "Carry" and "outcome" in detail:
            status, reason = "unknown", "unsupported_carry_outcome"
        if row["event_type"] == "Pass":
            if row["recipient_player_id"] != recipient_id:
                raise TacticalError("Recipient differs from original source")
            status, reason = "unknown", "unsupported_or_explicit_null_outcome"
            if "outcome" in detail:
                outcome = detail["outcome"]
                if isinstance(outcome, dict) and FAILURES.get(outcome.get("id")) == outcome.get(
                    "name"
                ):
                    status, reason = "failed", outcome["name"]
                elif outcome == {"id": 77, "name": "Unknown"}:
                    reason = "provider_unknown"
            else:
                # These required native fields distinguish a supported Pass object
                # from arbitrary missing data. Coordinates may remain null.
                numeric = all(
                    type(detail.get(k)) in (int, float) and math.isfinite(detail[k])
                    for k in ("length", "angle")
                )
                height = detail.get("height")
                contract = (
                    numeric
                    and detail["length"] >= 0
                    # Native float32-like angle rounding includes 3.1415927.
                    and -math.pi - 1e-6 <= detail["angle"] <= math.pi + 1e-6
                    and isinstance(height, dict)
                    and type(height.get("id")) is int
                    and {1: "Ground Pass", 2: "Low Pass", 3: "High Pass"}.get(height["id"])
                    == height.get("name")
                )
                if contract:
                    status, reason = "completed", "native_outcome_absent"
                else:
                    reason = "unsupported_pass_contract"
            if status == "completed" and (type(recipient_id) is not int or recipient_id <= 0):
                status, reason = "excluded", "missing_or_invalid_recipient"
        if (
            row["team_id"] not in (home, away)
            or type(row["player_id"]) is not int
            or row["player_id"] <= 0
        ):
            status, reason = "excluded", "missing_or_invalid_actor"
        if row["period"] not in (1, 2, 3, 4):
            status, reason = "excluded", "outside_match_play"
        result = {k: row[k] for k in ACTION_SCHEMA.names if k in row}
        result.update(
            {
                "recipient_id": recipient_id if type(recipient_id) is int else None,
                "player_name": (source.get("player") or {}).get("name"),
                "recipient_name": recipient.get("name") if isinstance(recipient, dict) else None,
                "status": status,
                "reason": reason,
                "score_state": event_score_state(row, home, away),
            }
        )
        output.append({**result, **progression(result)})
    actions = pa.Table.from_pylist(output, schema=ACTION_SCHEMA)
    edges, nodes = passing_network(actions)
    quality = {
        "source_rows": events.num_rows,
        "action_rows": actions.num_rows,
        "pass_rows": sum(r["event_type"] == "Pass" for r in output),
        "status_counts": dict(Counter(r["status"] for r in output)),
        "reason_counts": dict(Counter(r["reason"] for r in output)),
        "physical_directions": "unknown; no flip or tracking",
        "position_basis": "mean completed-pass origins; event samples, not formation",
        "progression_basis": "native +x convention, >=10 provider-unit goal-distance gain",
        "progression_unresolved": sum(
            r["status"] in ("completed", "observed_carry") and r["progressive"] is None
            for r in output
        ),
    }
    return TacticalFacts(actions, edges, nodes, quality)
