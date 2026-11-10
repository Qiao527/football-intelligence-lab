"""Verify a deployed public alpha instance against this repository's contract."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUERY = (
    "Find players who contribute to defensive transitions and build-up even when "
    "conventional attacking statistics are unremarkable."
)
REQUIRED_PLAYERS = {"Mara Vale", "Tess Rowe"}


def health_problems(payload: dict, expected_commit: str | None = None) -> list[str]:
    """Return contract violations for the deployment identity endpoint."""
    problems = []
    if payload.get("status") != "ok":
        problems.append(f"health status is {payload.get('status')!r}")
    if payload.get("mode") != "synthetic-only":
        problems.append(f"source mode is {payload.get('mode')!r}")
    if expected_commit is not None and payload.get("commit") != expected_commit:
        problems.append(
            f"deployed commit {payload.get('commit')!r} does not match expected {expected_commit!r}"
        )
    return problems


def scout_problems(payload: dict) -> list[str]:
    """Return contract violations for the Find candidates response."""
    problems = []
    if payload.get("source_mode") != "synthetic":
        problems.append(f"scout source mode is {payload.get('source_mode')!r}")
    names = {candidate.get("name") for candidate in payload.get("candidates", [])}
    missing = sorted(REQUIRED_PLAYERS - names)
    if missing:
        problems.append(f"scout response is missing candidate evidence for {missing}")
    if payload.get("abstention"):
        problems.append(f"scout request abstained: {payload['abstention']}")
    return problems


def index_problems(html: str) -> list[str]:
    """Return contract violations for the discovery page."""
    if "Find candidates" in html:
        return []
    return ["the discovery page has no Find candidates control"]


def fetch(url: str, payload: dict | None = None) -> tuple[int, bytes]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    with urlopen(Request(url, data=data, headers=headers), timeout=20) as response:
        return response.status, response.read()


def describe_failure(error: HTTPError) -> str:
    body = error.read().decode(errors="replace")
    if error.headers.get("x-vercel-error") == "NOT_FOUND" or "could not be found" in body:
        return (
            f"HTTP {error.code} from the hosting platform, not this API. "
            "The serverless function is not deployed for this route."
        )
    return f"HTTP {error.code}: {body[:200]}"


def check(url: str, expected_commit: str | None, browser: str | None) -> list[str]:
    problems = []
    try:
        status, body = fetch(f"{url}/api/health")
        health = json.loads(body)
        if status != 200:
            problems.append(f"health returned HTTP {status}")
        problems.extend(health_problems(health, expected_commit))
        status, body = fetch(f"{url}/api/scout", {"query": DEFAULT_QUERY})
        problems.extend(scout_problems(json.loads(body)))
        status, body = fetch(f"{url}/api/scout-fixture")
        if status != 200 or json.loads(body)["provenance"]["mode"] != "synthetic":
            problems.append("the scout fixture is unavailable")
        status, body = fetch(f"{url}/")
        problems.extend(index_problems(body.decode(errors="replace")))
    except HTTPError as error:
        problems.append(describe_failure(error))
        return problems
    if browser:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "check_scout_copilot_browser.py"),
                "--browser",
                browser,
                "--url",
                url,
            ],
            check=False,
        )
        if result.returncode:
            problems.append("the Chromium journey failed")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expect-commit", help="Commit SHA the deployment must report")
    parser.add_argument("--browser", help="Chromium executable for the interactive journey")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    problems = check(base, args.expect_commit, args.browser)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        raise SystemExit(1)
    if args.expect_commit is None:
        print("WARN: --expect-commit was omitted, so deployment identity was not checked")
    print(f"PASS: {base} serves the synthetic Find candidates contract")


if __name__ == "__main__":
    main()
