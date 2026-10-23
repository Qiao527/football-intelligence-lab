"""Local exploratory passing connections; no ability scores or causal network claims."""

import argparse
import hashlib
import json
import math
import re
import statistics
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from fil.research.accepted_corpus import write_bundle
from fil.research.acquisition import REVISION, digest
from fil.research.attribute_registry import load
from fil.research.eligibility import ordered_score
from fil.research.integrity_review import verify_artifact
from fil.research.pilot import encode
from fil.research.prospective import components

VERSION = "fil-attacking-connectivity-1"
PROTOCOL = Path("docs/research/CONNECTIVITY_PROTOCOL.md")


def zone(point: object, nx: int = 6, ny: int = 4) -> str | None:
    """Native 120×80 cells, inclusive outer boundary; missing/invalid never zero-filled."""
    if not isinstance(point, list) or len(point) != 2:
        return None
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in point):
        return None
    x, y = point
    if not (0 <= x <= 120 and 0 <= y <= 80):
        return None
    return f"{min(int(x * nx / 120), nx - 1)}:{min(int(y * ny / 80), ny - 1)}"


def completed(event: dict) -> bool:
    """StatsBomb absent outcome means completed; explicit null remains unknown."""
    return event["type"]["name"] == "Pass" and "outcome" not in event.get("pass", {})


def extract(raw: list[dict], roster: list[dict], metadata: dict, source_sha: str) -> dict:
    """Extract deterministic evidence after source verification, retaining exclusions."""
    if not raw or len({e["id"] for e in raw}) != len(raw):
        raise ValueError("Unique nonempty original source required")
    if any(a["index"] >= b["index"] for a, b in zip(raw, raw[1:], strict=False)):
        raise ValueError("Increasing provider order required")
    mid = metadata["match_id"]
    teams = [metadata[k][k + "_id"] for k in ("home_team", "away_team")]
    if {t["team_id"] for t in roster} != set(teams):
        raise ValueError("Roster/team identity mismatch")
    players, records = {}, {}
    for t in roster:
        for p in t["lineup"]:
            pid = p["player_id"]
            if pid in players:
                raise ValueError("Duplicate roster identity")
            players[pid] = t["team_id"]
            records[pid] = dict(
                match_id=mid,
                player_id=pid,
                team_id=t["team_id"],
                opponent_id=teams[1 - teams.index(t["team_id"])],
                source_manifest_sha256=source_sha,
                original_actor_event_ids=[],
                completed_pass_ids=[],
                received_pass_ids=[],
                possession_ids=[],
                native_position_evidence=[],
                substitution_evidence=[],
                roster_positions=p.get("positions"),
                roster_name=p["player_name"],
                zone_context_counts={},
                chain_ids=[],
            )
    decisions = ordered_score(raw, metadata)["decisions"]
    groups = defaultdict(list)
    for i, e in enumerate(raw):
        if e.get("possession") is not None:
            groups[e["possession"]].append(i)
        actor = e.get("player", {}).get("id")
        if actor is not None and e["period"] < 5:
            if players.get(actor) != e["team"]["id"]:
                raise ValueError("Actor/roster mismatch")
            records[actor]["original_actor_event_ids"].append(e["id"])
        for p in (e.get("tactics") or {}).get("lineup", []):
            pid = p["player"]["id"]
            if players.get(pid) != e["team"]["id"]:
                raise ValueError("Native position identity mismatch")
            records[pid]["native_position_evidence"].append(
                dict(event_id=e["id"], index=e["index"], position=p.get("position"))
            )
        if e["type"]["name"] == "Substitution":
            for pid in (actor, e["substitution"]["replacement"]["id"]):
                if players.get(pid) != e["team"]["id"]:
                    raise ValueError("Replacement identity mismatch")
                records[pid]["substitution_evidence"].append(e["id"])
    valid_groups, exclusions = {}, []
    for pid, indices in groups.items():
        events = [raw[i] for i in indices]
        reasons = []
        if len({e["period"] for e in events}) != 1 or events[0]["period"] not in (1, 2, 3, 4):
            reasons.append("unsupported_or_cross_period")
        owners = {e.get("possession_team", {}).get("id") for e in events}
        if len(owners) != 1 or not owners <= set(teams):
            reasons.append("ambiguous_owner")
        if indices != list(range(indices[0], indices[-1] + 1)):
            reasons.append("noncontiguous")
        if reasons:
            exclusions.append(
                dict(possession_id=pid, event_ids=[e["id"] for e in events], reasons=reasons)
            )
        else:
            valid_groups[pid] = events
    passes = []
    eligible = {}
    for i, e in enumerate(raw):
        if e["type"]["name"] != "Pass":
            continue
        p = e.get("pass", {})
        actor, recipient = e.get("player", {}).get("id"), p.get("recipient", {}).get("id")
        reasons = []
        if e["period"] not in (1, 2, 3, 4):
            reasons.append("shootout_or_unsupported_period")
        if not completed(e):
            reasons.append("unknown_outcome" if p.get("outcome", 1) is None else "not_completed")
        if actor is None or recipient is None:
            reasons.append("missing_identity")
        elif players.get(actor) != e["team"]["id"] or players.get(recipient) != e["team"]["id"]:
            raise ValueError("Pass/recipient roster mismatch")
        elif actor == recipient:
            reasons.append("self_connection")
        prior = [
            d
            for d in decisions
            if d["domain"] == "match_play" and d["scored"] and d["provider_index"] < e["index"]
        ]
        own = sum(d["beneficiary_team_id"] == e["team"]["id"] for d in prior)
        other = len(prior) - own
        state = "level" if own == other else "leading" if own > other else "trailing"
        row = dict(
            match_id=mid,
            event_id=e["id"],
            provider_index=e["index"],
            period=e["period"],
            timestamp=e["timestamp"],
            team_id=e["team"]["id"],
            actor_id=actor,
            recipient_id=recipient,
            possession_id=e.get("possession"),
            start=e.get("location"),
            end=p.get("end_location"),
            start_zone=zone(e.get("location")),
            end_zone=zone(p.get("end_location")),
            score_state=state,
            prior_goal_event_ids=[j for d in prior for j in d["source_event_ids"]],
            source_manifest_sha256=source_sha,
            exclusion_reasons=reasons,
            sequence_membership_eligible=e.get("possession") in valid_groups,
        )
        passes.append(row)
        if not reasons:
            eligible[e["id"]] = (i, row)
            records[actor]["completed_pass_ids"].append(e["id"])
            records[recipient]["received_pass_ids"].append(e["id"])
            context = f"{row['start_zone']}|{e['period']}|{state}"
            counts = records[actor]["zone_context_counts"]
            counts[context] = counts.get(context, 0) + 1
    # Participation is original actor OR verified completed-pass recipient in eligible membership.
    for pid, events in valid_groups.items():
        owner = events[0]["possession_team"]["id"]
        involved = {e.get("player", {}).get("id") for e in events if e["team"]["id"] == owner}
        involved |= {
            eligible[e["id"]][1]["recipient_id"]
            for e in events
            if e["id"] in eligible and e["team"]["id"] == owner
        }
        for player in involved - {None}:
            records[player]["possession_ids"].append(pid)
    chains, rejected = [], Counter()
    for pid, events in valid_groups.items():
        owner = events[0]["possession_team"]["id"]
        ps = [e for e in events if e["id"] in eligible and e["team"]["id"] == owner]
        for first, second in zip(ps, ps[1:], strict=False):
            fi, a = eligible[first["id"]]
            si, b = eligible[second["id"]]
            if a["recipient_id"] != b["actor_id"]:
                rejected["recipient_not_next_passer"] += 1
                continue
            middle = raw[fi + 1 : si]
            if any(
                e["team"]["id"] != owner
                or e.get("player", {}).get("id") != b["actor_id"]
                or e["type"]["name"] not in ("Carry", "Ball Receipt*")
                or (e["type"]["name"] == "Ball Receipt*" and "outcome" in e.get("ball_receipt", {}))
                for e in middle
            ):
                rejected["intervening_nonpermitted_record"] += 1
                continue
            nonreturn = a["actor_id"] != b["recipient_id"]
            transitions = {}
            for name, nx, ny in (("6x4", 6, 4), ("3x2", 3, 2)):
                start, end = zone(a["start"], nx, ny), zone(b["end"], nx, ny)
                transitions[name] = None if start is None or end is None else start != end
            later = [
                e["id"]
                for e in events
                if e["index"] > second["index"]
                and e["team"]["id"] == owner
                and e["type"]["name"] == "Shot"
            ]
            chain = dict(
                match_id=mid,
                possession_id=pid,
                period=first["period"],
                team_id=owner,
                chain_id=first["id"] + "/" + second["id"],
                pass_event_ids=[first["id"], second["id"]],
                intervening_event_ids=[e["id"] for e in middle],
                player_ids=[a["actor_id"], b["actor_id"], b["recipient_id"]],
                nonreturn=nonreturn,
                zone_transition=transitions,
                first_start_zone=a["start_zone"],
                score_state=a["score_state"],
                later_recorded_shot_ids=later,
                source_manifest_sha256=source_sha,
                alternative_observed_chain_ids=[],
            )
            chains.append(chain)
            records[b["actor_id"]]["chain_ids"].append(chain["chain_id"])
    paths = defaultdict(list)
    for c in chains:
        paths[c["possession_id"], c["player_ids"][0], c["player_ids"][2]].append(c)
    for group in paths.values():
        for c in group:
            c["alternative_observed_chain_ids"] = [
                d["chain_id"] for d in group if c["player_ids"][1] != d["player_ids"][1]
            ]
    by_pass = {r["event_id"]: r for r in passes}
    by_chain = {r["chain_id"]: r for r in chains}
    for r in records.values():
        cs = [by_chain[i] for i in r["chain_ids"]]
        r["completed_passes"] = len(r["completed_pass_ids"])
        r["received_passes"] = len(r["received_pass_ids"])
        r["out_degree"] = len({by_pass[i]["recipient_id"] for i in r["completed_pass_ids"]})
        r["in_degree"] = len({by_pass[i]["actor_id"] for i in r["received_pass_ids"]})
        r["actor_records"] = len(r["original_actor_event_ids"])
        r["possession_participation"] = len(r["possession_ids"])
        r["team_completed_pass_opportunities"] = sum(
            len(v["completed_pass_ids"]) for v in records.values() if v["team_id"] == r["team_id"]
        )
        r["team_eligible_possessions"] = sum(
            es[0]["possession_team"]["id"] == r["team_id"] for es in valid_groups.values()
        )
        r["observed_chains"] = len(cs)
        r["known_geometry_chains"] = sum(c["zone_transition"]["6x4"] is not None for c in cs)
        r["cross_zone_nonreturn"] = sum(
            c["nonreturn"] and c["zone_transition"]["6x4"] is True for c in cs
        )
        r["coarse_cross_zone_nonreturn"] = sum(
            c["nonreturn"] and c["zone_transition"]["3x2"] is True for c in cs
        )
        r["conditional_chain_fraction"] = (
            r["cross_zone_nonreturn"] / r["known_geometry_chains"]
            if r["known_geometry_chains"]
            else None
        )
        strata = defaultdict(lambda: dict(known_chains=0, cross_zone_nonreturn=0))
        for c in cs:
            key = f"{c['first_start_zone']}|{c['period']}|{c['score_state']}"
            strata[key]["known_chains"] += c["zone_transition"]["6x4"] is not None
            strata[key]["cross_zone_nonreturn"] += (
                c["nonreturn"] and c["zone_transition"]["6x4"] is True
            )
        r["chain_context_counts"] = dict(strata)
        r["official_minutes"] = None
        r["ability_estimate"] = None
    return dict(
        match_id=mid,
        source_event_count=len(raw),
        passes=passes,
        chains=chains,
        players=list(records.values()),
        excluded_memberships=exclusions,
        rejected_adjacent_pairs=dict(rejected),
        team_ids=teams,
        player_ids=sorted(players),
        source="statsbomb_open_data",
    )


def correlation(a: list[float], b: list[float]) -> float | None:
    """Descriptive Pearson redundancy check; no inferential p-value."""
    if len(a) < 2 or len(a) != len(b) or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    return statistics.correlation(a, b)


def summarize(matches: list[dict], metadata: list[dict]) -> dict:
    """Outcome-blind player illustrations and dependency-aware descriptive diagnostics."""
    rows = [r for m in matches for r in m["players"]]
    support = defaultdict(list)
    for r in rows:
        if r["completed_passes"] >= 20:
            support[r["player_id"]].append(r)
    eligible = {p: rs for p, rs in support.items() if len(rs) >= 3}
    selected = sorted(
        eligible, key=lambda p: hashlib.sha256(f"statsbomb:{p}".encode()).hexdigest()
    )[:6]
    days = {m["match_id"]: m["match_date"] for m in metadata}
    all_by_player = defaultdict(list)
    for r in rows:
        all_by_player[r["player_id"]].append(r)
    stability = []
    for p in sorted(eligible):
        rs = sorted(eligible[p], key=lambda r: (days[r["match_id"]], r["match_id"]))
        observed = [
            r["conditional_chain_fraction"]
            for r in rs
            if r["conditional_chain_fraction"] is not None
        ]
        halves = []
        for group in (rs[::2], rs[1::2]):
            n = sum(r["known_geometry_chains"] for r in group)
            s = sum(r["cross_zone_nonreturn"] for r in group)
            halves.append(dict(denominator=n, numerator=s, fraction=s / n if n else None))
        stability.append(
            dict(
                player_id=p,
                supported_matches=len(rs),
                within_player_range=max(observed) - min(observed) if observed else None,
                chronological_splits=halves,
                absolute_split_difference=abs(halves[0]["fraction"] - halves[1]["fraction"])
                if all(h["fraction"] is not None for h in halves)
                else None,
            )
        )
    active = [r for r in rows if r["actor_records"] or r["received_passes"]]
    correlations = {
        name: correlation([r["cross_zone_nonreturn"] for r in active], [r[name] for r in active])
        for name in (
            "completed_passes",
            "received_passes",
            "in_degree",
            "out_degree",
            "actor_records",
            "possession_participation",
        )
    }
    # Exact volume-matched comparisons are descriptive, not role adjustment or causal effects.
    paired = []
    by_volume = defaultdict(list)
    for r in active:
        by_volume[r["match_id"], r["team_id"], r["completed_passes"], r["received_passes"]].append(
            r
        )
    for group in by_volume.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if a["cross_zone_nonreturn"] != b["cross_zone_nonreturn"]:
                    paired.append(
                        dict(
                            match_id=a["match_id"],
                            team_id=a["team_id"],
                            player_ids=[a["player_id"], b["player_id"]],
                            completed_passes=a["completed_passes"],
                            received_passes=a["received_passes"],
                            descriptor_counts=[
                                a["cross_zone_nonreturn"],
                                b["cross_zone_nonreturn"],
                            ],
                            limitation="zone/role/context not matched; not incremental validity",
                        )
                    )
    overlap = []
    for i, a in enumerate(selected):
        bins_a = {
            k
            for r in all_by_player[a]
            for k, v in r["chain_context_counts"].items()
            if v["known_chains"]
        }
        for b in selected[i + 1 :]:
            bins_b = {
                k
                for r in all_by_player[b]
                for k, v in r["chain_context_counts"].items()
                if v["known_chains"]
            }
            overlap.append(
                dict(
                    player_ids=[a, b],
                    shared_native_context_bins=len(bins_a & bins_b),
                    union_native_context_bins=len(bins_a | bins_b),
                    role_and_team_comparability_certified=False,
                )
            )
    retrieval = {}
    predicates = {
        "positive_observed": lambda c: c["nonreturn"]
        and c["zone_transition"]["6x4"] is True
        and bool(c["later_recorded_shot_ids"]),
        "return_counterexample": lambda c: not c["nonreturn"],
        "no_later_recorded_shot": lambda c: c["nonreturn"]
        and c["zone_transition"]["6x4"] is True
        and not c["later_recorded_shot_ids"],
    }
    for name, predicate in predicates.items():
        retrieval[name] = next(
            (
                c
                for m in sorted(matches, key=lambda m: m["match_id"])
                for c in m["chains"]
                if predicate(c)
            ),
            None,
        )
    dependency = components(matches)
    return dict(
        version=VERSION,
        scientific_verdict="INCONCLUSIVE",
        study_classification="exploratory",
        matches=len(matches),
        teams=len({t for m in matches for t in m["team_ids"]}),
        rostered_players=len(all_by_player),
        active_player_matches=len(active),
        original_events=sum(m["source_event_count"] for m in matches),
        completed_passes=sum(r["completed_passes"] for r in rows),
        observed_chains=sum(len(m["chains"]) for m in matches),
        cross_zone_nonreturn=sum(r["cross_zone_nonreturn"] for r in rows),
        coarse_cross_zone_nonreturn=sum(r["coarse_cross_zone_nonreturn"] for r in rows),
        missing_chain_geometry=sum(r["observed_chains"] - r["known_geometry_chains"] for r in rows),
        pass_exclusions=dict(
            Counter(
                reason for m in matches for p in m["passes"] for reason in p["exclusion_reasons"]
            )
        ),
        excluded_memberships=sum(len(m["excluded_memberships"]) for m in matches),
        eligible_players=len(eligible),
        selected_player_ids=selected,
        selected_player_matches=[r for p in selected for r in all_by_player[p]],
        stability=stability,
        descriptive_volume_correlations=correlations,
        equal_pass_volume_different_descriptor_pairs=paired,
        selected_context_overlap=overlap,
        support_distribution=dict(Counter(str(len(rs)) for rs in all_by_player.values())),
        roster_position_missing=sum(r["roster_positions"] is None for r in rows),
        roster_position_empty=sum(not r["roster_positions"] for r in rows),
        native_position_missing_active=sum(not r["native_position_evidence"] for r in active),
        zero_chain_active_player_matches=sum(not r["observed_chains"] for r in active),
        retrieval=retrieval,
        dependency=dependency,
        population_interval=None,
        population_interval_reason="one connected tournament; no independence",
        ability_identified=False,
        incremental_validity="not established",
        physical_timing_certified=False,
        physical_direction_certified=False,
    )


def run(corpus: Path, output: Path, implementation: str) -> Path:
    """Verify all protected sources/quality first, then write an immutable local research bundle."""
    if not re.fullmatch(r"[0-9a-f]{40}", implementation):
        raise ValueError("Full implementation commit required")
    if output.resolve().is_relative_to(corpus.resolve()):
        raise ValueError("Output must be outside protected corpus")
    manifest = verify_artifact(corpus)
    protected = dict(manifest["protected_inputs"])
    protected[str((corpus / "manifest.json").resolve())] = digest(
        (corpus / "manifest.json").read_bytes()
    )
    for name in manifest["files"]:
        protected[str((corpus / name).resolve())] = manifest["files"][name]
    if any(digest(Path(p).read_bytes()) != sha for p, sha in protected.items()):
        raise ValueError("Protected corpus input changed")
    quality = json.loads((corpus / "quality.json").read_bytes())
    if quality["source_revision"] != REVISION or quality["match_count"] != 64:
        raise ValueError("Exact authorized World Cup corpus required")
    original = Path(quality["reference_match"]["raw"])
    metadata = json.loads((original / "data/matches/43/3.json").read_bytes())
    metas = {m["match_id"]: m for m in metadata}
    inputs = [
        (
            8658,
            original / "data/events/8658.json",
            original / "data/lineups/8658.json",
            original / "manifest.json",
            quality["reference_match"]["eligibility"],
        )
    ]
    for m in quality["matches"]:
        qdir = Path(m["quality_path"])
        q = json.loads((qdir / "quality.json").read_bytes())
        if q["status"] != "PASS" or q["material_failures"]:
            raise ValueError("Material match-quality failure")
        rawdir = Path("data/raw/statsbomb-corpus") / REVISION / str(m["match_id"])
        inputs.append(
            (
                m["match_id"],
                rawdir / f"{m['match_id']}.json.events",
                rawdir / f"{m['match_id']}.json.lineups",
                rawdir / "manifest.json",
                q["metric_eligibility"],
            )
        )
    matches, source_inputs = [], []
    for mid, events, lineups, source_manifest, eligibility in sorted(inputs):
        if any(
            eligibility[d]["support"] != "fully_supported"
            for d in ("source_identity", "event_order", "score", "native_spatial")
        ):
            raise ValueError("Connectivity domain gate not supported")
        for p in (events, lineups, source_manifest):
            if str(p.resolve()) not in protected:
                raise ValueError("Source not protected by corpus manifest")
        matches.append(
            extract(
                json.loads(events.read_bytes()),
                json.loads(lineups.read_bytes()),
                metas[mid],
                digest(source_manifest.read_bytes()),
            )
        )
        source_inputs.append(
            dict(
                match_id=mid,
                events=str(events.resolve()),
                lineups=str(lineups.resolve()),
                source_manifest_path=str(source_manifest.resolve()),
                metadata=metas[mid],
                source_manifest_sha256=digest(source_manifest.read_bytes()),
            )
        )
    registry = load()
    target = output / VERSION / implementation
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".connectivity-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        for name, value in (
            ("evidence.json", matches),
            ("summary.json", summarize(matches, metadata)),
            ("source-inputs.json", source_inputs),
            ("registry.json", registry),
        ):
            (stage / name).write_text(encode(value))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=implementation,
                    source_revision=REVISION,
                    protocol_sha256=digest(PROTOCOL.read_bytes()),
                    protected_inputs=protected,
                    registry_sha256=digest((stage / "registry.json").read_bytes()),
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                    restrictions=(
                        "local noncommercial only; no redistribution/external AI/weights/deployment"
                    ),
                )
            )
        )
        if any(digest(Path(p).read_bytes()) != sha for p, sha in protected.items()):
            raise ValueError("Protected input changed during extraction")
        write_bundle(stage, target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/interim/attribute-research"))
    parser.add_argument("--pipeline-revision", required=True)
    args = parser.parse_args()
    print(encode(dict(bundle=str(run(args.corpus, args.output, args.pipeline_revision).resolve()))))


if __name__ == "__main__":
    main()
