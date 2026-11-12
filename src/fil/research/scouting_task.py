"""Scouting decision task v0: appearance reliability, ceiling and frozen gates.

Implements only the measurement stages of
`docs/research/SCOUTING_DECISION_PROTOCOL.md`. It never ranks players, never
labels ability and never scores a criterion. The caller supplies appearance
records produced from canonical source events; missing source values raise
instead of being replaced by zero.
"""

import math
import random
import statistics
from dataclasses import dataclass
from typing import Any

VERSION = "fil-scouting-decision-task-1"
METRICS = ("shots", "goals", "xg", "npxg")
REQUIRED = ("source", "match_id", "team_id", "player_id", "stage", "team_matchday",
            "position_label", "shots", "goals", "xg", "npxg")


@dataclass(frozen=True)
class Thresholds:
    """Frozen protocol values; ratifying a change is a protocol revision."""

    reliability_point: float = 0.50
    reliability_lower: float = 0.30
    reliability_margin: float = 0.10
    ceiling: float = 0.45
    minimum_worthwhile_difference: float = 0.10

    def __post_init__(self) -> None:
        values = (
            self.reliability_point,
            self.reliability_lower,
            self.reliability_margin,
            self.ceiling,
            self.minimum_worthwhile_difference,
        )
        if any(not math.isfinite(v) or not -1 <= v <= 1 for v in values):
            raise ValueError("Thresholds must be finite correlations in [-1, 1]")
        if self.reliability_lower > self.reliability_point:
            raise ValueError("Lower bound cannot exceed the point threshold")
        if not 0 < self.ceiling <= 1:
            raise ValueError("Ceiling threshold must be in (0, 1]")


DEFAULT_THRESHOLDS = Thresholds()


def window_of(row: dict[str, Any]) -> str:
    """Team matchdays 1-2 observe, matchday 3 is the primary criterion."""
    stage, matchday = row["stage"], row["team_matchday"]
    if stage == "group":
        if matchday in (1, 2):
            return "observation"
        if matchday == 3:
            return "criterion"
        raise ValueError("Group team matchday must be 1, 2 or 3")
    if stage == "knockout":
        if matchday is not None:
            raise ValueError("Knockout records carry no group team matchday")
        return "criterion_knockout"
    raise ValueError(f"Unsupported stage: {stage!r}")


def _number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite; missing source values are not zero")
    return float(value)


def _validate(row: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED if k not in row]
    if missing:
        raise ValueError(f"Appearance is missing fields: {missing}")
    for name in ("shots", "goals"):
        value = row[name]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    for name in ("xg", "npxg"):
        value = _number(row[name], name)
        if value < 0 or value > row["shots"] + 1e-9:
            raise ValueError(f"{name} must lie in [0, shots]")
    if row["npxg"] > row["xg"] + 1e-9:
        raise ValueError("Non-penalty xG cannot exceed total xG")
    if row["goals"] > row["shots"]:
        raise ValueError("Goals cannot exceed recorded shots")
    window_of(row)


def validate_appearances(rows: list[dict[str, Any]]) -> None:
    """Reject duplicates, missing source values and impossible records."""
    seen: set[tuple] = set()
    for row in rows:
        _validate(row)
        key = (row["source"], row["match_id"], row["team_id"], row["player_id"])
        if key in seen:
            raise ValueError("Duplicate player appearance identity")
        seen.add(key)


def candidate_universe(
    rows: list[dict[str, Any]], minimum_appearances: int = 1
) -> dict[str, Any]:
    """Observation-window players with a provider position label.

    A single appearance is the primary inclusion rule; the two-appearance
    variant is a declared sensitivity, not a retuning knob. Exclusion counts are
    within the observation window: a player seen only on matchday 3 is out of
    scope rather than insufficiently observed.
    """
    if minimum_appearances < 1:
        raise ValueError("Minimum appearances must be at least one")
    validate_appearances(rows)
    counts: dict[tuple, int] = {}
    labelled: dict[tuple, str | None] = {}
    for row in rows:
        if window_of(row) != "observation":
            continue
        key = (row["player_id"], row["team_id"])
        counts[key] = counts.get(key, 0) + 1
        # The first labelled appearance supplies the label; a null early record
        # must not hide later provider metadata.
        if labelled.get(key) is None and row["position_label"] is not None:
            labelled[key] = row["position_label"]
    included = sorted(k for k, n in counts.items() if n >= minimum_appearances
                      and labelled.get(k) is not None)
    return {
        "players": [{"player_id": p, "team_id": t} for p, t in included],
        "included": len(included),
        "observed": len(counts),
        "excluded_unlabelled": sum(
            1 for k, n in counts.items() if n >= minimum_appearances
            and labelled.get(k) is None
        ),
        "excluded_insufficient_appearances": sum(1 for n in counts.values()
                                                 if n < minimum_appearances),
        "minimum_appearances": minimum_appearances,
    }


def pearson(pairs: list[tuple[float, float]]) -> float | None:
    """Correlation of two measurements; undefined for <3 pairs or zero variance."""
    if len(pairs) < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = math.fsum((x - mx) ** 2 for x in xs)
    syy = math.fsum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    sxy = math.fsum((x - mx) * (y - my) for x, y in pairs)
    return sxy / math.sqrt(sxx * syy)


def spearman_brown(r: float, k: int = 2) -> float:
    """Reliability of the mean of k parallel measurements."""
    if not -1 <= r <= 1:
        raise ValueError("Reliability must lie in [-1, 1]")
    if k < 1:
        raise ValueError("Number of measurements must be positive")
    denominator = 1 + (k - 1) * r
    if denominator <= 0:
        raise ValueError("Spearman-Brown undefined for this reliability")
    return k * r / denominator


def measurement_ceiling(r_obs: float, r_crit: float) -> float:
    """Upper bound for a correlation attenuated by both measurement errors."""
    for name, value in (("r_obs", r_obs), ("r_crit", r_crit)):
        if not -1 <= value <= 1:
            raise ValueError(f"{name} must lie in [-1, 1]")
    return math.sqrt(max(0.0, r_obs) * max(0.0, r_crit))


def reliability_pairs(
    rows: list[dict[str, Any]], metric: str, minimum_appearances: int = 1
) -> dict[str, Any]:
    """First versus second observation appearance, for two-appearance players.

    The subgroup is regular starters, so the estimate is optimistic for the
    full universe; the caller must report that direction with the result.
    """
    if metric not in METRICS:
        raise ValueError(f"Unsupported metric: {metric!r}")
    universe = {
        (p["player_id"], p["team_id"])
        for p in candidate_universe(rows, minimum_appearances)["players"]
    }
    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (row["player_id"], row["team_id"])
        if key not in universe or window_of(row) != "observation":
            continue
        grouped.setdefault(key, []).append(row)
    pairs: list[tuple[float, float]] = []
    single = 0
    for appearances in grouped.values():
        ordered = sorted(appearances, key=lambda r: r["team_matchday"])
        if len(ordered) < 2:
            single += 1
            continue
        if len(ordered) > 2:
            raise ValueError("Observation window supplies at most two appearances")
        pairs.append((float(ordered[0][metric]), float(ordered[1][metric])))
    return {
        "pairs": pairs,
        "n_pairs": len(pairs),
        "single_appearance_players": single,
        "r_single": pearson(pairs),
        "metric": metric,
    }


def bootstrap_pairs(
    pairs: list[tuple[float, float]],
    seed: int = 1729,
    repetitions: int = 10000,
) -> list[float] | None:
    """Percentile interval resampling players, never appearances."""
    if repetitions < 100:
        raise ValueError("Bootstrap repetitions are too few to be meaningful")
    if len(pairs) < 3:
        return None
    rng = random.Random(seed)
    draws: list[float] = []
    attempts = 0
    while len(draws) < repetitions and attempts < repetitions * 20:
        attempts += 1
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        value = pearson(sample)
        if value is not None:
            draws.append(value)
    if len(draws) < repetitions // 2:
        return None
    draws.sort()
    return [
        draws[int(0.025 * len(draws))],
        draws[min(len(draws) - 1, int(0.975 * len(draws)))],
    ]


def reliability_gate(
    r_single: float | None,
    interval: list[float] | None,
    thresholds: Thresholds,
    comparative: float | None = None,
) -> dict[str, Any]:
    """Observation-window gate; never passes on a point estimate alone."""
    if r_single is None or interval is None:
        return {"passed": False, "reason": "insufficient_or_degenerate_pairs"}
    try:
        r_obs = spearman_brown(r_single)
    except ValueError:
        return {"passed": False, "reason": "unstable_point_estimate"}
    lower = spearman_brown(interval[0]) if interval[0] > -1 else None
    passed = (
        r_obs >= thresholds.reliability_point
        and lower is not None
        and lower >= thresholds.reliability_lower
    )
    reason = "passed" if passed else "below_declared_threshold"
    if passed and comparative is not None and comparative < -thresholds.reliability_margin:
        passed, reason = False, "xG_reliability_below_goals_margin"
    return {
        "passed": passed,
        "reason": reason,
        "r_single": r_single,
        "r_obs": r_obs,
        "r_single_lower": interval[0],
        "r_obs_lower": lower,
    }


def criterion_values(
    rows: list[dict[str, Any]], metric: str, window: str = "criterion"
) -> dict[tuple, float]:
    """Per-appearance criterion for players with a criterion appearance."""
    if metric not in METRICS:
        raise ValueError(f"Unsupported metric: {metric!r}")
    if window not in ("criterion", "criterion_knockout"):
        raise ValueError("Criterion window must be group matchday 3 or knockout")
    totals: dict[tuple, float] = {}
    counts: dict[tuple, int] = {}
    for row in rows:
        if window_of(row) != window:
            continue
        key = (row["player_id"], row["team_id"])
        totals[key] = totals.get(key, 0.0) + float(row[metric])
        counts[key] = counts.get(key, 0) + 1
    return {k: totals[k] / counts[k] for k in totals}


def ceiling_gate(r_obs: float, r_crit: float, thresholds: Thresholds) -> dict[str, Any]:
    """Pre-declared stop: attenuation, not absence, when the ceiling is too low."""
    value = measurement_ceiling(r_obs, r_crit)
    passed = value >= thresholds.ceiling
    return {
        "passed": passed,
        "reason": "passed" if passed else "uninformative_by_ceiling",
        "ceiling": value,
        "r_obs": r_obs,
        "r_crit": r_crit,
        "threshold": thresholds.ceiling,
    }


def classify_increment(
    interval: list[float] | None,
    ceiling: float,
    thresholds: Thresholds,
) -> dict[str, Any]:
    """Exhaustive, non-interchangeable labels for an increment interval."""
    if interval is None:
        label = "inconclusive"
        reason = "no_interval"
    elif ceiling < thresholds.ceiling:
        label = "uninformative"
        reason = "attenuation_dominates"
    elif interval[0] > 0:
        label, reason = "increment", "lower_bound_above_zero"
    elif interval[1] < 0:
        label, reason = "adverse", "upper_bound_below_zero"
    else:
        half_width = (interval[1] - interval[0]) / 2
        if half_width <= thresholds.minimum_worthwhile_difference:
            label, reason = "no_detectable_increment", "half_width_within_mwd"
        else:
            label, reason = "inconclusive", "half_width_exceeds_mwd"
    half_width = None if interval is None else (interval[1] - interval[0]) / 2
    return {"label": label, "reason": reason, "half_width": half_width,
            "minimum_worthwhile_difference": thresholds.minimum_worthwhile_difference}


def shrink(total: float, weight: float, prior_mean: float, prior_weight: float) -> float:
    """Pre-declared deterministic ranking input; never tuned on the criterion."""
    if weight < 0 or prior_weight <= 0:
        raise ValueError("Weights must be non-negative with a positive prior")
    if not 0 <= prior_mean <= 1:
        raise ValueError("Prior mean must be a probability")
    return (total + prior_weight * prior_mean) / (weight + prior_weight)


def reliability_stage(
    rows: list[dict[str, Any]],
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
    seed: int = 1729,
    repetitions: int = 10000,
) -> dict[str, Any]:
    """Run the observation gate and, if it passes, the ceiling gate.

    Returns a decision only. No criterion is scored and no player is ranked.
    """
    estimates = {metric: reliability_pairs(rows, metric) for metric in METRICS}
    metrics = {
        metric: {
            "r_single": estimate["r_single"],
            "interval": bootstrap_pairs(estimate["pairs"], seed, repetitions),
        }
        for metric, estimate in estimates.items()
    }
    xg = estimates["xg"]
    comparative = None
    if estimates["goals"]["r_single"] is not None and xg["r_single"] is not None:
        comparative = xg["r_single"] - estimates["goals"]["r_single"]
    gate = reliability_gate(xg["r_single"], metrics["xg"]["interval"], thresholds, comparative)
    report: dict[str, Any] = {
        "version": VERSION,
        "thresholds": thresholds,
        "metric": "xg",
        "n_pairs": xg["n_pairs"],
        "single_appearance_players": xg["single_appearance_players"],
        "metrics": metrics,
        "comparative_margin": comparative,
        "reliability_gate": gate,
        "stage": "stop_reliability" if not gate["passed"] else "ceiling_gate",
        "ceiling_gate": None,
        "notes": [
            "Regular-starter subgroup; reliability is optimistic for the universe.",
            "One appearance estimates r_crit by assumption, not by measurement.",
            "No ranking, ability label or criterion score is produced here.",
        ],
    }
    if gate["passed"]:
        ceiling = ceiling_gate(gate["r_obs"], gate["r_single"], thresholds)
        report["ceiling_gate"] = ceiling
        report["stage"] = "stop_ceiling" if not ceiling["passed"] else "proceed"
    return report
