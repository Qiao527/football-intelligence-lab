"""Package the explicitly listed fictional-only public runtime, failing closed."""

import argparse
import ast
import hashlib
import json
from pathlib import Path

# The destination is relative to the Vercel project root; no directory traversal or globbing.
PUBLIC_FILES = {
    "LICENSE": "LICENSE",
    "requirements.txt": "web/requirements.txt",
    "package.json": "web/package.json",
    "vercel.json": "web/vercel.json",
    "api/__init__.py": "web/api/__init__.py",
    "api/analyze.py": "web/api/analyze.py",
    "api/health.py": "web/api/health.py",
    "api/index.py": "web/api/index.py",
    "api/matches.py": "web/api/matches.py",
    "api/scout.py": "web/api/scout.py",
    "api/scout-fixture.py": "web/api/scout-fixture.py",
    "public/analytics.js": "web/public/analytics.js",
    "public/app.js": "web/public/app.js",
    "public/copilot.js": "web/public/copilot.js",
    "public/index.html": "web/public/index.html",
    "public/match.html": "web/public/match.html",
    "public/scout.css": "web/public/scout.css",
    "public/scout.js": "web/public/scout.js",
    "public/style.css": "web/public/style.css",
    "src/fil/__init__.py": "src/fil/__init__.py",
    "src/fil/intelligence/__init__.py": "src/fil/intelligence/__init__.py",
    "src/fil/intelligence/demo.py": "src/fil/intelligence/demo.py",
    "src/fil/intelligence/report_core.py": "src/fil/intelligence/report_core.py",
    "src/fil/intelligence/public_score.py": "src/fil/intelligence/public_score.py",
    "src/fil/intelligence/scout.py": "src/fil/intelligence/scout.py",
    "src/fil/intelligence/scout_fixture.py": "src/fil/intelligence/scout_fixture.py",
}


def package(root: Path) -> list[dict]:
    """Read only allowlisted regular files and check their explicit FIL imports."""
    root = root.resolve()
    files = []
    for destination, source in sorted(PUBLIC_FILES.items()):
        path = root / source
        if any(part.is_symlink() for part in (path, *path.parents) if part != root):
            raise ValueError(f"Symlink in release input: {source}")
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Missing or unsafe release input: {source}")
        data = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            for node in ast.walk(ast.parse(data, filename=source)):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith("fil.")
                ):
                    module = node.module.replace(".", "/")
                    if f"src/{module}.py" not in PUBLIC_FILES and (
                        f"src/{module}/__init__.py" not in PUBLIC_FILES
                    ):
                        raise ValueError(f"Unlisted import {node.module} in {source}")
                if isinstance(node, ast.Import):
                    for item in node.names:
                        if item.name.startswith("fil."):
                            raise ValueError(f"Unverified FIL import {item.name} in {source}")
        files.append({"file": destination, "data": data, "encoding": "utf-8"})
    return files


def manifest(files: list[dict]) -> dict:
    """Return an exact per-file digest without including source contents."""
    return {
        "status": "PENDING_INDEPENDENT_REVIEW",
        "files": [
            {
                "path": f["file"],
                "bytes": len(f["data"].encode()),
                "sha256": hashlib.sha256(f["data"].encode()).hexdigest(),
            }
            for f in files
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--directory", type=Path, help="New, empty package directory")
    args = parser.parse_args()
    files = package(Path(__file__).resolve().parents[1])
    if args.manifest:
        args.manifest.write_text(json.dumps(manifest(files), indent=2) + "\n")
    if args.directory:
        args.directory.mkdir(parents=True, exist_ok=False)
        for item in files:
            path = args.directory / item["file"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(item["data"], encoding="utf-8")
    else:
        print(json.dumps(files))


if __name__ == "__main__":
    main()
