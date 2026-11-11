"""Fetch the frozen league development set; the held-out league is never touched.

Enumeration comes from the provider's own match index at a pinned revision, and each
file is verified against the git tree blob SHA-1 and size, so a download cannot pass
by being merely "the right URL".
"""

import argparse
import hashlib
import json
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

REVISION = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
RAW = f"https://raw.githubusercontent.com/hudl/open-data/{REVISION}/"
TREE = f"https://api.github.com/repos/hudl/open-data/git/trees/{REVISION}?recursive=1"
DEVELOPMENT = ((2, 27, "Premier League"), (11, 27, "La Liga"), (12, 27, "Serie A"))
HELD_OUT = (7, 27, "Ligue 1")
AUTHORIZATION = (
    "Owner authorization in FIL conversation, 2026-11-11: fetch the 2015/16 league "
    "development set only. Ligue 1 is never acquired here."
)
RIGHTS = "local noncommercial research only; no redistribution or external upload"
VERSION = "fil-league-fetch-1"


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def blob_sha1(body: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()


def fetch(url: str, attempts: int = 4) -> bytes:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "fil-research"})
            with urllib.request.urlopen(request, timeout=180) as response:
                return response.read()
        except Exception as error:
            last = error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Fetch failed after {attempts} attempts: {url}") from last


def tree_index() -> dict[str, dict]:
    payload = json.loads(fetch(TREE))
    if payload.get("truncated"):
        raise ValueError("Git tree is truncated; enumeration would be incomplete")
    return {entry["path"]: entry for entry in payload["tree"] if entry["type"] == "blob"}


def verify_bundle(folder: Path, expected: dict[str, dict]) -> None:
    manifest = json.loads((folder / "manifest.json").read_bytes())
    if manifest["upstream_revision"] != REVISION or manifest["match_id"] != int(folder.name):
        raise ValueError("Bundle identity mismatch")
    if set(manifest["files"]) != set(expected):
        raise ValueError("Bundle scope mismatch")
    for path, item in manifest["files"].items():
        name = Path(path).name + "." + path.split("/")[1]
        body = (folder / name).read_bytes()
        if (
            blob_sha1(body) != expected[path]["sha"]
            or len(body) != expected[path]["size"]
            or digest(body) != item["sha256"]
        ):
            raise ValueError(f"Payload mismatch: {path}")


def build_bundle(match_id: int, entries: dict[str, dict], root: Path) -> Path:
    folder = root / REVISION / str(match_id)
    if folder.exists():
        verify_bundle(folder, entries)
        return folder
    folder.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".stage-{match_id}-", dir=folder.parent))
    files: dict[str, dict] = {}
    for path, entry in entries.items():
        body = fetch(RAW + path)
        if len(body) != entry["size"] or blob_sha1(body) != entry["sha"]:
            raise ValueError(f"Source byte/hash mismatch: {path}")
        name = Path(path).name + "." + path.split("/")[1]
        (stage / name).write_bytes(body)
        files[path] = {
            "source_url": RAW + path,
            "sha256": digest(body),
            "size_bytes": len(body),
            "upstream_git_blob_sha1": entry["sha"],
        }
    manifest = {
        "version": VERSION,
        "source": "statsbomb_open_data",
        "match_id": match_id,
        "upstream_revision": REVISION,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "owner_authorization": AUTHORIZATION,
        "rights": RIGHTS,
        "files": files,
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    stage.rename(folder)
    verify_bundle(folder, entries)
    return folder


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/statsbomb-league"))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    index = tree_index()
    (args.root / REVISION / "meta").mkdir(parents=True, exist_ok=True)
    per_league = {}
    matches: dict[int, dict[str, dict]] = {}
    for competition, season, name in DEVELOPMENT:
        path = f"data/matches/{competition}/{season}.json"
        body = fetch(RAW + path)
        entry = index[path]
        if len(body) != entry["size"] or blob_sha1(body) != entry["sha"]:
            raise ValueError(f"Match index hash mismatch: {path}")
        (args.root / REVISION / "meta" / f"{competition}-{season}.json").write_bytes(body)
        ids = [m["match_id"] for m in json.loads(body)]
        per_league[name] = {"matches": len(ids), "competition": competition,
                            "season": season, "index_sha256": digest(body)}
        for match_id in ids:
            matches[match_id] = {
                f"data/events/{match_id}.json": index[f"data/events/{match_id}.json"],
                f"data/lineups/{match_id}.json": index[f"data/lineups/{match_id}.json"],
            }

    selected = sorted(matches)
    if args.limit:
        selected = selected[: args.limit]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(lambda mid: build_bundle(mid, matches[mid], args.root), selected))

    summary = {
        "version": VERSION,
        "upstream_revision": REVISION,
        "tree_entries": len(index),
        "owner_authorization": AUTHORIZATION,
        "rights": RIGHTS,
        "held_out_not_acquired": {
            "league": HELD_OUT[2], "competition": HELD_OUT[0], "season": HELD_OUT[1]
        },
        "leagues": per_league,
        "matches": len(selected),
        "bytes": sum(
            item["size_bytes"]
            for mid in selected
            for item in json.loads(
                (args.root / REVISION / str(mid) / "manifest.json").read_bytes()
            )["files"].values()
        ),
        "verification": "size + git tree blob SHA-1 + sha256 manifest per file",
    }
    (args.root / REVISION / "fetch.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({k: summary[k] for k in ("matches", "bytes", "leagues")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
