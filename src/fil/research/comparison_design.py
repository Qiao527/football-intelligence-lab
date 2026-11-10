"""Outcome-free crossed-support and additive-design identifiability audit; no player fitting."""

import argparse
import json
import re
import tempfile
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from fil.research.accepted_corpus import write_bundle
from fil.research.acquisition import digest
from fil.research.connectivity import zone
from fil.research.integrity_review import verify_artifact
from fil.research.pilot import encode

VERSION = "fil-player-comparison-design-1"
PARENT_MANIFEST = "0f45169769931d49167b2e6ce38ebf9b4848caef40161d0a6543673148d98f71"
PROTOCOL = Path("docs/research/COMPARISON_DESIGN_PROTOCOL.md")
PROTOCOL_SHA256 = "28cabc3c225db1b0d2a42ec6caf3788761ac9a18484fe55d63e16143d1241758"
POPULATIONS = ("pass_attempt", "verified_completed", "chain_release")
DESIGNS = ("team", "team_match", "native_context", "known_position_context")


def observations(parent: dict, source: dict, raw: list[dict]) -> list[dict]:
    """One actor-pass record, with completion/chain selection flags and original release context."""
    if len({e["id"] for e in raw}) != len(raw) or any(
        a["index"] >= b["index"] for a, b in zip(raw, raw[1:], strict=False)
    ):
        raise ValueError("Source identity/order failure")
    ps = {p["event_id"]: p for p in parent["passes"]}
    players = {p["player_id"]: p for p in parent["players"]}
    chain = {c["pass_event_ids"][1]: c for c in parent["chains"]}
    if len(chain) != len(parent["chains"]):
        raise ValueError("Ambiguous original chain release")
    teams = parent["team_ids"]
    rows = []
    for e in raw:
        if e["type"]["name"] != "Pass" or e["period"] not in (1, 2, 3, 4):
            continue
        actor = e.get("player", {}).get("id")
        if actor is None:
            continue
        p = players.get(actor)
        if p is None or p["team_id"] != e["team"]["id"]:
            raise ValueError("Actor/roster mismatch")
        original = ps[e["id"]]
        annotation = next(
            (a for a in reversed(p["native_position_evidence"]) if a["index"] <= e["index"]), None
        )
        position = annotation.get("position") if annotation else None
        payload = e.get("pass", {})
        unknown = "outcome" in payload and payload["outcome"] is None
        rows.append(
            dict(
                record_id=f"{source['match_id']}:{e['id']}",
                event_id=e["id"],
                match_id=source["match_id"],
                team_id=p["team_id"],
                opponent_id=next(t for t in teams if t != p["team_id"]),
                player_id=actor,
                provider_index=e["index"],
                period=e["period"],
                timestamp=e["timestamp"],
                score_state=original["score_state"],
                prior_goal_event_ids=original["prior_goal_event_ids"],
                native_start=e.get("location"),
                native_cell=zone(e.get("location")),
                position_annotation=annotation,
                position_id=position["id"] if position else None,
                unknown_outcome=unknown,
                outcome_key_present="outcome" in payload,
                memberships=dict(
                    pass_attempt=True,
                    verified_completed=not original["exclusion_reasons"],
                    chain_release=e["id"] in chain,
                ),
                chain_id=chain[e["id"]]["chain_id"] if e["id"] in chain else None,
                source_manifest_sha256=source["source_manifest_sha256"],
            )
        )
    return rows


def context(row: dict, design: str) -> tuple | None:
    if design not in DESIGNS:
        raise ValueError("Unknown comparison design")
    key = (row["team_id"],)
    if design != "team":
        key += (row["match_id"],)
    if design in ("native_context", "known_position_context"):
        if row["native_cell"] is None:
            return None
        key += (row["period"], row["score_state"], row["native_cell"])
    if design == "known_position_context":
        if row["position_id"] is None:
            return None
        key += (row["position_id"],)
    return key


class Union:
    """Union-find of typed player/context vertices, independent of outcome/edge frequency."""

    def __init__(self):
        self.parent = {}

    def root(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def join(self, a, b):
        ra, rb = self.root(a), self.root(b)
        if ra != rb:
            self.parent[rb] = ra


def topology(edges: list[tuple[str, str]]) -> dict:
    """Exact two-indicator rank: observed columns minus bipartite connected components."""
    union = Union()
    for a, b in edges:
        if not a.startswith("p:") or not b.startswith("c:"):
            raise ValueError("Typed nonempty player/context edges required")
        union.join(a, b)
    groups = defaultdict(list)
    for node in union.parent:
        groups[union.root(node)].append(node)
    components = sorted(sorted(nodes) for nodes in groups.values())
    components.sort(key=lambda g: g[0])
    players = [n for n in union.parent if n.startswith("p:")]
    counts = [sum(n.startswith("p:") for n in group) for group in components]
    within = sum(n * (n - 1) // 2 for n in counts)
    total = len(players) * (len(players) - 1) // 2
    return dict(
        vertices=len(union.parent),
        player_columns=len(players),
        context_columns=len(union.parent) - len(players),
        components=components,
        exact_rank=len(union.parent) - len(components),
        nullity=len(components),
        within_component_player_contrasts=within,
        across_component_player_contrasts=total - within,
        nullspace_pattern="+1 on players and -1 on contexts in each component; zero elsewhere",
        algebra_only=True,
        player_effects_fitted=False,
    )


def graph(rows: list[dict], design: str) -> dict:
    edge_rows = defaultdict(list)
    dropped = []
    for r in rows:
        key = context(r, design)
        if key is None:
            dropped.append(r["record_id"])
            continue
        c = "c:" + json.dumps(key, separators=(",", ":"))
        edge_rows[f"p:{r['player_id']}", c].append(r)
    edges = [(a, b) for a, b in edge_rows]
    result = topology(edges)
    contexts = defaultdict(list)
    edge_evidence = []
    for (player, c), members in sorted(edge_rows.items()):
        item = dict(
            player=player,
            context=c,
            n=len(members),
            record_ids=[r["record_id"] for r in members],
            match_ids=sorted({r["match_id"] for r in members}),
            match_counts=dict(Counter(str(r["match_id"]) for r in members)),
        )
        edge_evidence.append(item)
        contexts[c].append(item)
    pairs = defaultdict(
        lambda: dict(
            shared_contexts=0,
            shared_match_ids=set(),
            supported_match_ids=set(),
            supported_contexts=0,
        )
    )
    for members in contexts.values():
        for a, b in combinations(members, 2):
            key = tuple(sorted((a["player"], b["player"])))
            p = pairs[key]
            p["shared_contexts"] += 1
            p["shared_match_ids"].update(set(a["match_ids"]) & set(b["match_ids"]))
            if a["n"] >= 5 and b["n"] >= 5:
                p["supported_contexts"] += 1
                p["supported_match_ids"].update(
                    mid
                    for mid in set(a["match_ids"]) & set(b["match_ids"])
                    if a["match_counts"][str(mid)] >= 5 and b["match_counts"][str(mid)] >= 5
                )
    result.update(
        observations=sum(len(rs) for rs in edge_rows.values()),
        unique_edges=len(edges),
        dropped_record_ids=dropped,
        edge_evidence=edge_evidence,
        unobserved_population_players=sorted(
            {r["player_id"] for r in rows} - {int(a[2:]) for a, _ in edges}
        ),
        direct_pairs=[
            dict(
                players=list(pair),
                shared_contexts=v["shared_contexts"],
                shared_match_ids=sorted(v["shared_match_ids"]),
                supported_contexts=v["supported_contexts"],
                supported_match_ids=sorted(v["supported_match_ids"]),
            )
            for pair, v in sorted(pairs.items())
        ],
        pairs_with_shared_context=len(pairs),
        pairs_with_at_least5_context=sum(v["supported_contexts"] > 0 for v in pairs.values()),
        pairs_with_at_least5_in_two_matches=sum(
            len(v["supported_match_ids"]) >= 2 for v in pairs.values()
        ),
    )
    return result


def leave_match_out(rows: list[dict]) -> list[dict]:
    """Retain the original player universe when assessing a whole-match support loss."""
    original = graph(rows, "team_match")
    original_players = {r["player_id"] for r in rows}
    original_contrasts = original["within_component_player_contrasts"]
    result = []
    for mid in sorted({r["match_id"] for r in rows}):
        kept = [r for r in rows if r["match_id"] != mid]
        edges = {(f"p:{r['player_id']}", f"c:{r['team_id']}:{r['match_id']}") for r in kept}
        topo = topology(list(edges))
        result.append(
            dict(
                excluded_match_id=mid,
                missing_player_ids=sorted(original_players - {r["player_id"] for r in kept}),
                originally_supported_contrasts_lost=(
                    original_contrasts - topo["within_component_player_contrasts"]
                ),
            )
        )
    return result


def analyse(rows: list[dict], roster: set[int]) -> dict:
    if len({r["record_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate actor-pass records")
    result = {}
    for population in POPULATIONS:
        selected = [r for r in rows if r["memberships"][population]]
        if not selected:
            raise ValueError("Empty declared population; do not silently change estimand")
        result[population] = dict(
            observations=len(selected),
            players=len({r["player_id"] for r in selected}),
            roster_without_observations=sorted(roster - {r["player_id"] for r in selected}),
            unknown_outcome=sum(r["unknown_outcome"] for r in selected),
            missing_position=sum(r["position_id"] is None for r in selected),
            missing_native_cell=sum(r["native_cell"] is None for r in selected),
            designs={name: graph(selected, name) for name in DESIGNS},
            leave_match_out=leave_match_out(selected),
        )
    return dict(
        version=VERSION,
        populations=result,
        response_values_fitted=False,
        selection_uses_provider_completion=True,
        models_fitted=False,
        scientific_status="exploratory_design_diagnostics_not_ability_validation",
    )


def report(summary: dict) -> str:
    lines = [
        "# LOCAL ONLY — Outcome-free comparison design audit",
        "",
        "No response, player coefficient, rating or latent model is fitted.",
        "Rank and contrast statements apply only to the stated additive design.",
        "",
        "| Population | Design | Rows | Players | Contexts | Components | Rank | "
        "Repeated supported pairs |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for population, data in summary["populations"].items():
        for name, g in data["designs"].items():
            lines.append(
                f"| {population} | {name} | {g['observations']} | {g['player_columns']} | "
                f"{g['context_columns']} | {len(g['components'])} | {g['exact_rank']} | "
                f"{g['pairs_with_at_least5_in_two_matches']} |"
            )
    lines += [
        "",
        "Repeated support means >=5 observations per player in a common context in",
        "at least two distinct matches; it is not a statistical adequacy or ability gate.",
        "Only the native-context designs define match-specific cells for this diagnostic.",
        "Repeated support uses >=5 per player per match, even in the team-only graph.",
        "",
        "## Missingness, support loss and exclusions",
    ]
    for name, data in summary["populations"].items():
        info = {k: v for k, v in data.items() if k not in ("designs", "leave_match_out")}
        info["leave_match_out"] = data["leave_match_out"]
        lines += ["", f"### {name}", "", "```json", encode(info).rstrip(), "```"]
    lines += [
        "",
        "## Interpretation limits",
        "",
        "Each disconnected component permits a player/context offset tradeoff.",
        "More repeated rows do not identify cross-component contrasts.",
        "Within-component estimability assumes homogeneous additive player/context effects;",
        "it does not establish causal attribution, transport, precision or latent ability.",
        "Opponents are fixed within team-match; this graph differs from match dependence.",
        "Known source positions are last-observed annotations, not certified stable roles.",
        "The entire corpus is exposed; no independent confirmation is claimed.",
        "See evidence.json for original-event records and summary.json for every edge/pair.",
        "",
    ]
    return "\n".join(lines)


def run(parent: Path, output: Path, implementation: str) -> Path:
    if digest(PROTOCOL.read_bytes()) != PROTOCOL_SHA256:
        raise ValueError("Frozen comparison protocol changed")
    if not re.fullmatch("[0-9a-f]{40}", implementation):
        raise ValueError("Full calculation SHA required")
    if digest((parent / "manifest.json").read_bytes()) != PARENT_MANIFEST:
        raise ValueError("Exact delivered PR20 audit required")
    manifest = verify_artifact(parent)
    protected = dict(manifest["protected_inputs"])
    protected.update({str(p.resolve()): digest(p.read_bytes()) for p in parent.iterdir()})
    if any(digest(Path(p).read_bytes()) != sha for p, sha in protected.items()):
        raise ValueError("Protected parent/source changed")
    if any(output.resolve().is_relative_to(Path(p).parent.resolve()) for p in protected):
        raise ValueError("Output overlaps protected input")
    attribute = Path(manifest["parent_bundle"])
    inputs = json.loads((attribute / "source-inputs.json").read_bytes())
    parents = json.loads((attribute / "evidence.json").read_bytes())
    rows, roster, exclusions = [], set(), []
    for old, source in zip(parents, inputs, strict=True):
        if old["match_id"] != source["match_id"]:
            raise ValueError("Match identity mismatch")
        roster.update(old["player_ids"])
        raw = json.loads(Path(source["events"]).read_bytes())
        rows.extend(observations(old, source, raw))
        for e in raw:
            if e["type"]["name"] == "Pass":
                reasons = []
                if e["period"] not in (1, 2, 3, 4):
                    reasons.append("unsupported_period")
                if e.get("player", {}).get("id") is None:
                    reasons.append("missing_actor")
                if reasons:
                    exclusions.append(
                        dict(match_id=source["match_id"], event_id=e["id"], reasons=reasons)
                    )
    summary = analyse(rows, roster)
    summary["source_exclusions"] = exclusions
    summary["source_events_read"] = sum(p["source_event_count"] for p in parents)
    target = output / VERSION / implementation
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".design-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        (stage / "evidence.json").write_text(encode(rows))
        (stage / "summary.json").write_text(encode(summary))
        (stage / "audit.md").write_text(report(summary))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=implementation,
                    parent_bundle=str(parent.resolve()),
                    parent_manifest_sha256=PARENT_MANIFEST,
                    protocol_sha256=digest(PROTOCOL.read_bytes()),
                    protected_inputs=protected,
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                    restrictions=(
                        "local noncommercial; no provider-data publication or new model fitting"
                    ),
                )
            )
        )
        if any(digest(Path(p).read_bytes()) != sha for p, sha in protected.items()):
            raise ValueError("Source changed during design audit")
        write_bundle(stage, target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/interim/comparison-design"))
    parser.add_argument("--pipeline-revision", required=True)
    args = parser.parse_args()
    print(encode(dict(bundle=str(run(args.parent, args.output, args.pipeline_revision).resolve()))))


if __name__ == "__main__":
    main()
