"""Match-held-out baseline evaluation; predictive scores never certify player value."""

import math
import random
import statistics
from collections import defaultdict
from datetime import date
from statistics import NormalDist

VERSION = "fil-research-evaluation-1"


def key(row: dict) -> tuple:
    return row["source"], row["match_id"]


def chronological_split(matches: list[dict], train_end: str, validation_end: str) -> dict:
    """Date boundaries are declared externally; all actions of a match stay together."""
    a, b = date.fromisoformat(train_end), date.fromisoformat(validation_end)
    if a >= b:
        raise ValueError("Training boundary must precede validation boundary")
    if len({r["source"] for r in matches}) > 1:
        raise ValueError("Provider-specific evaluation required; no silent pooling")
    output = {"train": set(), "validation": set(), "test": set()}
    seen = set()
    for row in matches:
        k = key(row)
        if k in seen:
            raise ValueError("Duplicate match; date/identity conflict or pseudoreplication")
        seen.add(k)
        day = date.fromisoformat(row["match_date"])
        label = "train" if day <= a else "validation" if day <= b else "test"
        if k == ("statsbomb_open_data", 8658) and label != "train":
            raise ValueError("Match 8658 is development-exposed; never a validation/test holdout")
        output[label].add(k)
    if any(not s for s in output.values()):
        raise ValueError("Insufficient distinct dated matches for train/validation/test")
    return output


def check_feature_lineage(
    records: list[dict], feature_ids: list[str], cutoff: int, outcome_id: str
) -> None:
    """Reject future-event features and cross-period/foreign-match labels."""
    by_id = {r["event_id"]: r for r in records}
    if len(by_id) != len(records) or not feature_ids or len(feature_ids) != len(set(feature_ids)):
        raise ValueError("Invalid feature evidence IDs")
    try:
        features = [by_id[i] for i in feature_ids]
        outcome = by_id[outcome_id]
    except KeyError as e:
        raise ValueError("Foreign evidence ID") from e
    if (
        any(
            key(r) != key(outcome)
            or r["period"] != outcome["period"]
            or r["provider_index"] > cutoff
            for r in features
        )
        or outcome["provider_index"] <= cutoff
    ):
        raise ValueError("Future information or foreign match/period in features")


def _binary(value):
    if value not in (0, 1):
        raise ValueError("Outcome must be known binary; no missing-as-zero")
    return int(value)


def fit_baselines(train: list[dict]) -> dict:
    """Training-only equal-match prior and weighted context-frequency baseline.

    Two training matches is a technical guard, not an adequate scientific sample.
    Context must be pre-action, declared beforehand and independently leak-audited.
    """
    matches = {key(r) for r in train}
    if len(matches) < 2:
        raise ValueError("At least two training matches required; adequacy remains unestablished")
    labels = [_binary(r["outcome"]) for r in train]
    match_counts = defaultdict(int)
    for r in train:
        match_counts[key(r)] += 1
    groups = defaultdict(list)
    weighted = []
    for r, y in zip(train, labels, strict=True):
        w = 1 / match_counts[key(r)]
        weighted.append((y, w))
        if r.get("context") is not None:
            groups[r["context"]].append((y, w))

    def frequency(values):
        return math.fsum(y * w for y, w in values) / math.fsum(w for _, w in values)

    return dict(
        training_matches=matches,
        prior=frequency(weighted),
        context={k: dict(probability=frequency(v), n=len(v)) for k, v in groups.items()},
        weighting="inverse within-match record count, aligned with equal-match evaluation",
        status="exploratory_baselines_not_validated",
    )


def baseline_predictions(model: dict, test: list[dict]) -> list[dict]:
    if any(key(r) in model["training_matches"] for r in test):
        raise ValueError("Training/test match leakage")
    return [
        {
            **r,
            "baseline": model["prior"],
            "candidate": model["context"]
            .get(r.get("context"), {})
            .get("probability", model["prior"]),
            "context_supported": r.get("context") in model["context"],
        }
        for r in test
    ]


def calibration(rows: list[dict], name: str, bins: int = 5) -> list[dict]:
    if bins < 2:
        raise ValueError("Need at least two fixed calibration bins")
    result = []
    for i in range(bins):
        values = [r for r in rows if min(int(r[name] * bins), bins - 1) == i]
        result.append(
            dict(
                lower=i / bins,
                upper=(i + 1) / bins,
                n=len(values),
                mean_probability=statistics.mean(r[name] for r in values) if values else None,
                observed_frequency=statistics.mean(r["outcome"] for r in values)
                if values
                else None,
            )
        )
    return result


def cluster_interval(values: list[float], seed: int = 0, repetitions: int = 2000) -> list | None:
    """Percentile bootstrap over independent cluster summaries, never individual actions."""
    if repetitions < 100 or any(not math.isfinite(v) for v in values):
        raise ValueError("Invalid bootstrap configuration/data")
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    samples = sorted(
        statistics.mean(rng.choices(values, k=len(values))) for _ in range(repetitions)
    )
    return [
        samples[int(0.025 * repetitions)],
        samples[min(repetitions - 1, int(0.975 * repetitions))],
    ]


def evaluate(rows: list[dict], seed: int = 0) -> dict:
    """Paired equal-match Brier differences, calibration, log loss and coverage.

    Match resampling does not solve repeat-team/player dependence or confer decision
    usefulness. All evaluations remain exploratory pending independent validation.
    """
    if not rows:
        raise ValueError("Empty evaluation")
    ids = [(*key(r), r["event_id"]) for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate evaluation unit")
    for r in rows:
        _binary(r["outcome"])
        for name in ("baseline", "candidate"):
            p = r[name]
            if not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
                raise ValueError("Missing/invalid probability; never impute zero")
    grouped = defaultdict(list)
    for r in rows:
        grouped[key(r)].append(r)
    scores = {}
    briers = {}
    for name in ("baseline", "candidate"):
        losses = {
            k: statistics.mean((r[name] - r["outcome"]) ** 2 for r in v) for k, v in grouped.items()
        }
        briers[name] = losses
        log_losses = []
        impossible = 0
        for values in grouped.values():
            terms = []
            for r in values:
                p = r[name] if r["outcome"] else 1 - r[name]
                if p == 0:
                    impossible += 1
                else:
                    terms.append(-math.log(p))
            log_losses.append(statistics.mean(terms) if len(terms) == len(values) else None)
        scores[name] = dict(
            equal_match_brier=statistics.mean(losses.values()),
            equal_match_log_loss=statistics.mean(log_losses) if not impossible else None,
            infinite_log_loss_predictions=impossible,
            calibration=calibration(rows, name),
            calibration_weighting="event-weighted; Brier/logloss above equal-match weighted",
        )
    delta = [briers["baseline"][k] - briers["candidate"][k] for k in sorted(grouped)]
    return dict(
        version=VERSION,
        status="exploratory",
        scientifically_validated=False,
        match_count=len(grouped),
        event_count=len(rows),
        scores=scores,
        equal_match_brier_improvement=statistics.mean(delta),
        match_bootstrap_95_interval=cluster_interval(delta, seed),
        decision_value_status=(
            "insufficient_evidence; independent prospective analyst review required"
        ),
        uncertainty_limits=(
            "Match clusters only; recurrent team/player dependence, selection "
            "and rare strata require separate audit"
        ),
        null_contexts=sum(r.get("context") is None for r in rows),
    )


def negative_control(rows: list[dict], seed: int = 0) -> list[dict]:
    """Experimental within-match/team/period label shuffle; never replace source truth."""
    rng = random.Random(seed)
    grouped = defaultdict(list)
    for i, r in enumerate(rows):
        grouped[(*key(r), r["team_id"], r["period"])].append(i)
    output = [dict(r) for r in rows]
    for indices in grouped.values():
        ys = [_binary(rows[i]["outcome"]) for i in indices]
        rng.shuffle(ys)
        for i, y in zip(indices, ys, strict=True):
            output[i]["outcome"] = y
            output[i]["experimental_label_permutation"] = True
    return output


def required_clusters(
    pilot_effects: list[float], meaningful_effect: float, alpha: float = 0.05, power: float = 0.8
) -> dict:
    """Normal-approximation paired-mean planning; effect/cluster unit declared by analyst.

    No arbitrary match/minute floor. Independent pilot clusters are required;
    repeated-team dependence and learning curves can invalidate this approximation.
    """
    if (
        not 0 < alpha < 1
        or not 0.5 < power < 1
        or not math.isfinite(meaningful_effect)
        or meaningful_effect <= 0
    ):
        raise ValueError("Invalid predeclared effect/power/alpha")
    if any(not math.isfinite(v) for v in pilot_effects):
        raise ValueError("Invalid pilot effects")
    sd = statistics.stdev(pilot_effects) if len(pilot_effects) >= 2 else None
    n = None
    if sd is not None and sd > 0:
        z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
        n = math.ceil((z * sd / meaningful_effect) ** 2)
    return dict(
        method="paired independent cluster mean, normal approximation",
        pilot_clusters=len(pilot_effects),
        pilot_sd=sd,
        meaningful_effect=meaningful_effect,
        alpha=alpha,
        power=power,
        required_clusters=n,
        status="planning_approximation" if n else "insufficient_independent_pilot_variance",
        limitations=(
            "Not model-training adequacy; validate dependence, rare outcomes and "
            "learning curves separately"
        ),
    )


def dependence_audit(partitions: dict, match_metadata: list[dict]) -> dict:
    """Expose repeat-team/player dependence instead of claiming disjoint matches solve it.

    Missing identity coverage remains unknown, never an empty overlap. Metadata
    identities must use provider IDs in the source namespace; no name matching.
    """
    by_key = {key(r): r for r in match_metadata}
    if len(by_key) != len(match_metadata):
        raise ValueError("Duplicate metadata match")
    labels = list(partitions)
    assigned = set()
    for keys in partitions.values():
        if assigned & keys:
            raise ValueError("Match partition overlap")
        assigned.update(keys)
    if assigned - set(by_key):
        raise ValueError("Missing partition match metadata")
    result = {}
    for i, a in enumerate(labels):
        for b in labels[i + 1 :]:
            row = {}
            for field in ("team_ids", "player_ids"):
                if any(by_key[k].get(field) is None for k in partitions[a] | partitions[b]):
                    row["shared_" + field] = None
                else:
                    left = {(k[0], p) for k in partitions[a] for p in by_key[k][field]}
                    right = {(k[0], p) for k in partitions[b] for p in by_key[k][field]}
                    row["shared_" + field] = sorted(left & right)
            result[a + "__" + b] = row
    return dict(
        overlap=result,
        independence_certified=False,
        limits=(
            "Match splits prevent action leakage; shared teams/players require "
            "context adjustment and dependence sensitivity"
        ),
    )
