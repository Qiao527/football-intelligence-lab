"""Reproduce the approved pilot and independent evidence locally; no full expansion bypass."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from fil.research.acquisition import REVISION, acquire, scope
from fil.research.pilot import audit, encode, pilot_gate
from fil.research.worldcup import build


def write_once(path: Path, body: str):
    if path.exists() and path.read_text() != body:
        raise ValueError("Existing run evidence differs; never overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(body)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--pipeline-revision", required=True)
    p.add_argument("--output", type=Path, default=Path("data/interim/worldcup-delivery"))
    p.add_argument("--raw-root", type=Path, default=Path("data/raw/statsbomb-corpus"))
    p.add_argument(
        "--proposal", type=Path, default=Path("docs/research/statsbomb_corpus_proposal.json")
    )
    p.add_argument(
        "--acquire-pilot",
        action="store_true",
        help="Only six approved pilot matches; existing immutable bundles verified on reuse",
    )
    a = p.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", a.pipeline_revision):
        raise ValueError("Full implementation SHA required")
    config = json.loads(a.config.read_bytes())
    if any(
        a.output.resolve().is_relative_to(root.resolve())
        for root in [a.raw_root, *[Path(config[k]) for k in ("raw", "canonical", "clock", "score")]]
    ):
        raise ValueError("Outputs must be outside immutable inputs")
    reports = []
    for mid in scope(a.proposal)["pilot_new_match_ids"]:
        folder = a.raw_root / REVISION / str(mid)
        if a.acquire_pilot:
            folder = acquire(mid, a.raw_root, a.proposal, a.pipeline_revision)
        reports.append(
            audit(
                folder, a.proposal, Path(config["raw"]), a.output / "quality", a.pipeline_revision
            )
        )
    run = a.output / "runs" / a.pipeline_revision
    report_path = run / "reports.json"
    write_once(report_path, encode([str(p.resolve()) for p in reports]))
    bundle = build(
        reports, a.raw_root, a.proposal, config, a.output / "corpus", a.pipeline_revision
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("verify_worldcup_source.py")),
            str(a.config),
            str(report_path),
            str(bundle),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    independent = run / "independent-verification.json"
    write_once(independent, completed.stdout)
    gate = pilot_gate(reports, run / "pilot-gate.json", independent)
    result = dict(
        bundle=str(bundle.resolve()),
        pilot_gate=gate["status"],
        independent_verification=str(independent.resolve()),
        new_raw_matches=6,
        expansion_performed=False,
    )
    write_once(run / "delivery.json", encode(result))
    print(encode(result))


if __name__ == "__main__":
    main()
