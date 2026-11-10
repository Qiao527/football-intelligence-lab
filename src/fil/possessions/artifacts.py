"""Immutable local possession QA/facts, recomputed from the existing verified source chain."""

import argparse
import hashlib
import json
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from fil.explorer.data import fingerprint, load_match
from fil.possessions.extract import VERSION, process_summary, reconstruct


def prepare(config: dict, output: Path, revision: str) -> Path:
    """Stage fresh facts or verify exact existing outputs; never repair/overwrite."""
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected full implementation SHA")
    if any(
        output.resolve().is_relative_to(Path(config[k]).resolve())
        for k in ("raw", "canonical", "clock", "score", "metrics")
        if k in config
    ):
        raise ValueError("Possession output must be outside immutable inputs")
    content_key = fingerprint(config)
    events, meta = load_match(config)
    facts = reconstruct(events, meta["home_team_id"], meta["away_team_id"])
    report = {
        **facts.quality,
        "version": VERSION,
        "match": meta,
        "inputs": content_key,
        "code_sha": revision,
        "process_summary": process_summary(facts.possessions),
        "comparison_exposure": "raw counts; no equal-minutes/causal interpretation",
        "membership_semantics": "StatsBomb native possession IDs, specification v1.1 pp9-10",
        "rights": "unchanged local noncommercial research; no redistribution",
    }
    target = output / content_key / VERSION / revision
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fil-possessions-", dir=target.parent) as tmp:
        candidate = Path(tmp) / "bundle"
        candidate.mkdir()
        for name, table in (
            ("possessions", facts.possessions),
            ("possession_actions", facts.actions),
        ):
            pq.write_table(
                table,
                candidate / f"{name}.parquet",
                compression="zstd",
                version="2.6",
                use_dictionary=False,
                write_statistics=True,
            )
        (candidate / "quality.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        files = {
            p.name: {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "size_bytes": p.stat().st_size,
            }
            for p in sorted(candidate.iterdir())
        }
        manifest = {
            "version": VERSION,
            "progression_version": facts.quality["progression_version"],
            "native_action_version": facts.quality["native_action_version"],
            "inputs": content_key,
            "code_sha": revision,
            "files": files,
            "writer": {
                "pyarrow": pa.__version__,
                "compression": "zstd",
                "version": "2.6",
                "use_dictionary": False,
                "write_statistics": True,
            },
            "source_manifest_sha256": meta["source_manifest_sha256"],
            "score_manifest_sha256": meta["score_manifest_sha256"],
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "rights": "local noncommercial research only; no redistribution",
        }
        if fingerprint(config) != content_key:
            raise ValueError("Input tree changed during possession verification")
        if target.exists() or target.is_symlink():
            if target.is_symlink() or {p.name for p in target.iterdir()} != set(files) | {
                "manifest.json"
            }:
                raise ValueError("Invalid possession bundle members")
            if any(p.is_symlink() or not p.is_file() for p in target.iterdir()):
                raise ValueError("Invalid/symlink possession member")
            for name in files:
                if (target / name).read_bytes() != (candidate / name).read_bytes():
                    raise ValueError("Possession artifact differs from recomputed source facts")
            prior = json.loads((target / "manifest.json").read_bytes())
            stamp = prior["generated_at_utc"]
            if datetime.fromisoformat(stamp).utcoffset() != UTC.utcoffset(None):
                raise ValueError("Expected UTC generation time")
            manifest["generated_at_utc"] = stamp
            if prior != manifest:
                raise ValueError("Possession manifest mismatch")
            return target
        (candidate / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        candidate.rename(target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/interim/possessions"))
    parser.add_argument("--pipeline-revision", required=True)
    args = parser.parse_args()
    folder = prepare(json.loads(args.config.read_bytes()), args.output, args.pipeline_revision)
    print(json.dumps({"possessions": str(folder.resolve()), "status": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
