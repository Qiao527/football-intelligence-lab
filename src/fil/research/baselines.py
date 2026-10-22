"""Frozen pilot-only real-match baselines; no model selection or football value claim."""

import math
from collections import defaultdict

import pyarrow as pa

from fil.research.evaluation import (
    baseline_predictions,
    chronological_split,
    dependence_audit,
    evaluate,
    fit_baselines,
)

VERSION = "fil-worldcup-pilot-baselines-1"
FEATURES = ("context", "location", "forwardness", "gain_5", "gain_10", "gain_15")


def examples(events: pa.Table, process: dict, home_team_id: int) -> list[dict]:
    """Cutoff record alone supplies features; future evidence supplies labels only."""
    by_id = {r["event_id"]: r for r in events.to_pylist()}
    output = []
    for w in process["forecast_windows"]:
        if w["outcome"] is None or w["match_id"] == 8658:
            continue
        r = by_id[w["cutoff_event_id"]]
        future = [by_id[i] for i in w["outcome_event_ids"]]
        if len(future) != 5 or any(
            s["provider_index"] <= r["provider_index"]
            or s["period"] != r["period"]
            or s["possession_id"] != r["possession_id"]
            or s["team_id"] != r["team_id"]
            for s in future
        ):
            raise ValueError("Forecast evidence leakage or foreign period/owner")
        if r["match_id"] != w["match_id"] or r["team_id"] != r["possession_team_id"]:
            raise ValueError("Cutoff identity/owner mismatch")
        if w["feature_event_ids"] != [r["event_id"]] or w["outcome"] != int(
            any(s["event_type"] == "Shot" for s in future)
        ):
            raise ValueError("Outcome or feature lineage differs from source window")
        raw_home, raw_away = r["score_home_before"], r["score_away_before"]
        difference = (raw_home - raw_away) * (1 if r["team_id"] == home_team_id else -1)
        state = "leading" if difference > 0 else "trailing" if difference < 0 else "level"
        feature_geometry = [r[k] for k in ("x", "y", "end_x", "end_y")]

        def point(x, y):
            return (
                all(v is not None and math.isfinite(v) for v in (x, y))
                and 0 <= x <= 120
                and 0 <= y <= 80
            )

        start_valid, end_valid = point(r["x"], r["y"]), point(r["end_x"], r["end_y"])
        dx = r["end_x"] - r["x"] if start_valid and end_valid else None
        contexts = dict(
            context=f"period={r['period']}:state={state}",
            location=f"{min(int(r['end_x'] // 20), 5)}:{min(int(r['end_y'] // 20), 3)}"
            if end_valid
            else None,
            forwardness="nonpositive"
            if dx is not None and dx <= 0
            else "0to5"
            if dx is not None and dx <= 5
            else "5to10"
            if dx is not None and dx <= 10
            else "above10"
            if dx is not None
            else None,
            **{f"gain_{t}": str(dx >= t) if dx is not None else None for t in (5, 10, 15)},
        )
        output.append(
            dict(
                source="statsbomb_open_data",
                match_id=r["match_id"],
                event_id=r["event_id"],
                team_id=r["team_id"],
                period=r["period"],
                cutoff_provider_index=r["provider_index"],
                cutoff_period_elapsed_ms=r["period_elapsed_ms"],
                source_manifest_sha256=r["source_manifest_sha256"],
                feature_event_ids=[r["event_id"]],
                outcome_event_ids=w["outcome_event_ids"],
                outcome=w["outcome"],
                features=contexts,
                source_feature_geometry=feature_geometry,
                score_home_before=raw_home,
                score_away_before=raw_away,
            )
        )
    return output


def run(rows: list[dict], metadata: list[dict]) -> tuple[dict, list[dict]]:
    """Date protocol frozen before fitting; report every prespecified comparison."""
    if any(r["match_id"] == 8658 for r in rows):
        raise ValueError("Development fixture excluded from pilot experiment")
    parts = chronological_split(metadata, "2018-07-06", "2018-07-07")
    grouped = defaultdict(list)
    for r in rows:
        labels = [name for name, ids in parts.items() if (r["source"], r["match_id"]) in ids]
        if len(labels) != 1:
            raise ValueError("Foreign or overlapping partition")
        grouped[labels[0]].append(r)
    if set(grouped) != {"train", "validation", "test"}:
        raise ValueError("Empty outcome partition")
    results = {}
    predictions = []
    for feature in FEATURES:
        data = {
            label: [{**r, "context": r["features"][feature]} for r in values]
            for label, values in grouped.items()
        }
        model = fit_baselines(data["train"])
        comparison = {}
        for label in ("validation", "test"):
            scored = baseline_predictions(model, data[label])
            comparison[label] = evaluate(scored)
            comparison[label]["unsupported_context_rows"] = sum(
                not r["context_supported"] for r in scored
            )
            predictions.extend(
                {**r, "partition": label, "baseline_feature": feature} for r in scored
            )
        results[feature] = dict(
            training_prior=model["prior"],
            training_contexts=model["context"],
            comparisons=comparison,
        )
    return dict(
        version=VERSION,
        partitions={k: sorted(v) for k, v in parts.items()},
        partition_rows={k: len(v) for k, v in grouped.items()},
        dependence=dependence_audit(parts, metadata),
        results=results,
        status="pilot_diagnostic_only_not_scientifically_validated",
        limitations=(
            "One test match; no between-match interval. Quality-screened pilot, repeated "
            "teams/players, knockout selection and long-window censoring. "
            "No general football or importance conclusion."
        ),
    ), predictions
