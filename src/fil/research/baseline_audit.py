"""Read-only diagnosis of frozen real pilot outputs and separate development shrinkage."""

import math
import statistics
from collections import defaultdict

DEVELOPMENT = frozenset({8649, 8650, 8651, 8652})
ALPHAS = (0.25, 0.5, 1.0, 2.0, 4.0)
VERSION = "fil-frozen-baseline-audit-1"


def audit(
    rows: list[dict],
    predictions: list[dict],
    process: list[dict],
    canonical: list[dict],
    results: dict,
) -> dict:
    by_id = {(r["match_id"], r["event_id"]): r for r in canonical}
    by_match = defaultdict(list)
    for r in rows:
        by_match[r["match_id"]].append(r)
    partitions = {mid: name for name, ids in results["partitions"].items() for source, mid in ids}
    prevalence = []
    for mid, values in sorted(by_match.items()):
        shots = {
            i
            for r in values
            if r["outcome"]
            for i in r["outcome_event_ids"]
            if by_id[mid, i]["event_type"] == "Shot"
        }
        prevalence.append(
            dict(
                match_id=mid,
                partition=partitions[mid],
                n=len(values),
                positive=sum(r["outcome"] for r in values),
                prevalence=sum(r["outcome"] for r in values) / len(values),
                distinct_label_shots=len(shots),
                native_horizon_seconds=dict(
                    minimum=min(
                        (
                            by_id[mid, r["outcome_event_ids"][-1]]["period_elapsed_ms"]
                            - by_id[mid, r["event_id"]]["period_elapsed_ms"]
                        )
                        / 1000
                        for r in values
                    ),
                    median=statistics.median(
                        (
                            by_id[mid, r["outcome_event_ids"][-1]]["period_elapsed_ms"]
                            - by_id[mid, r["event_id"]]["period_elapsed_ms"]
                        )
                        / 1000
                        for r in values
                    ),
                    maximum=max(
                        (
                            by_id[mid, r["outcome_event_ids"][-1]]["period_elapsed_ms"]
                            - by_id[mid, r["event_id"]]["period_elapsed_ms"]
                        )
                        / 1000
                        for r in values
                    ),
                ),
            )
        )
    bins = []
    zero_errors = []
    for feature in ("context", "location"):
        groups = defaultdict(lambda: defaultdict(list))
        for r in rows:
            groups[r["features"][feature]][partitions[r["match_id"]]].append(r)
        prior = results["results"][feature]["training_prior"]
        for name, parts in sorted(groups.items(), key=lambda v: str(v[0])):
            train = parts["train"]
            mass = sum(1 / len(by_match[r["match_id"]]) for r in train)
            positives = sum(r["outcome"] / len(by_match[r["match_id"]]) for r in train)
            bins.append(
                dict(
                    feature=feature,
                    bin=name,
                    train_n=len(train),
                    train_positive=sum(r["outcome"] for r in train),
                    train_match_count=len({r["match_id"] for r in train}),
                    training_weight_mass=mass,
                    training_positive_mass=positives,
                    predicted_probability=positives / mass if mass and name is not None else prior,
                    validation_n=len(parts["validation"]),
                    validation_positive=sum(r["outcome"] for r in parts["validation"]),
                    test_n=len(parts["test"]),
                    test_positive=sum(r["outcome"] for r in parts["test"]),
                )
            )
        for p in predictions:
            if p["baseline_feature"] != feature or p["candidate"] != 0 or p["outcome"] != 1:
                continue
            source = by_id[p["match_id"], p["event_id"]]
            zero_errors.append(
                dict(
                    feature=feature,
                    partition=p["partition"],
                    bin=p["context"],
                    match_id=p["match_id"],
                    event_id=p["event_id"],
                    provider_index=p["cutoff_provider_index"],
                    period=p["period"],
                    timestamp=source["period_timestamp"],
                    team_id=p["team_id"],
                    player_id=source["player_id"],
                    source_manifest_sha256=p["source_manifest_sha256"],
                    feature_event_ids=p["feature_event_ids"],
                    future_event_ids=p["outcome_event_ids"],
                    shot_event_ids=[
                        i
                        for i in p["outcome_event_ids"]
                        if by_id[p["match_id"], i]["event_type"] == "Shot"
                    ],
                )
            )
    # Inspect all declared window exclusions without relabelling any original outcome.
    own = defaultdict(list)
    from fil.possessions.extract import OWNER_ACTIONS

    for r in canonical:
        if (
            r["period"] in (1, 2, 3, 4)
            and r["team_id"] == r["possession_team_id"]
            and r["event_type"] in OWNER_ACTIONS
        ):
            own[r["match_id"], r["possession_id"], r["period"]].append(r)
    for group in own.values():
        group.sort(key=lambda r: r["provider_index"])
    strata = defaultdict(list)
    for p in process:
        for w in p["forecast_windows"]:
            r = by_id[w["match_id"], w["cutoff_event_id"]]
            group = own[r["match_id"], r["possession_id"], r["period"]]
            later = [s for s in group if s["provider_index"] > r["provider_index"]][:5]
            strata[w["match_id"], w["eligibility"]].append(
                dict(
                    period=w["period"],
                    event_type=r["event_type"],
                    owner_record_count=len(group),
                    missing_endpoint=r["end_x"] is None or r["end_y"] is None,
                    observed_short_chain_shot=w["eligibility"] == "right_censored_short_chain"
                    and any(s["event_type"] == "Shot" for s in later),
                )
            )
    selection = [
        dict(
            match_id=mid,
            eligibility=reason,
            n=len(v),
            observed_short_chain_shots=sum(r["observed_short_chain_shot"] for r in v),
            median_owner_records=statistics.median(r["owner_record_count"] for r in v),
            missing_endpoints=sum(r["missing_endpoint"] for r in v),
            period_counts={
                p: sum(r["period"] == p for r in v) for p in sorted({r["period"] for r in v})
            },
        )
        for (mid, reason), v in sorted(strata.items())
    ]
    return dict(
        version=VERSION,
        match_prevalence=prevalence,
        bin_support=bins,
        zero_probability_errors=zero_errors,
        censoring_selection=selection,
        original_calibration={
            f: {
                part: r["scores"]["candidate"]["calibration"]
                for part, r in v["comparisons"].items()
            }
            for f, v in results["results"].items()
        },
        original_dependence=results["dependence"],
        uncertainty=(
            "No iid window intervals: overlapping shot labels, four development matches "
            "and one test match; no between-match test interval."
        ),
        original_experiment_changed=False,
    )


def shrinkage_development(rows: list[dict]) -> dict:
    """Parameters frozen by complete-match CV on development only; never score old test."""
    if {r["match_id"] for r in rows} != DEVELOPMENT:
        raise ValueError(
            "Exactly four declared development matches required; "
            "test/development-exposed fixtures forbidden"
        )
    grouped = {mid: [r for r in rows if r["match_id"] == mid] for mid in DEVELOPMENT}
    output = {}
    for feature in ("context", "location"):
        losses = {}
        for alpha in ALPHAS:
            fold = []
            for held in sorted(DEVELOPMENT):
                train = [r for mid, rs in grouped.items() if mid != held for r in rs]
                prior = (
                    sum(
                        sum(r["outcome"] for r in grouped[mid]) / len(grouped[mid])
                        for mid in DEVELOPMENT - {held}
                    )
                    / 3
                )
                bins = defaultdict(lambda: [0.0, 0.0])
                for r in train:
                    key = r["features"][feature]
                    if key is not None:
                        w = 1 / len(grouped[r["match_id"]])
                        bins[key][0] += w * r["outcome"]
                        bins[key][1] += w
                errors = []
                for r in grouped[held]:
                    key = r["features"][feature]
                    s, n = bins.get(key, [0.0, 0.0])
                    p = (s + alpha * prior) / (n + alpha)
                    errors.append((p - r["outcome"]) ** 2)
                fold.append(sum(errors) / len(errors))
            losses[alpha] = sum(fold) / len(fold)
        chosen = min(ALPHAS, key=lambda a: (losses[a], -a))
        if not math.isfinite(losses[chosen]):
            raise ValueError("Nonfinite development loss")
        output[feature] = dict(
            alpha_match_equivalent_mass=chosen,
            development_cv_brier=losses[chosen],
            grid_brier=losses,
        )
    return dict(
        version="fil-shrinkage-development-freeze-1",
        development_match_ids=sorted(DEVELOPMENT),
        families=output,
        test_scored=False,
        confirmation_status="requires_new_independent_matches_not_available_under_blocked_gate",
        scientifically_validated=False,
    )
