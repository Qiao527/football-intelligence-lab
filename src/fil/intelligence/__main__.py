"""Launch FIL Match Intelligence or bind an existing offline research library."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Launch loopback-only; synthetic demo by default")
    run.add_argument("--port", type=int, default=8501)
    run.add_argument("--local-library", type=Path)
    prepare = sub.add_parser(
        "prepare", help="Bind already acquired/verified local data; no network"
    )
    prepare.add_argument("--corpus", type=Path, required=True)
    prepare.add_argument("--reference", type=Path, required=True)
    prepare.add_argument(
        "--output", type=Path, default=Path("data/interim/intelligence/library.json")
    )
    args = parser.parse_args()
    if args.command == "prepare":
        from fil.intelligence.sources import prepare_library

        try:
            print(prepare_library(args.corpus, args.reference, args.output))
        except (OSError, ValueError, KeyError) as exc:
            parser.exit(1, f"Local verification failed: {exc}\n")
        return
    if not 1024 <= args.port <= 65535:
        parser.error("Port must be between 1024 and 65535")
    if args.local_library is not None and not args.local_library.is_file():
        parser.error("Local library does not exist; prepare it first")
    # Explicit default removes inherited local-data configuration from demo launches.
    env = {
        **os.environ,
        "FIL_INTELLIGENCE_LIBRARY": str(args.local_library.resolve()) if args.local_library else "",
    }
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(Path(__file__).with_name("app.py")),
                "--server.address=127.0.0.1",
                f"--server.port={args.port}",
                "--server.headless=true",
                "--browser.gatherUsageStats=false",
                "--server.fileWatcherType=none",
                "--client.toolbarMode=minimal",
                "--theme.base=dark",
                "--theme.primaryColor=#7ee5ba",
                "--theme.backgroundColor=#0a111a",
                "--theme.secondaryBackgroundColor=#13202d",
                "--theme.textColor=#e7eef5",
            ],
            env=env,
        )
    )


if __name__ == "__main__":
    main()
