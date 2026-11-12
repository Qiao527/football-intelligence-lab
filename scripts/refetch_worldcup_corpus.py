"""Owner-authorized re-fetch of the pinned World Cup enumeration.

This is a byte-level re-fetch, not a renewed data acceptance. It verifies each
file against the approved enumeration (size plus upstream git blob SHA-1) and
writes the same manifest shape the acceptance pipeline reads, so
`fil.research.acquisition.verify` can validate every bundle afterwards.
"""

import argparse
import hashlib
import json
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from fil.research.acquisition import PROPOSAL_SHA256, REVISION, digest, scope, verify

AUTHORIZATION = (
    "Owner authorization in FIL conversation, 2026-11-11: re-fetch the pinned "
    "enumeration. Byte verification only; no renewed acceptance or gate claim."
)
RIGHTS = "local noncommercial research only; no redistribution or external upload"
MATCHES_PATH = "data/matches/43/3.json"
MATCHES_NAME = "competition-matches.json"


def blob_sha1(body: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()


def fetch(url: str, attempts: int = 4) -> bytes:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                return response.read()
        except Exception as error:
            last = error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Fetch failed after {attempts} attempts: {url}") from last


def url_for(path: str) -> str:
    return f"https://raw.githubusercontent.com/hudl/open-data/{REVISION}/{path}"


def build_bundle(mid: int, entries: list[dict], root: Path, implementation: str) -> Path:
    folder = root / REVISION / str(mid)
    if folder.exists():
        verify(folder, PROPOSAL_PATH)
        return folder
    folder.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".stage-{mid}-", dir=folder.parent))
    files: dict[str, dict] = {}
    for entry in entries:
        body = fetch(url_for(entry["path"]))
        if len(body) != entry["size_bytes"] or blob_sha1(body) != entry["upstream_git_blob_sha1"]:
            raise ValueError(f"Source byte/hash mismatch for {entry['path']}")
        name = Path(entry["path"]).name + "." + entry["path"].split("/")[1]
        (stage / name).write_bytes(body)
        files[entry["path"]] = {
            "source_url": url_for(entry["path"]),
            "sha256": digest(body),
            "size_bytes": len(body),
            "upstream_git_blob_sha1": entry["upstream_git_blob_sha1"],
        }
    manifest = {
        "version": "fil-owner-authorized-refetch-1",
        "source": "statsbomb_open_data",
        "match_id": mid,
        "upstream_revision": REVISION,
        "proposal_sha256": PROPOSAL_SHA256,
        "implementation_sha": implementation,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "owner_authorization": AUTHORIZATION,
        "rights": RIGHTS,
        "files": files,
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    stage.rename(folder)
    verify(folder, PROPOSAL_PATH)
    return folder


def main() -> int:
    global PROPOSAL_PATH
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/statsbomb-corpus"))
    parser.add_argument("--proposal", type=Path,
                        default=Path("docs/research/statsbomb_corpus_proposal.json"))
    parser.add_argument("--implementation", required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    PROPOSAL_PATH = args.proposal
    approved = scope(args.proposal)
    by_match: dict[int, list[dict]] = {}
    for entry in approved["files"]:
        by_match.setdefault(int(Path(entry["path"]).stem), []).append(entry)
    if len(approved["files"]) != 126 or len(by_match) != 63:
        raise ValueError("Approved enumeration changed")

    args.root.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(
            lambda item: build_bundle(item[0], item[1], args.root, args.implementation),
            sorted(by_match.items()),
        ))

    metadata = fetch(url_for(MATCHES_PATH))
    expected = approved["metadata_source_sha256"]
    if digest(metadata) != expected:
        raise ValueError("Competition metadata hash mismatch")
    (args.root / REVISION / MATCHES_NAME).write_bytes(metadata)

    manifests = [json.loads((p / "manifest.json").read_bytes()) for p in results]
    summary = {
        "version": "fil-owner-authorized-refetch-1",
        "upstream_revision": REVISION,
        "proposal_sha256": PROPOSAL_SHA256,
        "implementation_sha": args.implementation,
        "owner_authorization": AUTHORIZATION,
        "matches": len(manifests),
        "files": sum(len(m["files"]) for m in manifests),
        "bytes": sum(
            item["size_bytes"] for m in manifests for item in m["files"].values()
        ),
        "competition_metadata_sha256": digest(metadata),
        "verification": "size + upstream git blob SHA-1 + bundle verify() for every match",
        "not_claimed": "renewed acceptance, pilot gate, batch proof or model/data rights",
    }
    (args.root / REVISION / "refetch.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({k: summary[k] for k in ("matches", "files", "bytes")}, indent=1))
    return 0


PROPOSAL_PATH = Path("docs/research/statsbomb_corpus_proposal.json")

if __name__ == "__main__":
    sys.exit(main())
