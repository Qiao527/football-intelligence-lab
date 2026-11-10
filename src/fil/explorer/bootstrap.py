"""Rebuild all derived layers from a verified local raw bundle, then prepare Explorer config."""

import argparse
import json
from pathlib import Path

from fil.explorer.data import prepare
from fil.ingestion.normalize import build_dataset
from fil.metrics.score_artifacts import build_score_artifact
from fil.time.artifacts import build_clock_artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--pipeline-revision", required=True)
    parser.add_argument("--root", type=Path, default=Path("data/interim/local-explorer"))
    args = parser.parse_args()
    raw = args.raw.resolve()
    root = args.root
    canonical = build_dataset(raw, root / "events", args.pipeline_revision)
    clock = build_clock_artifact(raw, canonical, root / "clocks", args.pipeline_revision)
    score = build_score_artifact(raw, canonical, clock, root / "scores", args.pipeline_revision)
    config = {
        k: str(p.resolve())
        for k, p in zip(
            ("raw", "canonical", "clock", "score"), (raw, canonical, clock, score), strict=True
        )
    }
    folder = prepare(config, root / "metrics", args.pipeline_revision)
    config["metrics"] = str(folder.resolve())
    path = folder / "local-config.json"
    body = json.dumps(config, indent=2) + "\n"
    if path.exists() and path.read_text() != body:
        raise ValueError("Existing local config differs; never overwrite")
    if not path.exists():
        path.write_text(body)
    print(json.dumps({"config": str(path.resolve()), "metrics": str(folder)}, indent=2))


if __name__ == "__main__":
    main()
