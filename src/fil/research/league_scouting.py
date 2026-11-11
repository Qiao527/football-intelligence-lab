"""League windows and the stage A reliability/ceiling decision.

Implements the estimands of `docs/research/LEAGUE_SCOUTING_PROTOCOL.md`. It never
ranks players and never scores the criterion: it returns a stop or proceed decision
for a within-season, per-appearance design with no minutes.
"""

import json
import math
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

VERSION = "fil-league-scouting-1"
MIN_APPEARANCES = 5
METRICS = ("shots", "goals", "xg", "npxg")
ROW_KEYS = ("source", "match_id", "team_id", "player_id", "match_date", "window",
            "fixture_index", "position_label", "position_names", "league", "shots",
            "goals", "xg", "npxg", "op_npxg")


@dataclass(frozen=True)
class LeagueThresholds:
    reliability_point: float = 0.50
    reliability_lower: float = 0.30
    reliability_margin: float = 0.10
    ceiling: float = 0.45
    minimum_appearances: int = MIN_APPEARANCES


DEFAULT_THRESHOLDS = LeagueThresholds()


def team_windows(
    matches: list[dict[str, Any]], drop_tail: int = 0
) -> dict[tuple, dict[str, Any]]:
    """Split each team's own fixture list at the halfway point of its length.

    `drop_tail` removes the team's final fixtures entirely, as a pre-declared
    end-of-season sensitivity; dropped matches are not placed in either window.
    """
    if not matches:
        raise ValueError("Empty match list")
    seen: set[int] = set()
    by_team: dict[int, list[dict]] = defaultdict(list)
    for match in matches:
        if match["match_id"] in seen:
            raise ValueError("Duplicate match metadata")
        seen.add(match["match_id"])
        for team in (match["home_team_id"], match["away_team_id"]):
            by_team[team].append(match)
    out: dict[tuple, dict[str, Any]] = {}
    for team, fixtures in by_team.items():
        ordered = sorted(fixtures, key=lambda m: (m["match_date"], m["match_id"]))
        usable = ordered[: len(ordered) - drop_tail] if drop_tail else ordered
        split = math.ceil(len(usable) / 2)
        for index, match in enumerate(usable):
            out[(match["match_id"], team)] = {
                "window": "A" if index < split else "B",
                "fixture_index": index,
                "match_date": match["match_date"],
            }
        for match in ordered[len(usable):]:
            out[(match["match_id"], team)] = {
                "window": "DROP",
                "fixture_index": None,
                "match_date": match["match_date"],
            }
    return out


def build_rows(
    events: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    windows: dict[tuple, dict[str, Any]],
    league: str = "unknown",
) -> list[dict[str, Any]]:
    """Observed actor appearances with source shots and verbatim position metadata."""
    labels: dict[tuple, tuple[str | None, tuple[str, ...]]] = {}
    for entry in lineups:
        key = (entry["match_id"], entry["team_id"], entry["player_id"])
        positions = entry["positions"]
        names = tuple(sorted({
            item.get("position") for item in positions or []
            if isinstance(item, dict) and item.get("position")
        }))
        labels[key] = (json.dumps(positions, sort_keys=True) if positions else None, names)
    grouped: dict[tuple, dict[str, Any]] = {}
    for event in events:
        if event["period"] == 5 or event["player_id"] is None:
            continue
        key = (event["match_id"], event["team_id"], event["player_id"])
        row = grouped.get(key)
        if row is None:
            slot = windows.get((event["match_id"], event["team_id"]))
            if slot is None:
                raise ValueError("Event team is absent from the match metadata")
            if slot["window"] == "DROP":
                continue
            row = grouped[key] = {
                "source": event.get("source"),
                "match_id": event["match_id"],
                "team_id": event["team_id"],
                "player_id": event["player_id"],
                "match_date": slot["match_date"],
                "window": slot["window"],
                "fixture_index": slot["fixture_index"],
                "league": league,
                "position_label": labels.get(key, (None, ()))[0],
                "position_names": labels.get(key, (None, ()))[1],
                "shots": 0,
                "goals": 0,
                "xg": 0.0,
                "npxg": 0.0,
                "op_npxg": 0.0,
            }
        if event["event_type"] == "Shot":
            xg = event["shot_xg"]
            if not isinstance(xg, (int, float)) or not math.isfinite(xg) or not 0 <= xg <= 1:
                raise ValueError("Shot without a usable source xG")
            row["shots"] += 1
            row["goals"] += int(event["shot_outcome"] == "Goal")
            row["xg"] += float(xg)
            if event["shot_type"] != "Penalty":
                row["npxg"] += float(xg)
                if event["shot_type"] == "Open Play":
                    row["op_npxg"] += float(xg)
    return sorted(grouped.values(), key=lambda r: (r["team_id"], r["player_id"],
                                                   r["match_date"], r["match_id"]))


def _validate(rows: list[dict[str, Any]]) -> None:
    seen: set[tuple] = set()
    for row in rows:
        missing = [k for k in ROW_KEYS if k not in row]
        if missing:
            raise ValueError(f"Row is missing fields: {missing}")
        if row["window"] not in ("A", "B"):
            raise ValueError("Unsupported window")
        key = (row["match_id"], row["team_id"], row["player_id"])
        if key in seen:
            raise ValueError("Duplicate player appearance")
        seen.add(key)


def included_players(
    rows: list[dict[str, Any]], thresholds: LeagueThresholds = DEFAULT_THRESHOLDS
) -> dict[str, Any]:
    """Players with the minimum appearances in both windows."""
    _validate(rows)
    counts: dict[tuple, dict[str, int]] = defaultdict(lambda: {"A": 0, "B": 0})
    for row in rows:
        counts[(row["player_id"], row["team_id"])][row["window"]] += 1
    kept = sorted(
        key for key, value in counts.items()
        if value["A"] >= thresholds.minimum_appearances
        and value["B"] >= thresholds.minimum_appearances
    )
    return {
        "players": kept,
        "observed_players": len(counts),
        "excluded": len(counts) - len(kept),
        "median_appearances_a": statistics.median(
            [counts[k]["A"] for k in kept]
        ) if kept else None,
        "median_appearances_b": statistics.median(
            [counts[k]["B"] for k in kept]
        ) if kept else None,
    }


def consecutive_pairs(
    rows: list[dict[str, Any]], metric: str, players: list[tuple]
) -> dict[tuple, list[tuple[float, float]]]:
    """Adjacent window-A appearances per player, keyed by player."""
    if metric not in METRICS:
        raise ValueError(f"Unsupported metric: {metric!r}")
    keep = set(players)
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        key = (row["player_id"], row["team_id"])
        if key in keep and row["window"] == "A":
            grouped[key].append(row)
    pairs: dict[tuple, list[tuple[float, float]]] = {}
    for key, appearances in grouped.items():
        ordered = sorted(appearances, key=lambda r: (r["fixture_index"], r["match_id"]))
        pairs[key] = [
            (float(ordered[i][metric]), float(ordered[i + 1][metric]))
            for i in range(0, len(ordered) - 1, 2)
        ]
    return pairs


def pearson(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = math.fsum((x - mx) ** 2 for x in xs)
    syy = math.fsum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    value = math.fsum((x - mx) * (y - my) for x, y in pairs) / math.sqrt(sxx * syy)
    return max(-1.0, min(1.0, value))


def spearman_brown(r: float, k: float) -> float:
    """Composite reliability for k parallel measurements; k may be fractional."""
    if not -1 <= r <= 1 or k < 1:
        raise ValueError("Invalid reliability or measurement count")
    denominator = 1 + (k - 1) * r
    if denominator <= 0:
        raise ValueError("Spearman-Brown undefined")
    return k * r / denominator


def _composite(r: float, k: float) -> float | None:
    """Spearman-Brown with an undefined case reported rather than raised."""
    try:
        return spearman_brown(r, k)
    except ValueError:
        return None


def bootstrap_players(
    pairs: dict[tuple, list[tuple[float, float]]],
    seed: int = 1729,
    repetitions: int = 10000,
) -> list[float] | None:
    """Resample players, never individual pairs, and recompute r_single."""
    keys = sorted(k for k, v in pairs.items() if v)
    if len(keys) < 3 or repetitions < 100:
        return None
    rng = random.Random(seed)
    draws: list[float] = []
    attempts = 0
    while len(draws) < repetitions and attempts < repetitions * 20:
        attempts += 1
        sample = [keys[rng.randrange(len(keys))] for _ in keys]
        flat = [pair for key in sample for pair in pairs[key]]
        value = pearson(flat)
        if value is not None:
            draws.append(value)
    if len(draws) < repetitions // 2:
        return None
    draws.sort()
    return [draws[int(0.025 * len(draws))],
            draws[min(len(draws) - 1, int(0.975 * len(draws)))]]


def stable_position_players(rows: list[dict[str, Any]], players: list[tuple]) -> list[tuple]:
    """Players whose modal recorded position does not change between windows."""
    keep = set(players)
    counts: dict[tuple, dict[str, dict[str, int]]] = defaultdict(
        lambda: {"A": defaultdict(int), "B": defaultdict(int)}
    )
    for row in rows:
        key = (row["player_id"], row["team_id"])
        if key in keep and row["position_names"]:
            for name in row["position_names"]:
                counts[key][row["window"]][name] += 1
    stable = []
    for key, windows in counts.items():
        if not windows["A"] or not windows["B"]:
            continue
        modal = {
            window: max(sorted(names), key=lambda n: names[n])
            for window, names in windows.items()
        }
        if modal["A"] == modal["B"]:
            stable.append(key)
    return sorted(stable)


def position_change_fraction(
    rows: list[dict[str, Any]], players: list[tuple]
) -> float | None:
    """Share of included players whose recorded position metadata differs by window."""
    keep = set(players)
    counts: dict[tuple, dict[str, dict[str, int]]] = defaultdict(
        lambda: {"A": defaultdict(int), "B": defaultdict(int)}
    )
    for row in rows:
        key = (row["player_id"], row["team_id"])
        if key in keep and row["position_names"]:
            for name in row["position_names"]:
                counts[key][row["window"]][name] += 1
    comparable = {
        k: v for k, v in counts.items()
        if v["A"] and v["B"]
    }
    if not comparable:
        return None
    changed = 0
    for windows in comparable.values():
        modal = {
            window: max(sorted(names), key=lambda n: names[n])
            for window, names in windows.items()
        }
        changed += modal["A"] != modal["B"]
    return changed / len(comparable)


def stage_a(
    rows: list[dict[str, Any]],
    thresholds: LeagueThresholds = DEFAULT_THRESHOLDS,
    seed: int = 1729,
    repetitions: int = 10000,
    restrict: list[tuple] | None = None,
) -> dict[str, Any]:
    """Reliability and ceiling decision for the league population."""
    universe = included_players(rows, thresholds)
    players = list(restrict) if restrict is not None else universe["players"]
    if not players:
        raise ValueError("No player meets the per-window appearance minimum")
    estimates = {}
    for metric in METRICS:
        pairs = consecutive_pairs(rows, metric, players)
        flat = [pair for value in pairs.values() for pair in value]
        estimates[metric] = {
            "r_single": pearson(flat),
            "interval": bootstrap_players(pairs, seed, repetitions),
            "pairs": len(flat),
        }
    k_a = universe["median_appearances_a"]
    k_b = universe["median_appearances_b"]
    xg = estimates["xg"]["r_single"]
    goals = estimates["goals"]["r_single"]
    if xg is None or k_a is None or k_b is None:
        raise ValueError("Reliability is undefined for this sample")
    r_obs = _composite(xg, k_a)
    r_crit = _composite(xg, k_b)
    if r_obs is None or r_crit is None:
        return {
            "version": VERSION,
            "universe": {**universe, "players": len(players),
                     "restricted": restrict is not None},
            "metrics": estimates,
            "reliability_gate": {"passed": False, "reason": "unstable_composite"},
            "ceiling_gate": None,
            "stage": "stop_reliability",
        }
    lower = estimates["xg"]["interval"][0] if estimates["xg"]["interval"] else None
    lower_composite = spearman_brown(lower, k_a) if lower is not None and lower > -1 else None
    comparative = None if goals is None else xg - goals
    passed = (
        r_obs >= thresholds.reliability_point
        and lower_composite is not None
        and lower_composite >= thresholds.reliability_lower
        and (comparative is None or comparative >= -thresholds.reliability_margin)
    )
    ceiling = math.sqrt(max(0.0, r_obs) * max(0.0, r_crit))
    ceiling_passed = ceiling >= thresholds.ceiling
    return {
        "version": VERSION,
        "universe": {**universe, "players": len(players),
                     "restricted": restrict is not None},
        "median_appearances_a": k_a,
        "median_appearances_b": k_b,
        "metrics": estimates,
        "r_single": xg,
        "r_obs": r_obs,
        "r_crit": r_crit,
        "comparative_margin": comparative,
        "reliability_gate": {
            "passed": passed,
            "r_obs": r_obs,
            "r_obs_lower": lower_composite,
            "thresholds": thresholds,
        },
        "ceiling_gate": {"passed": ceiling_passed, "ceiling": ceiling,
                         "threshold": thresholds.ceiling},
        "position_change_fraction": position_change_fraction(rows, players),
        "stage": "proceed" if passed and ceiling_passed else
                 "stop_ceiling" if passed else "stop_reliability",
        "notes": [
            "Per-appearance only; minutes are not certified and per-90 is blocked.",
            "Pairs are adjacent fixtures inside window A; players, not pairs, resampled.",
            "r_crit is a window-B composite, unlike the v1 one-appearance criterion.",
            "No ranking, criterion score or ability label is produced here.",
        ],
    }
