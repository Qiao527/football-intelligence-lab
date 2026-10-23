"""Exploratory recorded retreat/re-entry at a fixed possession landmark; no model fit."""

import argparse
import json
import math
import re
import statistics
import tempfile
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from fil.research.accepted_corpus import write_bundle
from fil.research.acquisition import digest
from fil.research.eligibility import ordered_score
from fil.research.integrity_review import verify_artifact
from fil.research.pilot import encode
from fil.research.prospective import components

VERSION = "fil-recorded-reentry-study-1"
PROTOCOL = Path("docs/research/REENTRY_PROTOCOL.md")
PROTOCOL_SHA = "873fec08c970d4bb2181018fe3a666a6638e0a5e51c11b9ce770567436980da1"
PARENT_SHA = "c02124906e317733e08bafc9fe52b8898bcf607659760054033461a88ce4cb99"
VARIANTS = {
    "primary": (80, 5, False),
    "boundary75": (75, 5, False),
    "boundary85": (85, 5, False),
    "drop10": (80, 10, False),
    "pass_only": (80, 5, True),
}


def geometry(e: dict) -> tuple[list, list] | None:
    """Only completed provider passes and explicit recorded carries can establish arrivals."""
    kind = e["type"]["name"]
    details = e.get(kind.lower())
    if kind not in ("Pass", "Carry") or not isinstance(details, dict):
        return None
    if kind == "Pass" and "outcome" in details:
        return None
    start, end = e.get("location"), details.get("end_location")
    for point in (start, end):
        if not isinstance(point, list) or len(point) != 2:
            return None
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in point):
            return None
        if not (0 <= point[0] <= 120 and 0 <= point[1] <= 80):
            return None
    return start, end


def closure(raw: list[dict], indices: list[int], period: int) -> list[str]:
    """Source closure only, independent of unresolved physical Half End timestamps."""
    ends = [e for e in raw if e["period"] == period and e["type"]["name"] == "Half End"]
    if any(
        (e.get("half_end") or {}).get(k)
        for e in ends
        for k in ("early_video_end", "match_suspended")
    ):
        return []
    after = raw[indices[-1] + 1] if indices[-1] + 1 < len(raw) else None
    if after and after["period"] == period and after.get("possession") is not None:
        return [after["id"]]
    if (
        len(ends) != 2
        or len({e["team"]["id"] for e in ends}) != 2
        or ends[0]["id"] not in ends[1].get("related_events", [])
        or ends[1]["id"] not in ends[0].get("related_events", [])
    ):
        return []
    actions = [
        raw[i]
        for i in indices
        if raw[i]["type"]["name"] not in ("Half Start", "Half End", "Starting XI")
    ]
    if not actions or any(e["index"] <= actions[-1]["index"] for e in ends):
        return []
    if any(
        e.get("possession") != raw[indices[0]]["possession"] and e["type"]["name"] != "Half End"
        for e in raw
        if actions[-1]["index"] < e["index"] <= ends[-1]["index"]
    ):
        return []
    return [e["id"] for e in ends]


def extract(raw: list[dict], source: dict, variant: str) -> list[dict]:
    """At most one opportunity per original membership, retaining every exclusion."""
    if not raw or len({e["id"] for e in raw}) != len(raw):
        raise ValueError("Unique nonempty source required")
    if any(
        a["index"] >= b["index"] or a["period"] > b["period"]
        for a, b in zip(raw, raw[1:], strict=False)
    ):
        raise ValueError("Original increasing source order required")
    boundary, drop, pass_only = VARIANTS[variant]
    decisions = ordered_score(raw, source["metadata"])["decisions"]
    goals = [d for d in decisions if d["domain"] == "match_play" and d["scored"]]
    groups = defaultdict(list)
    for i, e in enumerate(raw):
        if e.get("possession") is not None:
            groups[e["possession"]].append(i)
    teams = {source["metadata"][k][k + "_id"] for k in ("home_team", "away_team")}
    output = []
    for pid, ix in groups.items():
        es = [raw[i] for i in ix]
        owners = {e.get("possession_team", {}).get("id") for e in es}
        owner, period = es[0].get("possession_team", {}).get("id"), es[0]["period"]
        reasons = []
        if len({e["period"] for e in es}) != 1 or period not in (1, 2, 3, 4):
            reasons.append("unsupported_or_cross_period")
        if len(owners) != 1 or owner not in teams:
            reasons.append("ambiguous_owner")
        if ix != list(range(ix[0], ix[-1] + 1)):
            reasons.append("noncontiguous_or_unassigned")
        row = dict(
            match_id=source["match_id"],
            possession_id=pid,
            team_id=owner,
            period=period,
            variant=variant,
            source_manifest_sha256=source["source_manifest_sha256"],
            source_event_ids=[e["id"] for e in es],
            exclusion_reasons=reasons,
            feature=None,
            outcome=None,
            full_segment_outcome=None,
        )
        output.append(row)
        if reasons:
            continue
        own = [e for e in es if e["team"]["id"] == owner]
        moves = [
            e for e in own if e["type"]["name"] in (("Pass",) if pass_only else ("Pass", "Carry"))
        ]
        entry = next(
            (
                j
                for j, e in enumerate(moves)
                if geometry(e) is not None and geometry(e)[0][0] < boundary <= geometry(e)[1][0]
            ),
            None,
        )
        if entry is None:
            reasons.append("no_observed_entry")
            continue
        first = moves[entry]
        row["entry_event_id"] = first["id"]
        row["entry_provider_index"] = first["index"]
        if any(geometry(e) is None for e in moves[:entry]):
            reasons.append("first_entry_ambiguous_after_failed_or_unknown_move")
        pattern = (first.get("play_pattern") or {}).get("name")
        if pattern not in ("Regular Play", "From Counter"):
            reasons.append("nonqualifying_native_play_pattern")
        window = moves[entry + 1 : entry + 4]
        row["landmark_window_ids"] = [e["id"] for e in window]
        if len(window) < 3:
            reasons.append("short_before_landmark")
        if any(geometry(e) is None for e in window):
            reasons.append("failed_or_unknown_landmark_geometry")
        if window and any(
            e["type"]["name"] == "Shot" and first["index"] < e["index"] <= window[-1]["index"]
            for e in own
        ):
            reasons.append("shot_before_landmark")
        if reasons:
            continue
        landmark = window[-1]
        retreat = [
            e
            for e in window
            if geometry(e)[0][0] >= boundary and geometry(e)[1][0] <= boundary - drop
        ]
        reentry = [e for e in window if geometry(e)[0][0] < boundary <= geometry(e)[1][0]]
        witnesses = [
            [a["id"], b["id"]] for a in retreat for b in reentry if a["index"] < b["index"]
        ]
        future = [
            e
            for e in own
            if e["index"] > landmark["index"] and e["type"]["name"] in ("Pass", "Carry", "Shot")
        ][:3]
        shots = [e for e in future if e["type"]["name"] == "Shot"]
        all_shots = [
            e for e in own if e["index"] > landmark["index"] and e["type"]["name"] == "Shot"
        ]
        end_ids = closure(raw, ix, period)
        y = 1 if shots else 0 if len(future) == 3 or end_ids else None
        full_y = 1 if all_shots else 0 if end_ids else None
        prior_goals = [g for g in goals if g["provider_index"] < landmark["index"]]
        diff = sum(1 if g["beneficiary_team_id"] == owner else -1 for g in prior_goals)
        score = "level" if diff == 0 else "leading" if diff > 0 else "trailing"
        endpoint = geometry(landmark)[1]
        prefix_passes = sum(
            e["type"]["name"] == "Pass" and geometry(e) is not None
            for e in own
            if e["index"] <= landmark["index"]
        )
        volume = "0-2" if prefix_passes <= 2 else "3-5" if prefix_passes <= 5 else "6+"
        cell = [min(int(endpoint[0] / 40), 2), min(int(endpoint[1] / 40), 1)]
        row.update(
            feature=bool(witnesses),
            outcome=y,
            full_segment_outcome=full_y,
            landmark_event_id=landmark["id"],
            landmark_provider_index=landmark["index"],
            landmark_endpoint=endpoint,
            landmark_cell=cell,
            score_state=score,
            prior_goal_event_ids=[i for g in prior_goals for i in g["source_event_ids"]],
            retreat_ids=[e["id"] for e in retreat],
            reentry_ids=[e["id"] for e in reentry],
            ordered_witnesses=witnesses,
            cooccurrence=bool(retreat and reentry),
            future_horizon_ids=[e["id"] for e in future],
            shot_event_ids=[e["id"] for e in shots],
            all_later_shot_ids=[e["id"] for e in all_shots],
            closure_ids=end_ids,
            prefix_passes=prefix_passes,
            pass_volume_bin=volume,
            window_passes=sum(e["type"]["name"] == "Pass" for e in window),
            source_play_pattern=pattern,
            source_known_horizon_xg_sum=math.fsum(
                e["shot"]["statsbomb_xg"]
                for e in shots
                if e["shot"].get("statsbomb_xg") is not None
            ),
            missing_horizon_xg_ids=[
                e["id"] for e in shots if e["shot"].get("statsbomb_xg") is None
            ],
        )
    return output


def counts(rows: list[dict]) -> dict:
    n = len(rows)
    positive = sum(r["outcome"] == 1 for r in rows)
    unknown = sum(r["outcome"] is None for r in rows)
    known = n - unknown
    return dict(
        n=n,
        positive=positive,
        negative=known - positive,
        unresolved=unknown,
        observed_rate=positive / known if known else None,
        prevalence_bounds=[positive / n, (positive + unknown) / n] if n else None,
    )


def comparison(rows: list[dict], context: bool) -> dict:
    groups = defaultdict(lambda: [[], []])
    for r in rows:
        key = (r["pass_volume_bin"], *r["landmark_cell"], r["window_passes"])
        if context:
            key += (r["team_id"], r["match_id"], r["period"], r["score_state"])
        groups[key][int(r["feature"])].append(r)
    shared, excluded, weighted, mass, bounds = [], 0, [], 0, [0.0, 0.0]
    for key, arms in sorted(groups.items(), key=lambda item: str(item[0])):
        if not all(arms):
            excluded += sum(map(len, arms))
            continue
        a, b = map(counts, arms)
        weight = min(a["n"], b["n"])
        lo = b["prevalence_bounds"][0] - a["prevalence_bounds"][1]
        hi = b["prevalence_bounds"][1] - a["prevalence_bounds"][0]
        bounds[0] += weight * lo
        bounds[1] += weight * hi
        mass += weight
        effect = (
            b["observed_rate"] - a["observed_rate"]
            if all(x["observed_rate"] is not None for x in (a, b))
            else None
        )
        if effect is not None:
            weighted.append((weight, effect))
        shared.append(
            dict(
                stratum=list(key),
                nonmotif=a,
                motif=b,
                effect=effect,
                weight=weight,
                difference_bounds=[lo, hi],
                source_units=[[r["match_id"], r["possession_id"]] for arm in arms for r in arm],
            )
        )
    return dict(
        shared_strata=shared,
        excluded_no_arm_overlap=excluded,
        matched_rows=sum(s[a]["n"] for s in shared for a in ("nonmotif", "motif")),
        observed_difference=sum(w * e for w, e in weighted) / sum(w for w, _ in weighted)
        if weighted
        else None,
        difference_bounds=[b / mass for b in bounds] if mass else None,
        statistical_or_causal_identification_claimed=False,
    )


def repeat_support(rows: list[dict]) -> dict:
    groups = defaultdict(list)
    for r in rows:
        groups[
            r["team_id"], r["match_id"], r["period"], r["score_state"], r["landmark_cell"][1]
        ].append(r)
    supported = {k: v for k, v in groups.items() if len(v) >= 5}
    pairs = []
    for (ka, a), (kb, b) in combinations(sorted(supported.items()), 2):
        if ka[1] == kb[1] or ka[2:] != kb[2:]:
            continue
        ra, rb = sum(r["feature"] for r in a) / len(a), sum(r["feature"] for r in b) / len(b)
        pairs.append(
            dict(
                left=list(ka),
                right=list(kb),
                left_n=len(a),
                right_n=len(b),
                left_rate=ra,
                right_rate=rb,
                absolute_difference=abs(ra - rb),
                same_team=ka[0] == kb[0],
            )
        )
    return dict(
        pairs=pairs,
        supported_team_matches=len({k[:2] for k in supported}),
        total_team_matches=len({(r["team_id"], r["match_id"]) for r in rows}),
        pairs_are_independent=False,
        mean_same_team_difference=statistics.mean(
            p["absolute_difference"] for p in pairs if p["same_team"]
        )
        if any(p["same_team"] for p in pairs)
        else None,
        mean_other_team_difference=statistics.mean(
            p["absolute_difference"] for p in pairs if not p["same_team"]
        )
        if any(not p["same_team"] for p in pairs)
        else None,
    )


def summarize(rows: list[dict]) -> dict:
    eligible = [r for r in rows if r["feature"] is not None]
    per = []
    for team, match in sorted({(r["team_id"], r["match_id"]) for r in eligible}):
        units = [r for r in eligible if (r["team_id"], r["match_id"]) == (team, match)]
        per.append(
            dict(
                team_id=team,
                match_id=match,
                n=len(units),
                motif=sum(r["feature"] for r in units),
                context=comparison(units, True),
            )
        )
    effects = [
        r["context"]["observed_difference"]
        for r in per
        if r["context"]["observed_difference"] is not None
    ]
    return dict(
        memberships=len(rows),
        eligible=len(eligible),
        exclusions=dict(Counter(reason for r in rows for reason in r["exclusion_reasons"])),
        motif=counts([r for r in eligible if r["feature"]]),
        nonmotif=counts([r for r in eligible if not r["feature"]]),
        cooccurrence=sum(r["cooccurrence"] for r in eligible),
        cooccurrence_not_ordered=sum(r["cooccurrence"] and not r["feature"] for r in eligible),
        volume_location=comparison(eligible, False),
        team_match_context=comparison(eligible, True),
        team_matches=per,
        equal_supported_team_match_difference=statistics.mean(effects) if effects else None,
        repeat_support=repeat_support(eligible),
        whole_segment_outcome_disagreements=sum(
            r["outcome"] != r["full_segment_outcome"] for r in eligible
        ),
        population_interval=None,
        independence_certified=False,
    )


def run(parent: Path, output: Path, revision: str) -> Path:
    """Verify approved immutable inputs; write a new local artifact, never acquire data."""
    if digest(PROTOCOL.read_bytes()) != PROTOCOL_SHA:
        raise ValueError("Frozen re-entry protocol changed")
    if not re.fullmatch("[0-9a-f]{40}", revision):
        raise ValueError("Exact calculation revision required")
    if digest((parent / "manifest.json").read_bytes()) != PARENT_SHA:
        raise ValueError("Exact PR21 design artifact required")
    m = verify_artifact(parent)
    protected = dict(m["protected_inputs"])
    protected.update({str(p.resolve()): digest(p.read_bytes()) for p in parent.iterdir()})
    if any(digest(Path(p).read_bytes()) != h for p, h in protected.items()):
        raise ValueError("Historical/source input changed")
    if any(output.resolve().is_relative_to(Path(p).parent.resolve()) for p in protected):
        raise ValueError("Output overlaps protected source")
    old = json.loads((Path(m["parent_bundle"]) / "manifest.json").read_bytes())
    sources = json.loads((Path(old["parent_bundle"]) / "source-inputs.json").read_bytes())
    rows, metadata, unassigned = defaultdict(list), [], []
    for source in sources:
        raw = json.loads(Path(source["events"]).read_bytes())
        roster = json.loads(Path(source["lineups"]).read_bytes())
        metadata.append(
            dict(
                source="statsbomb_open_data",
                match_id=source["match_id"],
                team_ids=[t["team_id"] for t in roster],
                player_ids=[p["player_id"] for t in roster for p in t["lineup"]],
            )
        )
        unassigned.extend([source["match_id"], e["id"]] for e in raw if e.get("possession") is None)
        for name in VARIANTS:
            rows[name].extend(extract(raw, source, name))
    summaries = {name: summarize(records) for name, records in rows.items()}
    primary = {(r["match_id"], r["possession_id"]): r for r in rows["primary"]}
    sensitivity = {}
    for name, records in rows.items():
        common = [
            (primary[r["match_id"], r["possession_id"]], r)
            for r in records
            if r["feature"] is not None
            and primary[r["match_id"], r["possession_id"]]["feature"] is not None
        ]
        sensitivity[name] = dict(
            common_eligible=len(common),
            feature_disagreements=sum(a["feature"] != b["feature"] for a, b in common),
            landmark_disagreements=sum(
                a["landmark_event_id"] != b["landmark_event_id"] for a, b in common
            ),
        )
    summary = dict(
        version=VERSION,
        variants=summaries,
        sensitivity=sensitivity,
        dependency=components(metadata),
        unassigned_source_ids=unassigned,
        all_matches_development_exposed=True,
        models_fitted=False,
        human_judgments_collected=0,
        physical_time_or_direction_certified=False,
    )
    target = output / VERSION / revision
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".reentry-") as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        (stage / "evidence.json").write_text(encode(rows))
        (stage / "summary.json").write_text(encode(summary))
        (stage / "source-inputs.json").write_text(encode(sources))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=revision,
                    protocol_sha256=PROTOCOL_SHA,
                    parent_bundle=str(parent.resolve()),
                    parent_manifest_sha256=PARENT_SHA,
                    protected_inputs=protected,
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                    rights="LOCAL ONLY; existing authorized noncommercial descriptive scope",
                )
            )
        )
        if any(digest(Path(p).read_bytes()) != h for p, h in protected.items()):
            raise ValueError("Source changed during extraction")
        write_bundle(stage, target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/interim/reentry-study"))
    parser.add_argument("--pipeline-revision", required=True)
    args = parser.parse_args()
    print(encode(dict(bundle=str(run(args.parent, args.output, args.pipeline_revision).resolve()))))


if __name__ == "__main__":
    main()
