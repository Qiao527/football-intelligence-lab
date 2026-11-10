"""Launch the read-only Streamlit Explorer on loopback only."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    if not args.config.is_file() or not 1024 <= args.port <= 65535:
        parser.error("Expected local config and port between 1024 and 65535")
    env = {**os.environ, "FIL_EXPLORER_CONFIG": str(args.config.resolve())}
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
                "--theme.base=dark",
                "--theme.primaryColor=#66c9ed",
                "--theme.backgroundColor=#0c1420",
                "--theme.secondaryBackgroundColor=#152131",
                "--theme.textColor=#e8edf3",
                "--client.toolbarMode=minimal",
            ],
            env=env,
        )
    )


if __name__ == "__main__":
    main()
