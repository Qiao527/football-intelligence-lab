"""Build or offline-verify a period-aware clock artifact, without altering canonical inputs."""

import argparse
import json
from pathlib import Path

import pyarrow as pa

from fil.ingestion.statsbomb import AcquisitionError
from fil.schema import SchemaError
from fil.time.artifacts import build_clock_artifact, verify_clock_artifact
from fil.time.clock import ClockError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--raw-bundle", type=Path, required=True)
        command.add_argument("--canonical-dataset", type=Path, required=True)
        if name == "build":
            command.add_argument("--pipeline-revision", required=True)
            command.add_argument("--output-root", type=Path, default=Path("data/interim/clocks"))
        else:
            command.add_argument("--clock-dataset", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        folder = (
            build_clock_artifact(
                args.raw_bundle, args.canonical_dataset, args.output_root, args.pipeline_revision
            )
            if args.command == "build"
            else args.clock_dataset
        )
        manifest = verify_clock_artifact(args.raw_bundle, args.canonical_dataset, folder)
    except (
        ClockError,
        SchemaError,
        AcquisitionError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        pa.ArrowException,
    ) as exc:
        parser.exit(1, f"Clock verification failed (inputs unchanged): {exc}\n")
    print(
        json.dumps(
            {
                "clock_dataset": str(folder),
                "clock_version": manifest["clock_version"],
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
