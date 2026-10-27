"""Assemble a synthetic-only Vercel file payload; never walk data or secret directories."""

import ast
import json
from pathlib import Path


def package(root: Path) -> list[dict]:
    files = []
    required = set()
    pending = ["fil.intelligence.demo", "fil.intelligence.engine"]
    while pending:
        module = pending.pop()
        path = root / "src" / (module.replace(".", "/") + ".py")
        if not path.exists():
            path = root / "src" / module.replace(".", "/") / "__init__.py"
        if path in required:
            continue
        required.add(path)
        for parent in path.parents:
            if parent == root / "src":
                break
            init = parent / "__init__.py"
            if init.exists():
                required.add(init)
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("fil."):
                pending.append(node.module)

    for base, prefix in ((root / "web", ""), (root / "src/fil", "src/fil/")):
        for p in sorted(base.rglob("*")):
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            rel = p.relative_to(base).as_posix()
            if base.name == "web" and not (
                rel.startswith(("public/", "api/")) or rel in ("requirements.txt", "vercel.json")
            ):
                continue
            if base.name == "fil" and p not in required and p.suffix != ".json":
                continue
            if p.is_symlink():
                raise ValueError("Symlink in release payload")
            files.append({"file": prefix + rel, "data": p.read_text(), "encoding": "utf-8"})
    files.append({"file": "LICENSE", "data": (root / "LICENSE").read_text(), "encoding": "utf-8"})
    return files


if __name__ == "__main__":
    print(json.dumps(package(Path.cwd())))
