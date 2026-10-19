"""Build or offline-verify a reconciled score artifact, without altering canonical inputs."""

import argparse
import json
from pathlib import Path

import pyarrow as pa

from fil.ingestion.statsbomb import AcquisitionError
from fil.metrics.score import ScoreError
from fil.metrics.score_artifacts import build_score_artifact, verify_score_artifact
from fil.schema import SchemaError
from fil.time.clock import ClockError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--raw-bundle", type=Path, required=True)
        command.add_argument("--canonical-dataset", type=Path, required=True)
        command.add_argument("--clock-dataset", type=Path, required=True)
        if name == "build":
            command.add_argument("--pipeline-revision", required=True)
            command.add_argument("--output-root", type=Path, default=Path("data/interim/scores"))
        else:
            command.add_argument("--score-dataset", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        folder = (
            build_score_artifact(
                args.raw_bundle,
                args.canonical_dataset,
                args.clock_dataset,
                args.output_root,
                args.pipeline_revision,
            )
            if args.command == "build"
            else args.score_dataset
        )
        manifest = verify_score_artifact(
            args.raw_bundle, args.canonical_dataset, args.clock_dataset, folder
        )
    except (
        ClockError,
        ScoreError,
        SchemaError,
        AcquisitionError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        pa.ArrowException,
    ) as exc:
        parser.exit(1, f"Score verification failed (inputs unchanged): {exc}\n")
    print(
        json.dumps(
            {
                "score_dataset": str(folder),
                "score_version": manifest["score_version"],
                "row_count": manifest["row_count"],
                "technical_verification": "PASS",
                "quality_report": str(folder / "quality.json"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
