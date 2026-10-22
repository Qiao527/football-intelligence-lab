"""Frozen future partition design and dependency-aware descriptive uncertainty."""

import math
import random
import statistics
from collections import defaultdict
from datetime import date

from fil.research.acquisition import PROPOSAL_SHA256, REVISION
from fil.research.evaluation import cluster_interval

VERSION = "fil-recorded-possession-study-1"
EXPOSED = frozenset({8649, 8650, 8651, 8652, 8655, 8656, 8658})


def partition_plan(proposal: dict, metadata: list[dict]) -> dict:
    """Plan only from held match metadata. Never acquire or open future event payloads."""
    ids = set(proposal["expansion_new_match_ids"])
    by = {m["match_id"]: m for m in metadata}
    if len(by) != len(metadata) or len(ids) != 57 or ids & EXPOSED or not ids <= by.keys():
        raise ValueError("Future scope is exactly the 57 unacquired matches")
    partitions = {"train": [], "validation": [], "test": []}
    for mid in sorted(ids):
        day = date.fromisoformat(by[mid]["match_date"])
        name = (
            "train"
            if day <= date(2018, 6, 26)
            else ("validation" if day <= date(2018, 7, 1) else "test")
        )
        partitions[name].append(
            dict(
                match_id=mid,
                match_date=day.isoformat(),
                team_ids=[by[mid][k][k + "_id"] for k in ("home_team", "away_team")],
                expected_files=[
                    dict(f, acquired_payload_sha256=None)
                    for f in proposal["files"]
                    if f["path"].endswith(f"/{mid}.json")
                ],
            )
        )
    if any(not rows for rows in partitions.values()):
        raise ValueError("Predeclared partitions empty: stop, do not reallocate")
    return dict(
        version=VERSION,
        partitions=partitions,
        excluded_exposed_match_ids=sorted(EXPOSED),
        metadata_sha256=proposal["metadata_source_sha256"],
        revision=REVISION,
        approved_enumeration_sha256=PROPOSAL_SHA256,
        authorization="PENDING_REVISED_POLICY_ACCEPTANCE",
        expansion_gate="BLOCKED",
        event_payloads_opened=False,
        evaluated=False,
    )


def components(matches: list[dict]) -> dict:
    """Join matches sharing provider team OR player; missing identity prevents certification."""
    keys = [(m["source"], m["match_id"]) for m in matches]
    if len(keys) != len(set(keys)) or len({k[0] for k in keys}) > 1:
        raise ValueError("Unique single-provider match identities required")
    groups = [{k} for k in keys]
    memberships = defaultdict(set)
    incomplete = []
    for k, m in zip(keys, matches, strict=True):
        for field in ("team_ids", "player_ids"):
            if m.get(field) is None:
                incomplete.append(dict(match=list(k), field=field))
            else:
                for i in m[field]:
                    memberships[k[0], field, i].add(k)
    for linked in memberships.values():
        merge = [g for g in groups if g & linked]
        if merge:
            joined = set.union(*merge)
            groups = [g for g in groups if not g & joined] + [joined]
    return dict(
        components=[sorted(g) for g in sorted(groups, key=lambda g: sorted(g))],
        missing_identity=incomplete,
        independence_certified=False,
    )


def paired_uncertainty(effects: list[dict], metadata: list[dict]) -> dict:
    """Conservative component sensitivity alongside conditional match bootstrap.

    Components do not prove exchangeability; disconnected clusters are still one
    tournament. Resample component weighted effect around the equal-match estimate.
    """
    by = {(r["source"], r["match_id"]): r["effect"] for r in effects}
    if len(by) != len(effects) or not by or any(not math.isfinite(v) for v in by.values()):
        raise ValueError("Distinct finite match effects required")
    graph = components(metadata)
    known = {tuple(k) for g in graph["components"] for k in g}
    if set(by) != known:
        raise ValueError("Metadata must exactly cover evaluated match effects")
    interval = None
    if not graph["missing_identity"] and len(graph["components"]) >= 2:
        values = [(sum(by[tuple(k)] for k in g), len(g)) for g in graph["components"]]
        rng = random.Random(1729)
        samples = []
        for _ in range(10000):
            draw = rng.choices(values, k=len(values))
            samples.append(sum(s for s, _ in draw) / sum(n for _, n in draw))
        samples.sort()
        interval = [samples[250], samples[9750]]
    return dict(
        version=VERSION,
        equal_match_effect=statistics.mean(by.values()),
        match_bootstrap_conditional_interval=cluster_interval(list(by.values()), 1729, 10000),
        dependency=graph,
        component_interval=interval,
        component_interval_status="withheld_incomplete_identity"
        if graph["missing_identity"]
        else "withheld_single_component"
        if len(graph["components"]) < 2
        else "conditional_size_weighted_component_bootstrap_not_certified_independence",
        inferential_independence_certified=False,
    )


def fit_weighted_baseline(rows: list[dict], feature: str, alpha: float) -> dict:
    """Training-only shrinkage in match units; alpha must be frozen by development CV."""
    if alpha not in (0.25, 0.5, 1, 2, 4):
        raise ValueError("Alpha outside the frozen grid")
    matches, bins = set(), defaultdict(lambda: [0.0, 0.0])
    total, positives = 0.0, 0.0
    weights = defaultdict(float)
    seen = set()
    for r in rows:
        key = (r["source"], r["match_id"])
        uid = (*key, r["cutoff_event_id"])
        if r.get("partition") != "train" or key[0] != "statsbomb_open_data" or uid in seen:
            raise ValueError("Training-only unique provider cutoffs required")
        seen.add(uid)
        y, w = r["outcome"], r["within_match_possession_weight"]
        if y not in (0, 1) or w is None or not math.isfinite(w) or w <= 0:
            raise ValueError("Confirmed labels and positive finite weights required")
        if not r["feature_indices"] or max(r["feature_indices"]) > r["cutoff_provider_index"]:
            raise ValueError("Future or absent feature lineage")
        matches.add(key)
        weights[key] += w
        total += w
        positives += y * w
        name = r["features"].get(feature)
        if name is not None:
            bins[name][0] += y * w
            bins[name][1] += w
    if len(matches) < 2 or any(not math.isclose(w, 1) for w in weights.values()):
        raise ValueError("At least two unit-weight matches required; not sample adequacy")
    prior = (positives + 0.5) / (total + 1)
    return dict(
        version=VERSION,
        training_matches=sorted(matches),
        feature=feature,
        alpha=alpha,
        prior=prior,
        bins={k: (s + alpha * prior) / (n + alpha) for k, (s, n) in bins.items()},
        scientifically_validated=False,
    )


def predict_weighted(model: dict, rows: list[dict]) -> list[float]:
    """Held-match record-order forecasts, no implicit scoring or silent refitting."""
    if any((r["source"], r["match_id"]) in model["training_matches"] for r in rows):
        raise ValueError("Training/prediction match overlap")
    if any(
        r["source"] != "statsbomb_open_data"
        or not r["feature_indices"]
        or max(r["feature_indices"]) > r["cutoff_provider_index"]
        for r in rows
    ):
        raise ValueError("Provider mismatch or feature cutoff leakage")
    return [model["bins"].get(r["features"].get(model["feature"]), model["prior"]) for r in rows]
