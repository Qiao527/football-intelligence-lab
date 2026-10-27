"""Assemble a synthetic-only Vercel file payload; never walk data or secret directories."""

import json
from pathlib import Path


def package(root: Path) -> list[dict]:
    files = []
    for base, prefix in ((root / "web", ""), (root / "src/fil", "src/fil/")):
        for p in sorted(base.rglob("*")):
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            rel = p.relative_to(base).as_posix()
            if base.name == "web" and not (
                rel.startswith(("public/", "api/")) or rel in ("requirements.txt", "vercel.json")
            ):
                continue
            if base.name == "fil" and p.suffix not in (".py", ".json"):
                continue
            if p.is_symlink():
                raise ValueError("Symlink in release payload")
            files.append({"file": prefix + rel, "data": p.read_text(), "encoding": "utf-8"})
    files.append({"file": "LICENSE", "data": (root / "LICENSE").read_text(), "encoding": "utf-8"})
    return files


if __name__ == "__main__":
    print(json.dumps(package(Path.cwd())))
