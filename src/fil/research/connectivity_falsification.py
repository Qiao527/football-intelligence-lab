"""Descriptive falsification audit, preserving the original connectivity metric unchanged."""

import argparse
import bisect
import json
import math
import re
import statistics
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from fil.research.accepted_corpus import write_bundle
from fil.research.acquisition import digest
from fil.research.connectivity import correlation
from fil.research.integrity_review import verify_artifact
from fil.research.pilot import encode

VERSION = "fil-connectivity-falsification-1"
PARENT_SHA = "d5a0e833f3eafdf2c3cf45a1b85702d9c59515a1"
PARENT_MANIFEST = "ec608f18aa8131d35ea493fef5ef0b8c08426886d7f33246eb463852f9991141"
PROTOCOL = Path("docs/research/CONNECTIVITY_FALSIFICATION_PROTOCOL.md")
PROTOCOL_SHA256 = "69d8fbcee14a6d60e0fc4bb1984375fdc648df189fdda9981b5ee8ff17ce65c2"
GRIDS = {
    "6x4": (6, 4, 0),
    "3x2": (3, 2, 0),
    "shift5": (6, 4, 5),
    "shift10": (6, 4, 10),
    "shift_minus5": (6, 4, -5),
}
LEGS = {"original": (0, 3), "incoming": (0, 1), "b_relocation_proxy": (1, 2), "b_outgoing": (2, 3)}
VARIANTS = ("original", "receipt_required", "no_carry", "no_intervening", "permit_complete_dribble")


def valid(point: object) -> bool:
    """Only finite original two-dimensional 120×80 event coordinates."""
    return (
        isinstance(point, list)
        and len(point) == 2
        and all(
            type(x) in (int, float) and math.isfinite(x) and 0 <= x <= limit
            for x, limit in zip(point, (120, 80), strict=True)
        )
    )


def cell(point: object, nx: int = 6, ny: int = 4, offset: int = 0) -> tuple | None:
    """Shift internal boundaries; edge cells change width, without wrapping."""
    if not valid(point):
        return None
    return tuple(
        bisect.bisect_right([k * limit / count + offset for k in range(1, count)], x)
        for x, limit, count in zip(point, (120, 80), (nx, ny), strict=True)
    )


def changed(a: object, b: object, grid: tuple) -> bool | None:
    ca, cb = cell(a, *grid), cell(b, *grid)
    return None if ca is None or cb is None else ca != cb


def distance(a: object, b: object) -> float | None:
    return math.dist(a, b) if valid(a) and valid(b) else None


def analyze_match(parent: dict, raw: list[dict]) -> dict:
    """Audit original candidate pairs and component geometry."""
    by = {e["id"]: (n, e) for n, e in enumerate(raw)}
    if len(by) != len(raw) or any(
        a["index"] >= b["index"] for a, b in zip(raw, raw[1:], strict=False)
    ):
        raise ValueError("Original identity/order failure")
    players = {p["player_id"]: p for p in parent["players"]}
    groups = defaultdict(list)
    for p in parent["passes"]:
        if (
            not p["exclusion_reasons"]
            and p["sequence_membership_eligible"]
            and p["team_id"] == by[p["event_id"]][1]["possession_team"]["id"]
        ):
            groups[p["possession_id"]].append(p)
    candidates, rows = [], []
    for pid, passes in groups.items():
        for first, second in zip(passes, passes[1:], strict=False):
            ia, a = by[first["event_id"]]
            ib, b = by[second["event_id"]]
            actor = second["actor_id"]
            middle = raw[ia + 1 : ib]
            shared = first["recipient_id"] == actor

            def allowed(e, dribble=False, team=first["team_id"], player=actor):
                if e["team"]["id"] != team or e.get("player", {}).get("id") != player:
                    return False
                kind = e["type"]["name"]
                return (
                    kind == "Carry"
                    or kind == "Ball Receipt*"
                    and "outcome" not in e.get("ball_receipt", {})
                    or dribble
                    and kind == "Dribble"
                    and e.get("dribble", {}).get("outcome", {}).get("name") == "Complete"
                )

            original = shared and all(allowed(e) for e in middle)
            receipt = [
                e
                for e in middle
                if e["type"]["name"] == "Ball Receipt*"
                and e.get("player", {}).get("id") == actor
                and e["team"]["id"] == first["team_id"]
                and "outcome" not in e.get("ball_receipt", {})
            ]
            eligibility = dict(
                original=original,
                receipt_required=original and len(receipt) == 1,
                no_carry=original and not any(e["type"]["name"] == "Carry" for e in middle),
                no_intervening=original and not middle,
                permit_complete_dribble=shared and all(allowed(e, True) for e in middle),
            )
            cid = a["id"] + "/" + b["id"]
            candidates.append(
                dict(
                    chain_id=cid,
                    match_id=parent["match_id"],
                    possession_id=pid,
                    pass_event_ids=[a["id"], b["id"]],
                    intervening_event_ids=[e["id"] for e in middle],
                    eligibility=eligibility,
                    recipient_matches=shared,
                    nonpermitted_original_event_ids=[e["id"] for e in middle if not allowed(e)],
                )
            )
            if not eligibility["permit_complete_dribble"]:
                continue
            points = [
                a.get("location"),
                a.get("pass", {}).get("end_location"),
                b.get("location"),
                b.get("pass", {}).get("end_location"),
            ]
            nonreturn = first["actor_id"] != second["recipient_id"]
            outcomes = {}
            for name, (start, end) in LEGS.items():
                outcomes[name] = {
                    grid: (
                        None
                        if (v := changed(points[start], points[end], spec)) is None
                        else nonreturn and v
                    )
                    for grid, spec in GRIDS.items()
                }
            observed_receipt = receipt[0] if len(receipt) == 1 else None
            rp = observed_receipt.get("location") if observed_receipt else None
            rr = changed(rp, points[2], GRIDS["6x4"])
            position = next(
                (
                    p
                    for p in reversed(players[actor]["native_position_evidence"])
                    if p["index"] <= a["index"]
                ),
                None,
            )
            role = position["position"]["id"] if position and position.get("position") else None
            rows.append(
                dict(
                    chain_id=cid,
                    match_id=parent["match_id"],
                    team_id=first["team_id"],
                    player_id=actor,
                    player_ids=[first["actor_id"], actor, second["recipient_id"]],
                    possession_id=pid,
                    period=a["period"],
                    score_state=first["score_state"],
                    prior_goal_event_ids=first["prior_goal_event_ids"],
                    pass_event_ids=[a["id"], b["id"]],
                    provider_indices=[a["index"], b["index"]],
                    intervening_event_ids=[e["id"] for e in middle],
                    eligibility=eligibility,
                    source_manifest_sha256=first["source_manifest_sha256"],
                    nonreturn=nonreturn,
                    points=points,
                    position_annotation=position,
                    position_annotation_id=role,
                    receipt_event_ids=[e["id"] for e in receipt],
                    receipt_point=rp,
                    b_observed_receipt_release=None if rr is None else nonreturn and rr,
                    receipt_proxy_separation=distance(points[1], rp),
                    outcomes=outcomes,
                    separation={
                        name: distance(points[i], points[j]) for name, (i, j) in LEGS.items()
                    },
                    vector_identity_residual=[
                        points[3][k]
                        - points[0][k]
                        - sum(points[j][k] - points[i][k] for i, j in ((0, 1), (1, 2), (2, 3)))
                        for k in (0, 1)
                    ]
                    if all(valid(p) for p in points)
                    else None,
                )
            )
    expected = {c["chain_id"]: c for c in parent["chains"]}
    actual = {r["chain_id"]: r for r in rows if r["eligibility"]["original"]}
    if expected.keys() != actual.keys():
        raise ValueError("Original chain eligibility changed")
    for cid, r in actual.items():
        c = expected[cid]
        for grid in ("6x4", "3x2"):
            v = c["zone_transition"][grid]
            if r["outcomes"]["original"][grid] != (None if v is None else c["nonreturn"] and v):
                raise ValueError("Original metric changed")
    return dict(match_id=parent["match_id"], candidates=candidates, rows=rows)


def distribution(values: list) -> dict:
    """Linear-interpolated inclusive quartiles, with all missing support retained."""
    known = sorted(v for v in values if v is not None)

    def quantile(p):
        x = (len(known) - 1) * p
        i = int(x)
        return known[i] + (known[min(i + 1, len(known) - 1)] - known[i]) * (x - i)

    return dict(
        known=len(known),
        missing=len(values) - len(known),
        min=known[0] if known else None,
        q25=quantile(0.25) if known else None,
        median=statistics.median(known) if known else None,
        q75=quantile(0.75) if known else None,
        max=known[-1] if known else None,
    )


def partitions(row: dict) -> dict:
    """Retrospective context keys; position is explicitly last observed annotation."""
    start = cell(row["points"][0])
    end = cell(row["points"][3])
    tm = [row["match_id"], row["team_id"]]
    context = tm + [row["period"], row["score_state"]]
    return dict(
        team_match=tm,
        team_period_score=context,
        start_zone=[start],
        endpoint_pair=[start, end],
        endpoint_pair_nonreturn=[start, end, row["nonreturn"]],
        team_possession=tm + [row["possession_id"]],
        team_period_score_start=context + [start],
        team_period_score_start_position=context + [start, row["position_annotation_id"]],
    )


def strata(rows: list[dict]) -> dict:
    """Exact observed binary within-stratum variation; no predictive/context fitting."""
    output = defaultdict(dict)
    for r in rows:
        y = r["outcomes"]["original"]["6x4"]
        if y is None:
            continue
        for name, parts in partitions(r).items():
            key = json.dumps(parts, separators=(",", ":"))
            group = output[name].setdefault(key, dict(n=0, k=0, players={}, chain_ids=[]))
            group["n"] += 1
            group["k"] += y
            group["chain_ids"].append(r["chain_id"])
            player = group["players"].setdefault(str(r["player_id"]), dict(n=0, k=0))
            player["n"] += 1
            player["k"] += y
    return dict(output)


def summarize(audits: list[dict], parent: list[dict]) -> dict:
    all_rows = [r for a in audits for r in a["rows"]]
    rows = [r for r in all_rows if r["eligibility"]["original"]]
    base = [r for r in rows if r["outcomes"]["original"]["6x4"] is not None]
    by_player = defaultdict(list)
    for r in rows:
        by_player[r["match_id"], r["player_id"]].append(r)
    decomposition = []
    for m in parent:
        for p in m["players"]:
            group = by_player[m["match_id"], p["player_id"]]
            known = [r for r in group if r["outcomes"]["original"]["6x4"] is not None]
            n, nonreturn = len(known), sum(r["nonreturn"] for r in known)
            k = sum(r["outcomes"]["original"]["6x4"] for r in known)
            if k != p["cross_zone_nonreturn"] or n != p["known_geometry_chains"]:
                raise ValueError("Opportunity reconciliation failure")
            decomposition.append(
                dict(
                    match_id=m["match_id"],
                    player_id=p["player_id"],
                    team_id=p["team_id"],
                    N=n,
                    M=nonreturn,
                    K=k,
                    nonreturn_fraction=nonreturn / n if n else None,
                    conditional_fraction=k / n if n else None,
                    cross_fraction_among_nonreturns=k / nonreturn if nonreturn else None,
                    completed_passes=p["completed_passes"],
                    received_passes=p["received_passes"],
                    actor_records=p["actor_records"],
                    in_degree=p["in_degree"],
                    out_degree=p["out_degree"],
                    possession_participation=p["possession_participation"],
                    team_completed_pass_opportunities=p["team_completed_pass_opportunities"],
                    team_eligible_possessions=p["team_eligible_possessions"],
                    chain_ids=[r["chain_id"] for r in group],
                    official_minutes=None,
                    ability_estimate=None,
                )
            )
    active = [d for d in decomposition if d["actor_records"] or d["received_passes"]]
    fractions = [d for d in active if d["conditional_fraction"] is not None]
    features = (
        "completed_passes",
        "received_passes",
        "N",
        "M",
        "in_degree",
        "out_degree",
        "possession_participation",
        "team_completed_pass_opportunities",
        "team_eligible_possessions",
    )
    redundancy = {
        name: dict(
            count_correlation=correlation([d["K"] for d in active], [d[name] for d in active]),
            fraction_correlation=correlation(
                [d["conditional_fraction"] for d in fractions], [d[name] for d in fractions]
            ),
        )
        for name in features
    }
    tabs = {}
    for definition in ("incoming", "b_relocation_proxy", "b_outgoing", "observed_receipt"):
        pairs = [
            (
                r["outcomes"]["original"]["6x4"],
                r["b_observed_receipt_release"]
                if definition == "observed_receipt"
                else r["outcomes"][definition]["6x4"],
            )
            for r in rows
        ]
        tabs[definition] = dict(
            Counter("unknown" if a is None or b is None else f"{int(a)}:{int(b)}" for a, b in pairs)
        )
    variants = {}
    for variant in VARIANTS:
        group = [r for r in all_rows if r["eligibility"][variant]]
        variants[variant] = dict(
            eligible=len(group),
            known=sum(r["outcomes"]["original"]["6x4"] is not None for r in group),
            cross_zone=sum(r["outcomes"]["original"]["6x4"] is True for r in group),
            chain_ids=[r["chain_id"] for r in group],
        )
    bins = Counter(
        "0"
        if not d["N"]
        else "1-4"
        if d["N"] < 5
        else "5-9"
        if d["N"] < 10
        else "10-19"
        if d["N"] < 20
        else ">=20"
        for d in active
    )
    tie_audits = {}
    for label, fields in (
        ("pass_volume", ("completed_passes", "received_passes")),
        ("pass_volume_and_chains", ("completed_passes", "received_passes", "N")),
    ):
        ties = defaultdict(list)
        for d in active:
            ties[tuple(d[f] for f in ("match_id", "team_id", *fields))].append(d)
        pairs = [
            dict(
                match_id=a["match_id"],
                team_id=a["team_id"],
                player_ids=[a["player_id"], b["player_id"]],
                opportunities=[a["N"], b["N"]],
                counts=[a["K"], b["K"]],
            )
            for group in ties.values()
            for i, a in enumerate(group)
            for b in group[i + 1 :]
        ]
        tie_audits[label] = dict(
            pairs=len(pairs),
            differing_counts=sum(a["counts"][0] != a["counts"][1] for a in pairs),
            evidence=pairs,
        )
    sparse = {}
    for label in ("0", "1-4", "5-9", "10-19", ">=20"):
        sample = [
            d["conditional_fraction"]
            for d in active
            if (
                "0"
                if not d["N"]
                else "1-4"
                if d["N"] < 5
                else "5-9"
                if d["N"] < 10
                else "10-19"
                if d["N"] < 20
                else ">=20"
            )
            == label
        ]
        sparse[label] = distribution(sample)
    groups = strata(rows)
    n, k = len(base), sum(r["outcomes"]["original"]["6x4"] for r in base)
    total_sse = k * (n - k) / n if n else None
    partition_summary = {}
    for name, values in groups.items():
        sse = math.fsum(g["k"] * (g["n"] - g["k"]) / g["n"] for g in values.values())
        multi = [g for g in values.values() if len(g["players"]) > 1]
        supported = [
            g for g in values.values() if sum(p["n"] >= 5 for p in g["players"].values()) >= 2
        ]
        partition_summary[name] = dict(
            strata=len(values),
            within_stratum_sse=sse,
            fraction_of_unstratified_sse=sse / total_sse if total_sse else None,
            opportunities_in_multi_player_strata=sum(g["n"] for g in multi),
            strata_with_two_players_at_least5=len(supported),
            opportunities_in_supported_strata=sum(g["n"] for g in supported),
            player_opportunities_at_least5_in_supported_strata=sum(
                p["n"] for g in supported for p in g["players"].values() if p["n"] >= 5
            ),
        )
    grids = {
        name: dict(
            cross_zone=sum(r["outcomes"]["original"][name] is True for r in rows),
            disagreement_with_primary=sum(
                r["outcomes"]["original"][name] != r["outcomes"]["original"]["6x4"] for r in rows
            ),
            missing=sum(r["outcomes"]["original"][name] is None for r in rows),
        )
        for name in GRIDS
    }
    mechanical = sum(
        r["outcomes"]["original"]["6x4"] is True and r["outcomes"]["original"]["3x2"] is False
        for r in rows
    )
    invalid_nested = sum(
        r["outcomes"]["original"]["6x4"] is False and r["outcomes"]["original"]["3x2"] is True
        for r in rows
    )
    if invalid_nested:
        raise ValueError("Nested-grid identity failure")
    filters = dict(
        original_without_outgoing=lambda r: r["outcomes"]["original"]["6x4"] is True
        and r["outcomes"]["b_outgoing"]["6x4"] is False,
        outgoing_without_original=lambda r: r["outcomes"]["original"]["6x4"] is False
        and r["outcomes"]["b_outgoing"]["6x4"] is True,
        original_without_relocation=lambda r: r["outcomes"]["original"]["6x4"] is True
        and r["outcomes"]["b_relocation_proxy"]["6x4"] is False,
        relocation_without_original=lambda r: r["outcomes"]["original"]["6x4"] is False
        and r["outcomes"]["b_relocation_proxy"]["6x4"] is True,
        missing_observed_receipt=lambda r: r["b_observed_receipt_release"] is None,
        tiny_boundary_crossing=lambda r: r["outcomes"]["original"]["6x4"] is True
        and r["separation"]["original"] is not None
        and r["separation"]["original"] < 1,
        long_within_cell=lambda r: r["nonreturn"]
        and r["outcomes"]["original"]["6x4"] is False
        and r["separation"]["original"] is not None
        and r["separation"]["original"] >= 20,
        fine_not_coarse=lambda r: r["outcomes"]["original"]["6x4"] is True
        and r["outcomes"]["original"]["3x2"] is False,
    )
    retrieval = {name: next((r for r in rows if check(r)), None) for name, check in filters.items()}
    retrieval["relaxed_only"] = next(
        (r for r in all_rows if not r["eligibility"]["original"]), None
    )
    return dict(
        version=VERSION,
        study_classification="exploratory",
        parent_sha=PARENT_SHA,
        matches=len(audits),
        source_events=sum(m["source_event_count"] for m in parent),
        decomposition=decomposition,
        redundancy=redundancy,
        correlation_support=dict(count_rows=len(active), fraction_rows=len(fractions)),
        opportunity_bins=dict(bins),
        sparse_fraction_distributions=sparse,
        within_team_match_baseline_ties=tie_audits,
        definition_cross_tabs=tabs,
        grids=grids,
        coarsening=dict(
            mechanical_reclassifications=mechanical,
            invalid_nested=invalid_nested,
            behavior_changed=False,
        ),
        variants=variants,
        partition_summary=partition_summary,
        partitions=groups,
        unstratified_sse=total_sse,
        continuous={name: distribution([r["separation"][name] for r in rows]) for name in LEGS},
        continuous_thresholds={
            str(t): sum(
                r["nonreturn"]
                and r["separation"]["original"] is not None
                and r["separation"]["original"] >= t
                for r in rows
            )
            for t in (20, 40)
        },
        receipt_proxy_separation=distribution([r["receipt_proxy_separation"] for r in rows]),
        missing_position_annotations=sum(r["position_annotation_id"] is None for r in rows),
        original_excluded_memberships=sum(len(m["excluded_memberships"]) for m in parent),
        original_pass_exclusion_flags=dict(
            Counter(
                reason for m in parent for p in m["passes"] for reason in p["exclusion_reasons"]
            )
        ),
        retrieval=retrieval,
        scientific_ability_verdict="INCONCLUSIVE",
        population_interval=None,
        independent_confirmation=False,
        recommendation="PENDING_SCIENTIFIC_REVIEW",
        recommendation_scope="descriptor presentation, not replacement score",
    )


def report(summary: dict) -> str:
    """Local-only audit report, including evidence and original IDs; never commit/publish."""
    lines = [
        "# LOCAL ONLY — Connectivity falsification audit v1",
        "",
        "Recommendation requires scientific review of these observations; no automatic promotion.",
        "Use 'observed cross-zone non-return pass chains' with opportunity counts and components.",
        "Attacking Connectivity remains INCONCLUSIVE as a distinct player ability.",
        "",
        "All matches are development-exposed. No fitting, causal attribution or ability score.",
        "Counts decompose exactly as N × nonreturn fraction × cross fraction among nonreturns.",
        "Undefined fractions stay null; team opportunities are not playing availability.",
        "",
    ]
    for name in (
        "correlation_support",
        "opportunity_bins",
        "sparse_fraction_distributions",
        "redundancy",
        "definition_cross_tabs",
        "grids",
        "coarsening",
        "continuous",
        "continuous_thresholds",
        "receipt_proxy_separation",
        "variants",
        "partition_summary",
    ):
        value = summary[name]
        if name == "variants":
            value = {k: {n: v for n, v in d.items() if n != "chain_ids"} for k, d in value.items()}
        lines += [f"## {name}", "", "```json", encode(value).rstrip(), "```", ""]
    lines += [
        "SSE tables are retrospective tallies, not fitted explanatory or predictive models.",
        (
            "Endpoint pair plus nonreturn determines the metric by definition; zero "
            "SSE is tautological."
        ),
        "All nested-grid count reduction recodes identical records mechanically.",
        "Native units are not metres. No coordinate is flipped or replaced.",
        "The p1→p2 relocation proxy is not a certified physical receive/run.",
        "Position context is last observed annotation, not an inferred stable role.",
        "Chain overlap and repeated teams/players prevent iid event inference.",
        "",
        "## Missingness and exclusions",
        "",
        "```json",
        encode(
            {
                k: summary[k]
                for k in (
                    "source_events",
                    "original_excluded_memberships",
                    "original_pass_exclusion_flags",
                    "missing_position_annotations",
                )
            }
        ).rstrip(),
        "```",
        "",
        "## Positive evidence and counterexamples (earliest provider order)",
    ]
    for name, value in summary["retrieval"].items():
        lines += ["", f"### {name}", "", "```json", encode(value).rstrip(), "```"]
    lines += [
        "",
        "## Recommendation and rejection criteria",
        "",
        (
            "KEEP source-ordered evidence retrieval: counts alone cannot recover "
            "exact action sequences."
        ),
        (
            "REVISE aggregate presentation: distinguish opportunities, endpoint "
            "geometry and B's components."
        ),
        "Do not replace this with a more attractive scalar or upgrade the proposed ability.",
        "RETIRE the distinct-ability claim if independent, adequately supported context/volume",
        (
            "comparisons and blinded retrieval tests fail to add meaningful evidence "
            "over a simple ledger."
        ),
        (
            "The current corpus cannot independently test that claim, and does not "
            "justify advancing it."
        ),
        "",
        "## New independent evidence required",
        "",
        (
            "Untouched authorized cross-league/season matches; comparable "
            "roles/opportunities or certified"
        ),
        (
            "exposure; predeclared clustered stability/context tests; independent "
            "human sequence relevance"
        ),
        "annotations; blinded ledger-baseline utility study with minimum meaningful effects.",
        (
            "Resolve source/model-specific fitting rights before any new "
            "predictive/hierarchical/latent model."
        ),
        (
            "See summary.json decomposition/partitions and evidence.json for complete "
            "event-level support."
        ),
        "",
    ]
    return "\n".join(lines)


def run(parent: Path, output: Path, implementation: str) -> Path:
    """Verify exact parent and immutable sources; write a separate local bundle."""
    if digest(PROTOCOL.read_bytes()) != PROTOCOL_SHA256:
        raise ValueError("Frozen falsification protocol changed")
    if not re.fullmatch(r"[0-9a-f]{40}", implementation):
        raise ValueError("Full implementation SHA required")
    if digest((parent / "manifest.json").read_bytes()) != PARENT_MANIFEST:
        raise ValueError("Exact PR19 delivered evidence required")
    manifest = verify_artifact(parent)
    protected = dict(manifest["protected_inputs"])
    protected.update({str(p.resolve()): digest(p.read_bytes()) for p in parent.iterdir()})
    if any(digest(Path(p).read_bytes()) != sha for p, sha in protected.items()):
        raise ValueError("Protected parent/source changed")
    if any(output.resolve().is_relative_to(Path(p).parent.resolve()) for p in protected):
        raise ValueError("Output overlaps protected input")
    parents = json.loads((parent / "evidence.json").read_bytes())
    sources = json.loads((parent / "source-inputs.json").read_bytes())
    audits = []
    for m, source in zip(parents, sources, strict=True):
        if m["match_id"] != source["match_id"]:
            raise ValueError("Parent match identity mismatch")
        audits.append(analyze_match(m, json.loads(Path(source["events"]).read_bytes())))
    summary = summarize(audits, parents)
    target = output / VERSION / implementation
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".falsification-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        (stage / "evidence.json").write_text(encode(audits))
        (stage / "summary.json").write_text(encode(summary))
        (stage / "audit.md").write_text(report(summary))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=implementation,
                    parent_sha=PARENT_SHA,
                    parent_bundle=str(parent.resolve()),
                    parent_manifest_sha256=PARENT_MANIFEST,
                    protocol_sha256=digest(PROTOCOL.read_bytes()),
                    protected_inputs=protected,
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                    rights=(
                        "local noncommercial; no redistribution/external AI/"
                        "new model fitting/deployment"
                    ),
                )
            )
        )
        if any(digest(Path(p).read_bytes()) != sha for p, sha in protected.items()):
            raise ValueError("Protected source changed during audit")
        write_bundle(stage, target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("data/interim/connectivity-falsification")
    )
    parser.add_argument("--pipeline-revision", required=True)
    args = parser.parse_args()
    print(encode(dict(bundle=str(run(args.parent, args.output, args.pipeline_revision).resolve()))))


if __name__ == "__main__":
    main()
