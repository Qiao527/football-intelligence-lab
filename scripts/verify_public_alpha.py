"""Build the public alpha bundle and verify it in isolation."""

import argparse
import hashlib
import json
import runpy
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
packager = runpy.run_path(str(ROOT / "scripts" / "package_public_web.py"))
API_ENTRYPOINTS = ("health", "matches", "analyze", "scout", "scout-fixture")
DEFAULT_QUERY = (
    "Find players who contribute to defensive transitions and build-up even when "
    "conventional attacking statistics are unremarkable."
)
REQUIRED_PLAYERS = {"Mara Vale", "Tess Rowe"}
SERVER = """
import importlib.util
import sys
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

root = sys.argv[1]
sys.path.insert(0, root)
spec = importlib.util.spec_from_file_location("bundle_api", root + "/api/scout.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
API = module.handler


class Local(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/"):
            return API.do_GET(self)
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/scout"):
            return API.do_POST(self)
        self.send_error(405)


server = HTTPServer(("127.0.0.1", 0), partial(Local, directory=root + "/public"))
print(server.server_port, flush=True)
server.serve_forever()
"""


def build(directory: Path) -> None:
    """Write the allowlisted bundle into a directory that must not already exist."""
    files = packager["package"](ROOT)
    directory.mkdir(parents=True)
    for item in files:
        path = directory / item["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item["data"], encoding="utf-8")


def digest(directory: Path) -> dict[str, tuple[int, str]]:
    return {
        str(path.relative_to(directory)): (
            path.stat().st_size,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def verify_manifest(committed: Path, directory: Path) -> None:
    """Fail when the committed release manifest does not describe the built bundle."""
    expected = {
        entry["path"]: (entry["bytes"], entry["sha256"])
        for entry in json.loads(committed.read_text(encoding="utf-8"))["files"]
    }
    actual = digest(directory)
    if set(expected) != set(actual):
        raise SystemExit(f"FAIL: bundle paths differ: {sorted(set(expected) ^ set(actual))}")
    stale = sorted(path for path in expected if expected[path] != actual[path])
    if stale:
        raise SystemExit(f"FAIL: committed manifest is stale for {stale}")


def check_entrypoints(directory: Path) -> None:
    """Load every API entrypoint the way a serverless builder executes it."""
    for name in API_ENTRYPOINTS:
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(directory / "api" / f"{name}.py")],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise SystemExit(f"FAIL: {name}.py did not load in isolation:\n{result.stderr}")


def fetch(url: str, payload: dict | None = None) -> tuple[int, bytes]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, response.read()


def check_http(directory: Path) -> None:
    """Serve the bundle with an isolated interpreter and verify the API contract."""
    process = subprocess.Popen(
        [sys.executable, "-I", "-B", "-c", SERVER, str(directory)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        port = process.stdout.readline().strip()
        if not port.isdigit():
            raise SystemExit("FAIL: the bundle server did not start")
        base = f"http://127.0.0.1:{port}"
        status, body = fetch(f"{base}/api/health")
        health = json.loads(body)
        if status != 200 or health.get("mode") != "synthetic-only":
            raise SystemExit(f"FAIL: unexpected health response: {status} {health}")
        status, body = fetch(f"{base}/api/scout", {"query": DEFAULT_QUERY})
        result = json.loads(body)
        names = {candidate["name"] for candidate in result.get("candidates", [])}
        if (
            status != 200
            or result.get("source_mode") != "synthetic"
            or not REQUIRED_PLAYERS <= names
        ):
            raise SystemExit(f"FAIL: unexpected scout response: {status} {result}")
        status, body = fetch(f"{base}/api/scout-fixture")
        if status != 200 or json.loads(body)["provenance"]["mode"] != "synthetic":
            raise SystemExit("FAIL: the scout fixture is unavailable")
        status, body = fetch(f"{base}/")
        if status != 200 or b"Find candidates" not in body:
            raise SystemExit("FAIL: the discovery interface is not served")
    finally:
        process.terminate()
        process.wait(timeout=10)


def verify_all(directory: Path, manifest: Path) -> None:
    """Build, exercise and re-check the bundle so no execution residue ships."""
    build(directory)
    verify_manifest(manifest, directory)
    check_entrypoints(directory)
    check_http(directory)
    verify_manifest(manifest, directory)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, help="New, empty bundle directory")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "docs" / "PUBLIC_ALPHA_MANIFEST.json",
        help="Committed release manifest to compare against",
    )
    args = parser.parse_args()
    if args.directory is None:
        with tempfile.TemporaryDirectory() as temporary:
            verify_all(Path(temporary) / "bundle", args.manifest)
    else:
        verify_all(args.directory, args.manifest)
    print("PASS: public alpha bundle matches its manifest and serves the Find candidates request")


if __name__ == "__main__":
    main()
