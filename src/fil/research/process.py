"""Observed co-occurrence and strict source-order transitions are separate estimands."""

from collections import defaultdict

import pyarrow as pa

VERSION = "fil-process-order-1"
WINDOW_VERSION = "fil-next-five-owner-actions-shot-1"


def analyse(actions: pa.Table) -> dict:
    """Use complete native memberships, never chains truncated by display filters.

    This is native +x geometry, not verified physical attacking direction. A
    reach is an observed start point or a successful move endpoint. Same-event
    geometry is co-occurrence, never a later event. No continuous-time claim.
    """
    groups = defaultdict(list)
    ids = set()
    indices = defaultdict(set)
    all_rows = actions.to_pylist()
    if any(type(r["provider_index"]) is not int for r in all_rows):
        raise ValueError("Missing source order")
    if any(r["coordinate_system"] != "raw_statsbomb_120x80" for r in all_rows):
        raise ValueError("Unsupported provider coordinate semantics")
    for r in all_rows:
        key = (r["match_id"], r["event_id"])
        if key in ids or r["provider_index"] in indices[r["match_id"]]:
            raise ValueError("Duplicate source event identity/order")
        ids.add(key)
        indices[r["match_id"]].add(r["provider_index"])
        if r["possession_id"] is not None:
            groups[r["match_id"], r["possession_id"]].append(r)
    output, windows = [], []
    for (match, pid), members in sorted(groups.items()):
        members.sort(key=lambda r: r["provider_index"])
        own = [r for r in members if r["is_owner_action"]]
        reasons = []
        if len({r["period"] for r in members}) != 1:
            reasons.append("cross_period_native_id")
        if len({r["source_manifest_sha256"] for r in members}) != 1:
            raise ValueError("Mixed source manifests")
        if len({r["possession_team_id"] for r in members}) != 1:
            reasons.append("inconsistent_owner")
        if any(
            r["match_id"] == match
            and members[0]["provider_index"] < r["provider_index"] < members[-1]["provider_index"]
            and r["possession_id"] != pid
            for r in all_rows
        ):
            reasons.append("noncontiguous_or_unassigned_membership")
        if any(r["period"] not in (1, 2, 3, 4) for r in members):
            reasons.append("unsupported_period")
        clocks = [r["period_elapsed_ms"] for r in members]
        if any(t is None for t in clocks) or any(
            a > b
            for a, b in zip(clocks, clocks[1:], strict=False)
            if a is not None and b is not None
        ):
            reasons.append("missing_or_reversing_clock")

        def reaches(r, zones):
            return r["zone"] in zones or (
                r["action_status"] in ("completed", "observed_carry") and r["end_zone"] in zones
            )

        ft = [r for r in own if reaches(r, {"ATT", "BOX"})]
        box = [r for r in own if reaches(r, {"BOX"})]
        shots = [r for r in own if r["event_type"] == "Shot"]
        eligible = bool(ft) and not reasons
        cutoff = ft[0]["provider_index"] if ft else None
        later_shots = [
            r["event_id"] for r in shots if cutoff is not None and r["provider_index"] > cutoff
        ]
        later_box = [
            r["event_id"] for r in box if cutoff is not None and r["provider_index"] > cutoff
        ]
        output.append(
            dict(
                match_id=match,
                possession_id=pid,
                source_manifest_sha256=members[0]["source_manifest_sha256"],
                source_event_ids=[r["event_id"] for r in members],
                observed_final_third_event_ids=[r["event_id"] for r in ft],
                observed_box_event_ids=[r["event_id"] for r in box],
                shot_event_ids=[r["event_id"] for r in shots],
                same_possession_shot_and_final_third=bool(ft and shots),
                same_possession_box_and_final_third=bool(ft and box),
                order_eligible=eligible,
                ordering_unresolved_reasons=reasons,
                eligibility_exclusion_reasons=(
                    reasons
                    + (["no_owner_actions"] if not own else [])
                    + (["no_observed_final_third"] if not ft else [])
                ),
                shot_strictly_after_observed_final_third=bool(later_shots) if eligible else None,
                box_strictly_after_observed_final_third=bool(later_box) if eligible else None,
                later_shot_event_ids=later_shots if eligible else [],
                later_box_event_ids=later_box if eligible else [],
                missing_start_positions=sum(r["zone"] == "UNKNOWN" for r in own),
            )
        )
        # Forecast after a completed pass/carry, excluding the cutoff action.
        # A complete five-action window is mandatory, including for positives;
        # shorter chains are censored, never silently labelled zero.
        for i, r in enumerate(own):
            if r["action_status"] not in ("completed", "observed_carry") or r["event_type"] not in (
                "Pass",
                "Carry",
            ):
                continue
            future = own[i + 1 : i + 6]
            complete = not reasons and len(future) == 5
            windows.append(
                dict(
                    match_id=match,
                    possession_id=pid,
                    cutoff_event_id=r["event_id"],
                    feature_event_ids=[r["event_id"]],
                    cutoff_provider_index=r["provider_index"],
                    cutoff_period_elapsed_ms=r["period_elapsed_ms"],
                    source_manifest_sha256=r["source_manifest_sha256"],
                    availability_assumption=(
                        "complete source record observed; not a live physical clock guarantee"
                    ),
                    period=r["period"],
                    window_version=WINDOW_VERSION,
                    outcome_event_ids=[s["event_id"] for s in future] if complete else [],
                    outcome=int(any(s["event_type"] == "Shot" for s in future))
                    if complete
                    else None,
                    eligibility="complete"
                    if complete
                    else "ordering_unresolved"
                    if reasons
                    else "right_censored_short_chain",
                )
            )
    eligible = [r for r in output if r["order_eligible"]]
    return dict(
        version=VERSION,
        unassigned_original_event_ids=[
            r["event_id"] for r in all_rows if r["possession_id"] is None
        ],
        window_version=WINDOW_VERSION,
        possessions=output,
        forecast_windows=windows,
        summary=dict(
            native_possessions=len(output),
            cooccurrence_shot_final_third=sum(
                r["same_possession_shot_and_final_third"] for r in output
            ),
            order_eligible_possessions=len(eligible),
            ordering_unresolved_possessions=sum(
                bool(r["ordering_unresolved_reasons"]) for r in output
            ),
            no_observed_final_third_possessions=sum(
                not r["observed_final_third_event_ids"] for r in output
            ),
            shot_after_observed_final_third=sum(
                r["shot_strictly_after_observed_final_third"] for r in eligible
            ),
            box_after_observed_final_third=sum(
                r["box_strictly_after_observed_final_third"] for r in eligible
            ),
            complete_forecast_windows=sum(r["eligibility"] == "complete" for r in windows),
            censored_or_unresolved_forecast_windows=sum(r["outcome"] is None for r in windows),
        ),
        uncertainty=(
            "Observed native +x states only; missing positions may hide reaches. "
            "Strict provider order is not elapsed time, off-ball movement, intent or causation."
        ),
    )
