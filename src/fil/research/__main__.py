"""Build an immutable local research corpus and illustrative case from verified configs."""

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

import pyarrow.parquet as pq

from fil.explorer.data import fingerprint, load_match
from fil.ingestion.player_roster import load_roster
from fil.possessions.extract import reconstruct
from fil.research.case import investigate
from fil.research.corpus import AUTHORISED, VERSION, MatchEvidence, assemble
from fil.research.process import analyse


def prepare(configs: list[dict], output: Path, revision: str) -> Path:
    if not re.fullmatch("[0-9a-f]{40}", revision):
        raise ValueError("Expected full implementation SHA")
    if not configs or any(
        output.resolve().is_relative_to(Path(c[k]).resolve())
        for c in configs
        for k in ("raw", "canonical", "clock", "score", "metrics")
        if k in c
    ):
        raise ValueError("Output must be outside immutable inputs; nonempty corpus required")
    hashes = sorted(fingerprint(c) for c in configs)
    matches = []
    for c in configs:
        manifest = (Path(c["raw"]) / "manifest.json").read_bytes()
        digest = hashlib.sha256(manifest).hexdigest()
        if digest not in {a[2] for a in AUTHORISED}:
            raise ValueError(
                "Source manifest outside reviewed authorisation; no acquisition performed"
            )
        events, meta = load_match(c)
        roster = load_roster(Path(c["raw"]), meta["match_id"], meta["source_manifest_sha256"])
        matches.append(MatchEvidence(events, meta, roster))
    matches.sort(key=lambda m: m.metadata["match_id"])
    table, report = assemble(matches)
    processes = [
        analyse(
            reconstruct(m.events, m.metadata["home_team_id"], m.metadata["away_team_id"]).actions
        )
        for m in matches
    ]
    # This illustrative case has one named source fixture; never fabricate a corpus case.
    case_match = next((m for m in matches if m.metadata["match_id"] == 8658), None)
    case = (
        investigate(case_match.events, case_match.metadata, case_match.roster)
        if case_match
        else dict(
            status="insufficient_evidence",
            scientifically_validated=False,
            reason="Nominated fixture absent; no substitute case selected",
        )
    )
    content = hashlib.sha256(json.dumps(hashes).encode()).hexdigest()
    target = output / content / VERSION / revision
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fil-research-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        pq.write_table(table, stage / "events.parquet", compression="zstd", use_dictionary=False)
        for name, value in [("corpus", report), ("case", case), ("process", processes)]:
            (stage / f"{name}.json").write_text(
                json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
            )
        (stage / "case.md").write_text(case_markdown(case))
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir()}
        manifest = dict(
            version=VERSION,
            implementation_sha=revision,
            input_hashes=hashes,
            files=files,
            rights="Unchanged local noncommercial scope only; no publication/redistribution",
            validation_status="insufficient_evidence_for_scientific_generalisation",
        )
        (stage / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        if hashes != sorted(fingerprint(c) for c in configs):
            raise ValueError("Inputs changed during research build")
        if target.exists() or target.is_symlink():
            if target.is_symlink() or {p.name for p in target.iterdir()} != {
                p.name for p in stage.iterdir()
            }:
                raise ValueError("Invalid research bundle members")
            for p in stage.iterdir():
                prior = target / p.name
                if (
                    prior.is_symlink()
                    or not prior.is_file()
                    or prior.read_bytes() != p.read_bytes()
                ):
                    raise ValueError("Research artifact differs; never overwrite")
            return target
        stage.rename(target)
    return target


def case_markdown(c: dict) -> str:
    if "player" not in c:
        return "# No illustrative case\n\n" + c["reason"] + "\n"
    p = c["player"]
    lines = [
        "# Local illustrative football case — inconclusive",
        "",
        c["question"],
        "",
        f"Selected player: {p['player_name']} ({p['player_id']}). {c['selection']}",
        "",
        "Conventional view: completed passes, shot-assist links and recorded shots are factual",
        "end-action summaries; they cannot establish quality or all buildup involvement.",
        f"Shot goals: {c['conventional']['shot_goals']}; "
        f"shots: {c['conventional']['shot_events']}; "
        f"source shot xG: {c['conventional']['source_shot_xg']:.6f}.",
        f"Recorded actor events: {p['selected_events']}; "
        f"completed passes: {p['completed_passes']}; "
        f"reciprocal native shot links: {p['native_shot_links']}; "
        f"pre-shot native IDs: {p['pre_shot_possessions']}.",
        "",
        "| Rule | Eligible moves | Later-shot moves | Fraction |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, r in c["player_baselines"].items():
        rate = "NA" if r["shot_followed_fraction"] is None else f"{r['shot_followed_fraction']:.3f}"
        lines.append(f"| {name} | {r['n']} | {r['shot_followed_n']} | {rate} |")
    omitted = c["shot_context_moves_excluded_by_gain10"]
    contrast = c["gain10_moves_without_later_shot"]
    all_hits = c["player_baselines"]["all_completed_moves"]["shot_followed_n"]
    lines += [
        "",
        "## Additional evidence and counterevidence",
        "",
        f"The gain-10 rule omits {len(omitted)} of {all_hits} recorded shot-followed moves. "
        f"It also flags {len(contrast)} moves without a later shot in the same native ID/period.",
        "This shows why geometric progression is not a complete buildup-contribution measure. "
        "A missing later shot does not make a completed move a bad decision.",
        "",
        "### Source-action review queue (illustrative, not ranked)",
        "",
    ]
    moves = {r["event_id"]: r for r in c["player_moves"]}
    for label, ids in (
        ("Shot context omitted by gain-10", omitted),
        ("Gain-10 without recorded later shot", contrast),
    ):
        lines += ["**" + label + "**", ""]
        for eid in ids[:3]:
            r = moves[eid]
            lines.append(
                f"- P{r['period']} {r['display_clock']} · {r['event_type']} · "
                f"source ID `{eid}` · native ID {r['possession_id']} · "
                f"Δx {r['delta_x']} / gain {r['distance_gain']} · "
                f"context shots {r['later_shot_ids']}"
            )
        if not ids:
            lines.append("No examples in this fixture selection.")
        lines.append("")
    lines += [
        "",
        "These are overlapping descriptive subsets, not forecasts or causal credit.",
        (
            "The JSON preserves every underlying move and later-shot ID, "
            "phase/state strata and team baseline."
        ),
        "",
        "Competing explanations: " + "; ".join(c["competing_explanations"]) + ".",
        "",
        "Independent verification: run scripts/verify_research_source.py on this bundle.",
        "This checks original records; it is not independent football judgement.",
        "",
        "Remaining uncertainty: " + c["uncertainty"],
        "",
        "Decision use: " + c["decision_use"] + ".",
        "",
        "Conclusion: hidden-connector importance and incremental practical value are INCONCLUSIVE.",
        (
            "A football reviewer should examine the retained actions and "
            "counterexamples, then replicate"
        ),
        (
            "on authorised held-out matches with validated exposure and "
            "role/state/opponent adjustment."
        ),
        "",
        "Local analysis only. Do not publish without the existing rights/branding review.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, action="append", required=True)
    p.add_argument("--output", type=Path, default=Path("data/interim/research"))
    p.add_argument("--pipeline-revision", required=True)
    args = p.parse_args()
    folder = prepare(
        [json.loads(c.read_bytes()) for c in args.config], args.output, args.pipeline_revision
    )
    print(
        json.dumps(
            dict(
                bundle=str(folder.resolve()),
                status="SOURCE_FACTS_VERIFIED",
                scientific_validation="insufficient_evidence",
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
