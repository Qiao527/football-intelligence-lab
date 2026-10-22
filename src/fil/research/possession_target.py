"""Proposed retrospective recorded-Shot target; original five-action labels unchanged."""

import re
from collections import defaultdict

VERSION = "fil-recorded-shot-before-segment-close-1"


def label_segments(raw: list[dict], source_manifest_sha256: str, match_id: int) -> list[dict]:
    """Separate observed positives, closed negatives and unresolved/censored cutoffs.

    No geometry, exposure, physical clock or future annotation-count prerequisite.
    A source scope/hash verifier must run before this pure local transformation.
    """
    if (
        type(match_id) is not int
        or match_id <= 0
        or not re.fullmatch("[0-9a-f]{64}", source_manifest_sha256)
    ):
        raise ValueError("Original match identity and verified source manifest hash required")
    ids = [e["id"] for e in raw]
    if len(set(ids)) != len(ids) or not raw:
        raise ValueError("Nonempty unique source events required")
    if any(
        a["index"] >= b["index"] or a["period"] > b["period"]
        for a, b in zip(raw, raw[1:], strict=False)
    ):
        raise ValueError("Unique increasing provider order required")
    groups = defaultdict(list)
    for i, e in enumerate(raw):
        if e.get("possession") is not None:
            groups[e["possession"]].append(i)
    output = []
    for pid, indices in groups.items():
        members = [raw[i] for i in indices]
        periods = {e["period"] for e in members}
        owners = {e.get("possession_team", {}).get("id") for e in members}
        reasons = []
        if len(periods) != 1 or not periods <= {1, 2, 3, 4}:
            reasons.append("unsupported_or_cross_period_membership")
        if len(owners) != 1 or None in owners:
            reasons.append("ambiguous_possession_owner")
        if indices != list(range(indices[0], indices[-1] + 1)):
            reasons.append("noncontiguous_or_unassigned_membership")
        owner = members[0].get("possession_team", {}).get("id")
        own = [e for e in members if e["team"]["id"] == owner]
        period = members[0]["period"]
        # The end markers may belong to this or a different native membership.
        ends = [e for e in raw if e["period"] == period and e["type"]["name"] == "Half End"]
        paired = (
            len(ends) == 2
            and len({e["team"]["id"] for e in ends}) == 2
            and ends[1]["id"] in ends[0].get("related_events", [])
            and ends[0]["id"] in ends[1].get("related_events", [])
        )
        incomplete = any(
            (e.get("half_end") or {}).get(k)
            for e in ends
            for k in ("early_video_end", "match_suspended")
        )
        after = raw[indices[-1] + 1] if indices[-1] + 1 < len(raw) else None
        nonmarkers = [
            e for e in members if e["type"]["name"] not in ("Half Start", "Half End", "Starting XI")
        ]
        last_action = nonmarkers[-1]["index"] if nonmarkers else None
        end_path_clear = (
            paired
            and last_action is not None
            and not any(
                e.get("possession") != pid and e["type"]["name"] != "Half End"
                for e in raw
                if last_action < e["index"] <= ends[-1]["index"]
            )
        )
        closure_ids, closure_kind = [], None
        if not reasons and not incomplete:
            if after and after["period"] == period and after.get("possession") is not None:
                closure_ids, closure_kind = [after["id"]], "next_native_membership"
            elif end_path_clear and all(e["index"] > last_action for e in ends):
                closure_ids, closure_kind = [e["id"] for e in ends], "paired_half_end"
        for cutoff in own:
            kind = cutoff["type"]["name"]
            if kind != "Carry" and not (kind == "Pass" and "outcome" not in cutoff.get("pass", {})):
                continue
            shots = [e for e in own if e["type"]["name"] == "Shot" and e["index"] > cutoff["index"]]
            known = [
                e["shot"]["statsbomb_xg"]
                for e in shots
                if e["shot"].get("statsbomb_xg") is not None
            ]
            missing = [e["id"] for e in shots if e["shot"].get("statsbomb_xg") is None]
            # Order/owner ambiguity prevents attribution even if a Shot is present.
            y = None if reasons else 1 if shots else 0 if closure_ids else None
            output.append(
                dict(
                    version=VERSION,
                    source="statsbomb_open_data",
                    match_id=match_id,
                    possession_id=pid,
                    period=period,
                    source_manifest_sha256=source_manifest_sha256,
                    cutoff_event_id=cutoff["id"],
                    cutoff_provider_index=cutoff["index"],
                    feature_event_ids=[cutoff["id"]],
                    owner_team_id=owner,
                    outcome=y,
                    observation_state="confirmed_recorded_positive"
                    if y == 1
                    else "confirmed_recorded_negative"
                    if y == 0
                    else "unresolved_or_censored",
                    unresolved_reasons=reasons
                    if reasons
                    else [
                        "incomplete_source_boundary"
                        if incomplete
                        else "no_verified_segment_closure"
                    ]
                    if y is None
                    else [],
                    later_shot_event_ids=[e["id"] for e in shots],
                    observed_known_source_xg_sum=sum(known),
                    complete_later_shot_xg_sum=sum(known)
                    if not missing and closure_ids and not reasons
                    else None,
                    missing_shot_xg_event_ids=missing,
                    closure_evidence_ids=closure_ids,
                    closure_kind=closure_kind,
                    complete_terminal_chance_evidence=bool(closure_ids) and not reasons,
                    physical_timing_certified=False,
                )
            )
    return output


def possession_weights(rows: list[dict]) -> list[dict]:
    """Equal match → possession → labelled cutoff. Unresolved weights remain null."""
    groups = defaultdict(lambda: defaultdict(list))
    seen = set()
    for n, r in enumerate(rows):
        key = (r["source"], r["match_id"], r["cutoff_event_id"])
        if r["source"] != "statsbomb_open_data" or key in seen:
            raise ValueError("Duplicate source identity or unsupported mixed provider")
        seen.add(key)
        if r["outcome"] not in (None, 0, 1):
            raise ValueError("Unknown label state")
        if r["match_id"] is None:
            raise ValueError("Source-namespaced match identity required")
        if r["outcome"] is not None:
            groups[r["match_id"]][r["possession_id"]].append(n)
    weights = {}
    for possessions in groups.values():
        for indices in possessions.values():
            weights.update({n: 1 / (len(possessions) * len(indices)) for n in indices})
    return [dict(r, within_match_possession_weight=weights.get(n)) for n, r in enumerate(rows)]


def label_support(rows: list[dict]) -> dict:
    """Descriptive support and missing-label bounds, never independent trials or CI."""
    shot_reuse = defaultdict(int)
    by_possession = defaultdict(list)
    for r in rows:
        by_possession[r["source"], r["match_id"], r["possession_id"]].append(r)
        if r["outcome"] == 1:
            for i in r["later_shot_event_ids"]:
                shot_reuse[r["source"], r["match_id"], i] += 1
    n = len(rows)
    positive = sum(r["outcome"] == 1 for r in rows)
    unresolved = sum(r["outcome"] is None for r in rows)
    return dict(
        all_cutoffs=n,
        confirmed_positives=positive,
        confirmed_negatives=sum(r["outcome"] == 0 for r in rows),
        unresolved=unresolved,
        unweighted_all_cutoff_prevalence_bounds=[positive / n, (positive + unresolved) / n]
        if n
        else None,
        bounds_interpretation="missing-label extremes, not confidence or physical-coverage bounds",
        distinct_linked_shots=len(shot_reuse),
        max_positive_cutoffs_sharing_one_shot=max(shot_reuse.values(), default=0),
        source_possessions=len(by_possession),
        positive_possessions=sum(any(r["outcome"] == 1 for r in v) for v in by_possession.values()),
        max_cutoffs_per_possession=max(map(len, by_possession.values()), default=0),
        independent_observations_certified=False,
    )
