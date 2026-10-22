"""Approved pilot normalization and explicit failure reports; no failed-gate repair."""

import json
import math
import tempfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import pyarrow.parquet as pq

from fil.ingestion.normalize import _json
from fil.ingestion.statsbomb import verify_bundle
from fil.ingestion.statsbomb_adapter import to_canonical
from fil.ingestion.statsbomb_score import official_score, scoring_signals
from fil.metrics.score import reconstruct_score
from fil.possessions.extract import reconstruct
from fil.research.acquisition import PROPOSAL_SHA256, REVISION, digest, verify
from fil.research.exposure import chronology
from fil.research.process import analyse
from fil.schema import SourceContext
from fil.time.clock import derive_clock

VERSION = "fil-worldcup-pilot-quality-1"


def encode(value: object) -> str:
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"


def reference(raw: Path) -> tuple[list, dict]:
    verified = verify_bundle(raw)
    matches = _json((raw / "data/matches/43/3.json").read_bytes())
    return matches, dict(
        manifest_sha256=digest((raw / "manifest.json").read_bytes()),
        match_metadata_sha256=digest((raw / "data/matches/43/3.json").read_bytes()),
        upstream_revision=verified["upstream_revision"],
    )


def audit(folder: Path, proposal: Path, original: Path, output: Path, implementation: str) -> Path:
    """Preserve canonical events even when strict downstream clocks fail closed."""
    manifest = verify(folder, proposal)
    matches, ref = reference(original)
    mid = manifest["match_id"]
    metadata = [r for r in matches if r["match_id"] == mid]
    if len(metadata) != 1 or ref["upstream_revision"] != REVISION:
        raise ValueError("Original metadata identity mismatch")
    meta = metadata[0]
    raw = _json((folder / f"{mid}.json.events").read_bytes())
    lineups = _json((folder / f"{mid}.json.lineups").read_bytes())
    source_hash = digest((folder / "manifest.json").read_bytes())
    ctx = SourceContext(
        "statsbomb_open_data",
        manifest["files"][f"data/events/{mid}.json"]["sha256"],
        REVISION,
        source_hash,
        implementation,
        mid,
        43,
        3,
        f"{mid}.json.events",
    )
    canonical = to_canonical(raw, ctx)
    teams = {meta["home_team"]["home_team_id"], meta["away_team"]["away_team_id"]}
    roster = [
        dict(
            team_id=t["team_id"],
            player_id=p["player_id"],
            player_name=p["player_name"],
            positions=p.get("positions"),
        )
        for t in lineups
        for p in t["lineup"]
    ]
    keys = {(r["team_id"], r["player_id"]) for r in roster}
    material = []
    if len(lineups) != 2 or {t["team_id"] for t in lineups} != teams or len(keys) != len(roster):
        material.append("lineup_identity_mismatch")
    if len({r["player_id"] for r in roster}) != len(roster):
        material.append("player_rostered_on_opposing_teams")
    if any(
        (e.get("half_end") or {}).get(k)
        for e in raw
        for k in ("early_video_end", "match_suspended")
    ):
        material.append("uncertified_video_or_suspended_boundary")
    missing = []
    for e in raw:
        if (
            e.get("team", {}).get("id") not in teams
            or e.get("possession_team", {}).get("id") not in teams
        ):
            material.append("event_team_identity_mismatch")
        for player in [
            e.get("player"),
            e.get("pass", {}).get("recipient"),
            e.get("substitution", {}).get("replacement"),
        ]:
            if player and (e["team"]["id"], player["id"]) not in keys:
                missing.append(
                    dict(event_id=e["id"], team_id=e["team"]["id"], player_id=player["id"])
                )
    if missing:
        material.append("unrostered_actor_recipient_or_replacement")
    out_of_domain = []
    for e in raw:
        points = [e.get("location")]
        if e["type"]["name"] in ("Pass", "Carry"):
            points.append(e[e["type"]["name"].lower()].get("end_location"))
        if any(p and not (0 <= p[0] <= 120 and 0 <= p[1] <= 80) for p in points):
            out_of_domain.append(e["id"])
    if out_of_domain:
        material.append("out_of_domain_action_geometry")
    report = dict(
        version=VERSION,
        implementation_sha=implementation,
        match_id=mid,
        match_date=meta["match_date"],
        source_manifest_sha256=source_hash,
        reference=ref,
        original_match_metadata=meta,
        roster=roster,
        raw_count=len(raw),
        canonical_count=canonical.num_rows,
        null_counts={k: canonical[k].null_count for k in canonical.column_names},
        unknown_types=dict(
            Counter(
                e["type"]["name"]
                for e, flags in zip(raw, canonical["quality_flags"].to_pylist(), strict=True)
                if flags
            )
        ),
        missing_roster_records=missing,
        out_of_domain_event_ids=out_of_domain,
        period_counts=dict(Counter(e["period"] for e in raw)),
        physical_direction="unknown; native StatsBomb 120x80 convention; no flips",
        half_end_evidence=[
            dict(
                event_id=e["id"],
                period=e["period"],
                timestamp=e["timestamp"],
                team_id=e["team"]["id"],
            )
            for e in raw
            if e["type"]["name"] == "Half End"
        ],
        source_match_play_known_xg_sum=math.fsum(
            e["shot"]["statsbomb_xg"]
            for e in raw
            if e["type"]["name"] == "Shot"
            and e["period"] != 5
            and e["shot"].get("statsbomb_xg") is not None
        ),
        source_shootout_known_xg_sum=math.fsum(
            e["shot"]["statsbomb_xg"]
            for e in raw
            if e["type"]["name"] == "Shot"
            and e["period"] == 5
            and e["shot"].get("statsbomb_xg") is not None
        ),
        missing_shot_xg_event_ids=[
            e["id"]
            for e in raw
            if e["type"]["name"] == "Shot" and e["shot"].get("statsbomb_xg") is None
        ],
    )
    target = output / source_hash / VERSION / implementation
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        pq.write_table(canonical, stage / "canonical.parquet", compression="zstd")
        report["canonical_sha256"] = digest((stage / "canonical.parquet").read_bytes())
        try:
            clock, periods = derive_clock(canonical, implementation, report["canonical_sha256"])
            report["periods"] = [asdict(p) for p in periods]
            if any(p.end_estimated or p.warnings for p in periods):
                material.append("uncertified_or_short_period_boundaries")
            pq.write_table(clock, stage / "clock.parquet", compression="zstd")
            scored, decisions, score_report = reconstruct_score(
                clock,
                scoring_signals(raw),
                official_score(matches, mid),
                implementation,
                digest((stage / "clock.parquet").read_bytes()),
            )
            report["score"] = score_report
            pq.write_table(scored, stage / "events.parquet", compression="zstd")
            pq.write_table(decisions, stage / "score_decisions.parquet", compression="zstd")
            census = chronology(scored, roster)
            report["exposure"] = census
            if census["issues"]:
                material.append("unresolved_lineup_chronology")
            facts = reconstruct(scored, *[meta[k][k + "_id"] for k in ("home_team", "away_team")])
            report["possession_quality"] = facts.quality
            (stage / "process.json").write_text(encode(analyse(facts.actions)))
        except ValueError as error:
            report["downstream_error"] = str(error)
            material.append("clock_score_or_possession_contract_failed")
        report["material_failures"] = sorted(set(material))
        report["status"] = "PASS" if not material else "BLOCKED"
        (stage / "quality.json").write_text(encode(report))
        files = {p.name: digest(p.read_bytes()) for p in stage.iterdir()}
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=implementation,
                    source_manifest_sha256=source_hash,
                    files=files,
                )
            )
        )
        if target.exists():
            if (
                target.is_symlink()
                or {p.name for p in target.iterdir()} != {p.name for p in stage.iterdir()}
                or any(
                    (target / p.name).is_symlink()
                    or (target / p.name).read_bytes() != p.read_bytes()
                    for p in stage.iterdir()
                )
            ):
                raise ValueError("Immutable pilot artifact changed")
        else:
            stage.rename(target)
    return target


def pilot_gate(reports: list[Path], output: Path) -> dict:
    """Bind all six material-quality decisions to immutable raw/report hashes."""
    from fil.research.acquisition import scope

    expected = set(
        scope(Path("docs/research/statsbomb_corpus_proposal.json"))["pilot_new_match_ids"]
    )
    rows = [json.loads((p / "quality.json").read_bytes()) for p in reports]
    if {r["match_id"] for r in rows} != expected or len(rows) != 6:
        raise ValueError("Complete six-match pilot required")
    gate = dict(
        status="PASS" if all(not r["material_failures"] for r in rows) else "BLOCKED",
        proposal_sha256=PROPOSAL_SHA256,
        pilot_matches={
            str(r["match_id"]): dict(
                source_manifest_sha256=r["source_manifest_sha256"],
                quality_report=str((p / "quality.json").resolve()),
                quality_sha256=digest((p / "quality.json").read_bytes()),
                material_failures=r["material_failures"],
            )
            for r, p in zip(rows, reports, strict=True)
        },
    )
    body = encode(gate)
    if output.exists() and output.read_text() != body:
        raise ValueError("Never overwrite an existing pilot gate")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        output.write_text(body)
    return gate
