"""Metric-specific diagnostic proposal; never a replacement acquisition gate."""

import hashlib
import json
import math
from collections import defaultdict

from fil.ingestion.statsbomb_score import official_score, scoring_signals
from fil.research.acquisition import REVISION
from fil.time.clock import parse_period_timestamp
from fil.time.uncertainty import envelopes, exposure_sensitivity

VERSION = "fil-metric-eligibility-proposal-1"


def ordered_score(raw: list[dict], metadata: dict) -> dict:
    """Reconcile native order without creating a clock or assuming physical endpoints.

    Own-goal perspectives require explicit source links and matching native times.
    Shootout success is separate and is not certified against match-play metadata.
    """
    official = official_score([metadata], metadata["match_id"])
    teams = (official.home_team_id, official.away_team_id)
    by = {e["id"]: e for e in raw}
    signals = {s.event_id: s for s in scoring_signals(raw)}
    adjacency = {i: set() for i in signals}
    for i, signal in signals.items():
        if signal.team_id not in teams or i in signal.related_event_ids:
            raise ValueError("Invalid scoring identity/link")
        for j in signal.related_event_ids:
            if j not in by:
                raise ValueError("Unavailable scoring link")
            if j in signals:
                adjacency[i].add(j)
                adjacency[j].add(i)
    visited, own_instants, decisions = set(), set(), []
    for i in signals:
        if i in visited:
            continue
        component, pending = {i}, [i]
        while pending:
            for j in adjacency[pending.pop()] - component:
                component.add(j)
                pending.append(j)
        visited.update(component)
        ids = sorted(component, key=lambda j: by[j]["index"])
        members = [signals[j] for j in ids]
        first = by[ids[0]]
        if len(ids) > 1 and (
            len(ids) != 2
            or {s.kind for s in members} != {"own_for", "own_against"}
            or len({(by[j]["period"], by[j]["timestamp"]) for j in ids}) != 1
            or len({s.team_id for s in members}) != 2
        ):
            raise ValueError("Ambiguous scoring representations")
        own = members[0].kind != "shot"
        if own:
            instant = (first["period"], first["timestamp"])
            if instant in own_instants or first["period"] == 5:
                raise ValueError("Unlinked own-goal representations or invalid shootout")
            own_instants.add(instant)
            beneficiary = next(
                (s.team_id for s in members if s.kind == "own_for"),
                teams[1 - teams.index(members[0].team_id)],
            )
        else:
            beneficiary = members[0].team_id
            if first["period"] == 5 and not members[0].penalty:
                raise ValueError("Non-penalty shootout record")
        decisions.append(
            dict(
                source_event_ids=ids,
                provider_index=first["index"],
                period=first["period"],
                beneficiary_team_id=beneficiary,
                scored=members[0].scored,
                domain="shootout" if first["period"] == 5 else "match_play",
            )
        )
    totals = {"match_play": [0, 0], "shootout": [0, 0]}
    for d in decisions:
        if d["scored"]:
            totals[d["domain"]][teams.index(d["beneficiary_team_id"])] += 1
    if totals["match_play"] != [official.home_score, official.away_score]:
        raise ValueError("Native-order score disagrees with official metadata")
    return dict(
        **totals,
        decisions=decisions,
        shootout_official_reconciliation="unavailable",
        physical_timing_certified=False,
    )


def source_clock_difference(first: dict, second: dict, model: dict) -> dict:
    """Propagate correlated period prefixes once; never report physical elapsed time."""
    if first["index"] >= second["index"] or first["period"] > second["period"]:
        raise ValueError("Strict provider-order pair required")
    if any(e["id"] not in model["event_ids"] for e in (first, second)):
        raise ValueError("Foreign source event identity")
    a, b = first["period"], second["period"]
    if a not in (1, 2, 3, 4) or b not in (1, 2, 3, 4):
        raise ValueError("Match-play source periods required")
    periods = {p["period"]: p for p in model["periods"]}
    if a != b and any(
        p not in periods or not periods[p]["conditional_eligible"] for p in range(a, b + 1)
    ):
        raise ValueError("Unresolved source boundary/order")
    delta = parse_period_timestamp(second["timestamp"]) - parse_period_timestamp(first["timestamp"])
    bounds = [delta, delta]
    for p in range(a, b):
        for k in (0, 1):
            bounds[k] += periods[p]["observed_end_envelope_ms"][k]
    if bounds[0] < 0:
        raise ValueError("Negative source interval")
    return dict(
        version=VERSION,
        source_event_ids=[first["id"], second["id"]],
        source_clock_difference_ms=bounds,
        dependency_periods=list(range(a, b)),
        support="fully_supported" if a == b else "conditionally_supported",
        physical_elapsed_ms=None,
        physical_timing_certified=False,
    )


def assess(
    raw_bytes: bytes,
    expected_sha256: str,
    canonical: list[dict],
    metadata: dict,
    roster: list[dict] | None = None,
    *,
    source_manifest_sha256: str,
) -> dict:
    """Evaluate held verified-source evidence. Expected hash comes from upstream verifier.

    A result is diagnostic eligibility *under this proposal*, not permission to
    acquire, deploy or publish. Missing geometry excludes affected records only.
    """
    raw = json.loads(raw_bytes)
    rows = {}

    def result(name, supported, reasons=(), **evidence):
        rows[name] = dict(support=supported, reasons=list(reasons), **evidence)

    identity_errors = []
    if hashlib.sha256(raw_bytes).hexdigest() != expected_sha256:
        identity_errors.append("upstream_payload_hash_mismatch")
    if not raw or len(raw) != len(canonical) or len({e["id"] for e in raw}) != len(raw):
        identity_errors.append("event_count_or_identity_mismatch")
    teams = {metadata[k][k + "_id"] for k in ("home_team", "away_team")}
    for n, (e, r) in enumerate(zip(raw, canonical, strict=False)):
        projection = {
            "event_id": e["id"],
            "provider_index": e["index"],
            "period": e["period"],
            "period_timestamp": e["timestamp"],
            "event_type": e["type"]["name"],
            "team_id": e["team"]["id"],
            "player_id": e.get("player", {}).get("id"),
            "possession_id": e.get("possession"),
            "possession_team_id": e.get("possession_team", {}).get("id"),
            "raw_event_row": n,
            "match_id": metadata["match_id"],
            "source": "statsbomb_open_data",
            "source_revision": expected_sha256,
            "source_manifest_sha256": source_manifest_sha256,
            "upstream_revision": REVISION,
        }
        detail_key = {
            "Pass": "pass",
            "Shot": "shot",
            "Carry": "carry",
            "Dribble": "dribble",
            "Duel": "duel",
            "Interception": "interception",
            "Ball Receipt*": "ball_receipt",
            "Goal Keeper": "goalkeeper",
            "50/50": "50_50",
        }.get(e["type"]["name"])
        detail = e.get(detail_key, {}) if detail_key else {}
        for point, prefix in [(e.get("location"), ""), (detail.get("end_location"), "end_")]:
            for offset, axis in enumerate(("x", "y", "z")):
                projection[prefix + axis] = point[offset] if point and len(point) > offset else None
        projection["shot_xg"] = detail.get("statsbomb_xg") if e["type"]["name"] == "Shot" else None
        projection["duration_s"] = e.get("duration")
        projection["coordinate_system"] = "raw_statsbomb_120x80"
        projection["related_event_ids"] = e.get("related_events")
        projection["recipient_player_id"] = (detail.get("recipient") or {}).get("id")
        for kind in ("Pass", "Shot"):
            projection[kind.lower() + "_outcome"] = (
                (detail.get("outcome") or {}).get("name") if e["type"]["name"] == kind else None
            )
        projection["shot_type"] = (
            (detail.get("type") or {}).get("name") if e["type"]["name"] == "Shot" else None
        )
        if (
            any(r.get(k) != v for k, v in projection.items())
            or json.loads(r.get("source_record_json", "null")) != e
        ):
            identity_errors.append(f"canonical_source_projection_mismatch:{e['id']}")
        if e["team"]["id"] not in teams or e.get("possession_team", {}).get("id") not in teams:
            identity_errors.append(f"foreign_team:{e['id']}")
    result(
        "source_identity",
        "blocked" if identity_errors else "fully_supported",
        identity_errors,
        original_event_count=len(raw),
        payload_sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )
    if identity_errors:
        for name in (
            "event_order",
            "score",
            "native_spatial",
            "physical_spatial",
            "within_period_source_clock",
            "known_completion_boundary_invariance",
            "cross_period_envelope",
            "recorded_census_envelope",
            "exact_time_exposure",
        ):
            result(name, "blocked", ["source_identity_failed"])
        return _report(metadata, rows)
    order_errors = []
    keys = [(e["period"], e["index"]) for e in raw]
    if keys != sorted(set(keys)) or any(a[1] >= b[1] for a, b in zip(keys, keys[1:], strict=False)):
        order_errors.append("duplicate_or_reversing_source_order")
    if {e["period"] for e in raw if e["period"] < 5} not in ({1, 2}, {1, 2, 3, 4}):
        order_errors.append("incomplete_match_periods")
    result("event_order", "blocked" if order_errors else "fully_supported", order_errors)
    try:
        if order_errors:
            raise ValueError("event_order_failed")
        score = ordered_score(raw, metadata)
        result("score", "fully_supported", **score)
    except ValueError as exc:
        result("score", "blocked", [str(exc)])
    spatial = defaultdict(list)
    for e in raw:
        if e["period"] == 5 or e["type"]["name"] not in ("Pass", "Carry", "Shot"):
            continue
        points = [e.get("location")]
        if e["type"]["name"] in ("Pass", "Carry"):
            points.append(e[e["type"]["name"].lower()].get("end_location"))
        reason = "valid"
        for point in points:
            if point is None:
                reason = "missing_geometry" if reason == "valid" else reason
            elif len(point) < 2 or any(
                type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= limit
                for v, limit in zip(point[:2], (120, 80), strict=False)
            ):
                reason = "invalid_geometry"
                break
        spatial[reason].append(e["id"])
    result(
        "native_spatial",
        "blocked"
        if spatial["invalid_geometry"]
        else "conditionally_supported"
        if spatial["missing_geometry"]
        else "fully_supported",
        coordinate_system="raw_statsbomb_120x80",
        physical_direction_certified=False,
        **dict(spatial),
        missing_as_zero=False,
    )
    result("physical_spatial", "blocked", ["no_physical_orientation_or_tracking_certification"])
    clocks = defaultdict(list)
    try:
        for e in raw:
            if e["period"] in (1, 2, 3, 4):
                clocks[e["period"]].append(parse_period_timestamp(e["timestamp"]))
        clock_ok = not order_errors and all(
            all(a <= b for a, b in zip(v, v[1:], strict=False)) for v in clocks.values()
        )
        result(
            "within_period_source_clock",
            "fully_supported" if clock_ok else "blocked",
            [] if clock_ok else ["missing_or_reversing_native_order_or_clock"],
            physical_timing_certified=False,
        )
    except ValueError as exc:
        result("within_period_source_clock", "blocked", [str(exc)])
    try:
        model = envelopes([e for e in raw if e["period"] < 5], teams)
        native = all(p["conditional_eligible"] for p in model["periods"] if p["period"] < 5)
        if order_errors:
            native = False
        result(
            "cross_period_envelope",
            "conditionally_supported" if native else "blocked",
            ["marker_containment_is_an_uncertified_scenario"],
            model=model,
        )
        overlap = [i for p in model["periods"] for i in p["known_duration_overlap_ids"]]
        unknown_duration = [
            e["id"]
            for e in raw
            if e["period"] < 5
            and e["type"]["name"] not in ("Half Start", "Half End")
            and e.get("duration") is None
        ]
        result(
            "known_completion_boundary_invariance",
            "fully_supported" if native and not overlap else "blocked",
            [] if native and not overlap else ["overlap_or_boundary_unresolved"],
            known_duration_overlap_ids=overlap,
            unknown_duration_event_ids=unknown_duration,
            scope="supplied source durations only, never physical completion certification",
        )
        census = exposure_sensitivity(raw, roster, model) if roster is not None else None
        census_ok = census is not None and not census["issues"]
        result(
            "recorded_census_envelope",
            "conditionally_supported" if native and not overlap and census_ok else "blocked",
            ["uncertified_marker_containment"] if census_ok else ["roster_census_unresolved"],
            census=census,
            known_duration_overlap_ids=overlap,
            official_minutes=None,
            per90_eligible=False,
        )
    except ValueError as exc:
        for name in (
            "cross_period_envelope",
            "recorded_census_envelope",
            "known_completion_boundary_invariance",
        ):
            result(name, "blocked", [str(exc)])
    result(
        "exact_time_exposure",
        "blocked",
        ["no_independent_physical_time_certification"],
        official_minutes=None,
        per90_eligible=False,
    )
    return _report(metadata, rows)


def _report(metadata: dict, rows: dict) -> dict:
    return dict(
        version=VERSION,
        match_id=metadata["match_id"],
        eligibility=rows,
        policy_status="PROPOSED_NOT_ACCEPTED",
        operational_eligibility_changed=False,
        expansion_gate="BLOCKED",
        expansion_authorized=False,
    )
