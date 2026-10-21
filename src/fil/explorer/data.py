"""Verified read-only Explorer inputs, versioned fact tables and immutable preparation."""

import argparse
import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from fil.metrics.score_artifacts import verify_score_artifact
from fil.metrics.shots import METRIC_VERSION, build_shots, cumulative, totals, window_threat


def fingerprint(config: dict) -> str:
    """Content-key all source/derived inputs; never serve a stale cache after byte changes."""
    h = hashlib.sha256()
    for key in ("raw", "canonical", "clock", "score"):
        root = Path(config[key])
        for p in sorted(root.rglob("*")):
            if p.is_symlink():
                raise ValueError("Symlink inputs are not supported")
            if p.is_file():
                h.update(str(p.relative_to(root)).encode())
                h.update(p.read_bytes())
    return h.hexdigest()


def load_match(config: dict) -> tuple[pa.Table, dict]:
    raw, canonical, clock, score = (Path(config[k]) for k in ("raw", "canonical", "clock", "score"))
    verified = verify_score_artifact(raw, canonical, clock, score)
    body = (score / "score_events.parquet").read_bytes()
    if hashlib.sha256(body).hexdigest() != verified["files"]["score_events.parquet"]["sha256"]:
        raise ValueError("Score data changed during load")
    events = pq.ParquetFile(pa.BufferReader(body)).read()
    source_body = (raw / "manifest.json").read_bytes()
    if hashlib.sha256(source_body).hexdigest() != verified["source_manifest_sha256"]:
        raise ValueError("Source manifest changed during load")
    source = json.loads(source_body)
    identity = source["quality"]["identity"]
    # Names, official final score and competition are from audited original source metadata.
    metadata = {
        **identity,
        "home_score": events["score_home_after"][-1].as_py(),
        "away_score": events["score_away_after"][-1].as_py(),
        "source_manifest_sha256": verified["source_manifest_sha256"],
        "source_revision": source["upstream_revision"],
        "score_manifest_sha256": hashlib.sha256((score / "manifest.json").read_bytes()).hexdigest(),
    }
    shots = build_shots(events)
    teams = (identity["home_team_id"], identity["away_team_id"])
    if any(r["team_id"] not in teams for r in shots.to_pylist()):
        raise ValueError("Shot belongs to an unknown official team")
    return events, metadata


def prepare(config: dict, output: Path, revision: str) -> Path:
    events, meta = load_match(config)
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("Expected full code revision")
    if any(
        output.resolve().is_relative_to(Path(config[k]).resolve())
        for k in ("raw", "canonical", "clock", "score")
    ):
        raise ValueError("Output must be outside immutable input bundles")
    shots = build_shots(events)
    teams = (meta["home_team_id"], meta["away_team_id"])
    points = cumulative(shots)
    windows = {str(width): window_threat(events, teams, width * 60000) for width in (5, 10, 15)}
    report = {
        "metric_version": METRIC_VERSION,
        "match": meta,
        "event_rows": events.num_rows,
        "shots": shots.num_rows,
        "shot_coordinate_nulls": {k: shots[k].null_count for k in ("x", "y")},
        "totals": [totals(shots, team) for team in teams],
        "shootout_excluded": sum(
            r["event_type"] == "Shot" and r["period"] == 5 for r in events.to_pylist()
        ),
        "limits": [
            "Provider xG model internals/version unavailable beyond source metadata",
            "Source-native 120x80 shot coordinates; no tracking or attack-direction flip",
            "Window threat is xG sum, not control or pressing efficiency",
        ],
        "canonical_manifest_sha256": events["canonical_manifest_sha256"][0].as_py(),
        "clock_manifest_sha256": events["clock_manifest_sha256"][0].as_py(),
    }
    content_key = fingerprint(config)
    folder = output / content_key / METRIC_VERSION / revision
    writer = dict(
        compression="zstd",
        version="2.6",
        use_dictionary=False,
        write_statistics=True,
        row_group_size=65536,
    )

    window_schema = pa.schema(
        [
            ("team_id", pa.int64()),
            ("shot_count", pa.int64()),
            ("xg", pa.float64()),
            ("non_penalty_xg", pa.float64()),
            ("mean_xg", pa.float64()),
            ("event_ids", pa.list_(pa.field("element", pa.string()))),
            ("metric_version", pa.string()),
            ("period", pa.int64()),
            ("width_ms", pa.int64()),
            ("start_ms", pa.int64()),
            ("end_ms", pa.int64()),
            ("include_terminal", pa.bool_()),
            ("xg_per_minute", pa.float64()),
        ]
    )

    def write(candidate: Path) -> None:
        pq.write_table(shots, candidate / "shots.parquet", **writer)
        point_schema = pa.schema(
            [
                ("event_id", pa.string()),
                ("team_id", pa.int64()),
                ("period", pa.int64()),
                ("provider_index", pa.int64()),
                ("chronological_ms", pa.int64()),
                ("display_clock", pa.string()),
                ("xg", pa.float64()),
                ("cumulative_xg", pa.float64()),
                ("metric_version", pa.string()),
                ("source_manifest_sha256", pa.string()),
            ]
        )
        pq.write_table(
            pa.Table.from_pylist(points, schema=point_schema),
            candidate / "xg_cumulative.parquet",
            **writer,
        )
        pq.write_table(
            pa.Table.from_pylist([r for v in windows.values() for r in v], schema=window_schema),
            candidate / "window_threat.parquet",
            **writer,
        )
        (candidate / "quality.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix=".fil-metrics-") as staging:
        candidate = Path(staging) / "bundle"
        candidate.mkdir()
        write(candidate)
        members = sorted(candidate.iterdir())
        files = {
            p.name: {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "size_bytes": p.stat().st_size,
            }
            for p in members
        }
        manifest = {
            "version": METRIC_VERSION,
            "code_sha": revision,
            "inputs": content_key,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "files": files,
            "source_manifest_sha256": meta["source_manifest_sha256"],
            "score_manifest_sha256": meta["score_manifest_sha256"],
            "pyarrow_version": pa.__version__,
            "writer": writer,
            "rights": "local noncommercial research only; no redistribution",
        }
        if folder.exists() or folder.is_symlink():
            expected = set(files) | {"manifest.json"}
            actual = {p.name for p in folder.iterdir()}
            if folder.is_symlink() or actual not in (expected, expected | {"local-config.json"}):
                raise ValueError("Unexpected metric bundle members")
            if any(p.is_symlink() or not p.is_file() for p in folder.iterdir()):
                raise ValueError("Symlink/invalid metric member")
            for name, entry in files.items():
                if hashlib.sha256((folder / name).read_bytes()).hexdigest() != entry["sha256"]:
                    raise ValueError("Existing metric bundle differs; never repair silently")
            prior = json.loads((folder / "manifest.json").read_bytes())
            stamp = prior["generated_at_utc"]
            if datetime.fromisoformat(stamp).utcoffset() != UTC.utcoffset(None):
                raise ValueError("Expected UTC metric timestamp")
            manifest["generated_at_utc"] = stamp
            if prior != manifest:
                raise ValueError("Metric manifest mismatch")
            return folder
        (candidate / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        candidate.rename(folder)
    return folder


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare verified local Explorer facts/config")
    for name in ("raw", "canonical", "clock", "score"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/interim/explorer"))
    parser.add_argument("--pipeline-revision", required=True)
    args = parser.parse_args()
    config = {k: str(getattr(args, k).resolve()) for k in ("raw", "canonical", "clock", "score")}
    folder = prepare(config, args.output, args.pipeline_revision)
    config["metrics"] = str(folder.resolve())
    path = folder / "local-config.json"
    if not path.exists():
        path.write_text(json.dumps(config, indent=2) + "\n")
    elif json.loads(path.read_bytes()) != config:
        raise ValueError("Existing local config differs")
    print(json.dumps({"config": str(path.resolve()), "metrics": str(folder)}, indent=2))


if __name__ == "__main__":
    main()
