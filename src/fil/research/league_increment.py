"""Increment test: does source xG order players better than goals alone?

Implements the amended increment stage of
`docs/research/LEAGUE_SCOUTING_PROTOCOL.md`. Rankings are built from window A only
and scored against window B xG per appearance. No player label, shortlist or ability
claim is produced; the output is a paired rank-correlation difference.
"""

import math
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from fil.research.scouting_task import classify_increment

VERSION = "fil-league-increment-1"
PRIOR_APPEARANCES = 10.0
TOP_K = 25


@dataclass(frozen=True)
class IncrementSettings:
    prior_appearances: float = PRIOR_APPEARANCES
    top_k: int = TOP_K
    ceiling: float = 0.45
    minimum_worthwhile_difference: float = 0.10


DEFAULT_SETTINGS = IncrementSettings()


def _aggregate(rows: list[dict[str, Any]], players: list[tuple]) -> dict[tuple, dict]:
    keep = set(players)
    out: dict[tuple, dict] = {}
    for row in rows:
        key = (row["player_id"], row["team_id"])
        if key not in keep:
            continue
        record = out.setdefault(key, {
            "appearances": {"A": 0, "B": 0},
            "goals": 0.0, "xg": 0.0, "op_npxg": 0.0, "xg_b": 0.0,
            "positions": defaultdict(int),
        })
        window = row["window"]
        record["appearances"][window] += 1
        record["positions"][row["position_names"][0] if row["position_names"] else "unknown"] += 1
        if window == "A":
            record["goals"] += row["goals"]
            record["xg"] += row["xg"]
            record["op_npxg"] += row["op_npxg"]
        else:
            record["xg_b"] += row["xg"]
    return out


def _modal(counter: dict[str, int]) -> str:
    return max(sorted(counter), key=lambda name: counter[name])


def _group_rates(
    aggregated: dict[tuple, dict], prior: float
) -> dict[tuple, float]:
    """Leave-one-out positional-group per-appearance rate, pooled in raw totals."""
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    membership: dict[tuple, str] = {}
    for key, record in aggregated.items():
        n = record["appearances"]["A"]
        if n == 0:
            continue
        membership[key] = _modal(record["positions"])
        for field in ("goals", "xg", "op_npxg"):
            groups[(membership[key], field)].append((record[field], n))
    rates: dict[tuple, float] = {}
    for key, record in aggregated.items():
        group = membership.get(key)
        if group is None:
            continue
        n = record["appearances"]["A"]
        for field in ("goals", "xg", "op_npxg"):
            total, count = 0.0, 0.0
            for value, appearances in groups[(group, field)]:
                total += value
                count += appearances
            own_total, own_n = record[field], n
            if count - own_n > 0:
                rate = (total - own_total) / (count - own_n)
            else:
                rate = total / count if count else 0.0
            rates[(key, field)] = (own_total + prior * rate) / (own_n + prior)
    return rates


def score_players(
    aggregated: dict[tuple, dict], settings: IncrementSettings = DEFAULT_SETTINGS
) -> dict[tuple, dict]:
    """Arm scores from window A, shrunk toward the positional-group mean."""
    rates = _group_rates(aggregated, settings.prior_appearances)
    scored = {}
    for key, record in aggregated.items():
        if record["appearances"]["A"] < 1 or record["appearances"]["B"] < 1:
            continue
        scored[key] = {
            "c0": rates[(key, "goals")],
            "c1": rates[(key, "xg")],
            "c2": rates[(key, "op_npxg")],
            "criterion": record["xg_b"] / record["appearances"]["B"],
            "group": _modal(record["positions"]),
        }
    return scored


def average_ranks(values: list[float]) -> list[float]:
    """Ascending average ranks; ties share the mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean = (i + j) / 2 + 1
        for index in order[i:j + 1]:
            ranks[index] = mean
        i = j + 1
    return ranks


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3 or len(a) != len(b):
        return None
    ra, rb = average_ranks(a), average_ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    sxx = math.fsum((x - ma) ** 2 for x in ra)
    syy = math.fsum((y - mb) ** 2 for y in rb)
    if sxx <= 0 or syy <= 0:
        return None
    value = math.fsum((x - ma) * (y - mb) for x, y in zip(ra, rb, strict=True))
    return max(-1.0, min(1.0, value / math.sqrt(sxx * syy)))


def rank_correlations(scored: dict[tuple, dict], keys: list[tuple] | None = None) -> dict:
    keys = sorted(scored) if keys is None else keys
    criterion = [scored[k]["criterion"] for k in keys]
    return {
        arm: spearman([scored[k][arm] for k in keys], criterion)
        for arm in ("c0", "c1", "c2")
    }


def top_overlap(scored: dict[tuple, dict], arm: str, k: int) -> float | None:
    if k < 1 or len(scored) < k:
        return None
    keys = sorted(scored)
    by_arm = sorted(keys, key=lambda key: scored[key][arm], reverse=True)[:k]
    by_criterion = sorted(keys, key=lambda key: scored[key]["criterion"], reverse=True)[:k]
    return len(set(by_arm) & set(by_criterion)) / k


def bootstrap_deltas(
    scored: dict[tuple, dict], settings: IncrementSettings, seed: int, repetitions: int
) -> dict:
    keys = sorted(scored)
    if len(keys) < 3 or repetitions < 100:
        raise ValueError("Too few players or repetitions for a bootstrap")
    rng = random.Random(seed)
    draws: dict[str, list[float]] = {"c1_c0": [], "c2_c0": []}
    for _ in range(repetitions):
        sample = [keys[rng.randrange(len(keys))] for _ in keys]
        values = rank_correlations(scored, sample)
        if None in values.values():
            continue
        draws["c1_c0"].append(values["c1"] - values["c0"])
        draws["c2_c0"].append(values["c2"] - values["c0"])
    if len(draws["c1_c0"]) < repetitions // 2:
        raise ValueError("Bootstrap failed on too many resamples")
    return {
        name: sorted(draws[name]) for name in draws
    }


def interval(draws: list[float]) -> list[float]:
    return [draws[int(0.025 * len(draws))],
            draws[min(len(draws) - 1, int(0.975 * len(draws)))]]


def run(
    rows: list[dict[str, Any]],
    players: list[tuple],
    settings: IncrementSettings = DEFAULT_SETTINGS,
    seed: int = 1729,
    repetitions: int = 10000,
) -> dict[str, Any]:
    """Paired rank-correlation differences with player-cluster intervals."""
    aggregated = _aggregate(rows, players)
    scored = score_players(aggregated, settings)
    if len(scored) < 3:
        raise ValueError("Too few scored players")
    base = rank_correlations(scored)
    draws = bootstrap_deltas(scored, settings, seed, repetitions)
    primary = interval(draws["c1_c0"])
    secondary = interval(draws["c2_c0"])
    return {
        "version": VERSION,
        "settings": settings,
        "players": len(scored),
        "top_k": settings.top_k,
        "rank_correlation": base,
        "deltas": {
            "c1_minus_c0": base["c1"] - base["c0"],
            "c2_minus_c0": base["c2"] - base["c0"],
        },
        "intervals": {"c1_minus_c0": primary, "c2_minus_c0": secondary},
        "labels": {
            "primary_c1_c0": classify_increment(primary, settings.ceiling, settings),
            "secondary_c2_c0": classify_increment(secondary, settings.ceiling, settings),
        },
        "top_overlap": {
            arm: top_overlap(scored, arm, settings.top_k) for arm in ("c0", "c1", "c2")
        },
        "notes": [
            "Rankings use window A only; the criterion is window-B xG per appearance.",
            "No probability model, no player label, no shortlist is produced.",
            "Development leagues only; the held-out league stays sealed.",
        ],
    }
