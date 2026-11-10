"""Owner-accepted, metric-specific corpus audit and independent pilot gate."""

import json
import math
import re
import tempfile
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

from fil.ingestion.statsbomb_adapter import RECOGNIZED_TYPES, to_canonical
from fil.research.acquisition import PROPOSAL_SHA256, REVISION, digest, scope, verify
from fil.research.eligibility import assess
from fil.research.integrity_review import DOCUMENTS, verify_artifact
from fil.research.pilot import encode, reference
from fil.research.possession_target import label_segments, label_support, possession_weights
from fil.schema import SourceContext

VERSION = "fil-accepted-metric-quality-1"
GATE_VERSION = "fil-accepted-metric-pilot-gate-1"
POLICY_VERSION = "fil-metric-eligibility-proposal-1"
POLICY_ANCHOR = "a6f64008a352689620971de4887cd48a431d43c9"
POLICY_SHA256 = "bda88c4231376c467dd2be90387d5fdae2139d3b121bfd24a8b414f2ebc68561"
PROTOCOL_SHA256 = "5f96b250935483eda4fd01816e5a4e816cef8a00bf0c9f4c7af6fdabe3d7161e"
REQUIRED = ("source_identity", "event_order", "score", "native_spatial")
PROPOSAL = Path("docs/research/statsbomb_corpus_proposal.json")


def supplemental_semantics(raw: list[dict]) -> dict:
    """Pinned spec p14: these context records were absent from the original 8658 recognizer.

    Preserve original canonical warning flags. Do not infer old numeric outcome/card
    mappings from a later documentation version; neither type is a pass/carry cutoff
    or Shot label. Census still reads explicit source card names and stays uncertain.
    """
    reviewed = {"Bad Behaviour": 24, "50/50": 33, "Offside": 8}
    remaining = [
        e["id"]
        for e in raw
        if e["type"]["name"] not in RECOGNIZED_TYPES
        and reviewed.get(e["type"]["name"]) != e["type"]["id"]
    ]
    return dict(
        reviewed_context_type_ids=reviewed,
        unreviewed_event_ids=remaining,
        numeric_attribute_remapping_performed=False,
        canonical_warning_flags_preserved=True,
    )


def policy() -> dict:
    """Bind explicit owner acceptance to unchanged reviewed documents, not a free-form flag."""
    if digest(Path("docs/research/METRIC_ELIGIBILITY.md").read_bytes()) != POLICY_SHA256:
        raise ValueError("Accepted policy file changed")
    if digest(Path("docs/research/PROSPECTIVE_PROTOCOL.md").read_bytes()) != PROTOCOL_SHA256:
        raise ValueError("Frozen study changed")
    scope(PROPOSAL)
    return dict(
        version=POLICY_VERSION,
        anchor=POLICY_ANCHOR,
        file_sha256=POLICY_SHA256,
        acceptance="explicit owner conversation acceptance; limited source-record domains",
        protocol_sha256=PROTOCOL_SHA256,
        revision=REVISION,
        approved_enumeration_sha256=PROPOSAL_SHA256,
    )


def write_bundle(stage: Path, folder: Path) -> Path:
    """Atomically preserve immutable artifacts; changed outputs are never overwritten."""
    if folder.exists():
        verify_artifact(folder)
        if {p.name for p in folder.iterdir()} != {p.name for p in stage.iterdir()} or any(
            (folder / p.name).read_bytes() != p.read_bytes() for p in stage.iterdir()
        ):
            raise ValueError("Immutable accepted-corpus artifact changed")
    else:
        stage.rename(folder)
    return folder


def audit_match(rawroot: Path, mid: int, original: Path, output: Path, implementation: str) -> Path:
    """Canonicalize all records; gate only named supported source-record domains."""
    accepted = policy()
    documentation = []
    for name, (local, expected) in DOCUMENTS.items():
        doc = Path("data/interim/spatial-docs") / local
        if digest(doc.read_bytes()) != expected:
            raise ValueError("Pinned provider semantics documentation changed")
        documentation.append(dict(upstream_path=name, sha256=expected))
    if not re.fullmatch("[0-9a-f]{40}", implementation):
        raise ValueError("Full implementation SHA required")
    manifest = verify(rawroot / REVISION / str(mid), PROPOSAL)
    matches, ref = reference(original)
    meta = next(m for m in matches if m["match_id"] == mid)
    folder = rawroot / REVISION / str(mid)
    body = (folder / f"{mid}.json.events").read_bytes()
    raw = json.loads(body)
    lineups = json.loads((folder / f"{mid}.json.lineups").read_bytes())
    source_hash = digest((folder / "manifest.json").read_bytes())
    ctx = SourceContext(
        "statsbomb_open_data",
        digest(body),
        REVISION,
        source_hash,
        implementation,
        mid,
        43,
        3,
        f"{mid}.json.events",
    )
    table = to_canonical(raw, ctx)
    roster = [
        dict(team_id=t["team_id"], player_id=p["player_id"]) for t in lineups for p in t["lineup"]
    ]
    keys = {(r["team_id"], r["player_id"]) for r in roster}
    teams = {meta[k][k + "_id"] for k in ("home_team", "away_team")}
    material = []
    if len(lineups) != 2 or {t["team_id"] for t in lineups} != teams or len(keys) != len(roster):
        material.append("lineup_identity_mismatch")
    if len({r["player_id"] for r in roster}) != len(roster):
        material.append("player_rostered_on_opposing_teams")
    unrostered = []
    for e in raw:
        for player in (
            e.get("player"),
            e.get("pass", {}).get("recipient"),
            e.get("substitution", {}).get("replacement"),
        ):
            if player and (e["team"]["id"], player["id"]) not in keys:
                unrostered.append(dict(event_id=e["id"], player_id=player["id"]))
    if unrostered:
        material.append("unrostered_actor_recipient_or_replacement")
    # Required action semantics are reviewed, not inferred from a numeric tag/library licence.
    bad_passes = [
        e["id"]
        for e in raw
        if e["type"]["name"] == "Pass"
        and "outcome" in e["pass"]
        and e["pass"]["outcome"].get("name")
        not in {"Incomplete", "Out", "Pass Offside", "Unknown", "Injury Clearance"}
    ]
    if bad_passes:
        material.append("unsupported_required_pass_semantics")
    eligibility = assess(
        body,
        manifest["files"][f"data/events/{mid}.json"]["sha256"],
        table.to_pylist(),
        meta,
        roster,
        source_manifest_sha256=source_hash,
    )
    material.extend(
        "required_metric_blocked:" + k
        for k in REQUIRED
        if eligibility["eligibility"][k]["support"] == "blocked"
    )
    unknown = dict(
        Counter(e["type"]["name"] for e in raw if e["type"]["name"] not in RECOGNIZED_TYPES)
    )
    semantics = supplemental_semantics(raw)
    if semantics["unreviewed_event_ids"]:
        material.append("unreviewed_provider_event_semantics")
    labels = [] if material else possession_weights(label_segments(raw, source_hash, mid))
    missing_xg = [
        e["id"]
        for e in raw
        if e["type"]["name"] == "Shot" and e["period"] < 5 and e["shot"].get("statsbomb_xg") is None
    ]
    invalid_xg = [
        e["id"]
        for e in raw
        if e["type"]["name"] == "Shot"
        and e["shot"].get("statsbomb_xg") is not None
        and not (math.isfinite(e["shot"]["statsbomb_xg"]) and 0 <= e["shot"]["statsbomb_xg"] <= 1)
    ]
    for row in labels:
        if set(row["later_shot_event_ids"]) & set(invalid_xg):
            row["complete_later_shot_xg_sum"] = None
            row["chance_evidence_exclusion_reasons"] = ["invalid_source_xg"]
    report = dict(
        version=VERSION,
        implementation_sha=implementation,
        policy=accepted,
        match_id=mid,
        source_manifest_sha256=source_hash,
        raw_manifest_path=str((folder / "manifest.json").resolve()),
        raw_count=len(raw),
        canonical_count=table.num_rows,
        reference=ref,
        reference_raw_path=str(original.resolve()),
        original_match_metadata=meta,
        roster=roster,
        unrostered=unrostered,
        unsupported_pass_event_ids=bad_passes,
        unknown_types=unknown,
        supplemental_semantics_review=semantics,
        semantics_documentation=documentation,
        canonical_null_counts={name: table[name].null_count for name in table.column_names},
        source_xg_quality=dict(
            support="blocked"
            if invalid_xg
            else "conditionally_supported"
            if missing_xg
            else "fully_supported",
            missing_event_ids=missing_xg,
            invalid_event_ids=invalid_xg,
            physical_chance_quality_certified=False,
        ),
        metric_eligibility=eligibility["eligibility"],
        label_support=label_support(labels),
        label_exclusion_counts=dict(
            Counter(reason for r in labels for reason in r["unresolved_reasons"])
        ),
        material_failures=sorted(set(material)),
        status="BLOCKED" if material else "PASS",
        official_minutes=None,
        per90_eligible=False,
        physical_timing_certified=False,
    )
    target = output / source_hash / VERSION / implementation
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=target.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        pq.write_table(table, stage / "canonical.parquet", compression="zstd")
        (stage / "quality.json").write_text(encode(report))
        (stage / "labels.json").write_text(encode(labels))
        (stage / "manifest.json").write_text(
            encode(
                dict(
                    version=VERSION,
                    implementation_sha=implementation,
                    policy=accepted,
                    source_manifest_sha256=source_hash,
                    files={p.name: digest(p.read_bytes()) for p in stage.iterdir()},
                )
            )
        )
        write_bundle(stage, target)
    return target


def create_gate(reports: list[Path], independent: Path, output: Path) -> Path:
    """A new gate requires independent proof of all six newly assessed source-record reports."""
    accepted = policy()
    expected = set(scope(PROPOSAL)["pilot_new_match_ids"])
    entries = {}
    for folder in reports:
        verify_artifact(folder)
        q = json.loads((folder / "quality.json").read_bytes())
        if q["match_id"] in entries or q["policy"] != accepted:
            raise ValueError("Duplicate/unaccepted pilot report")
        entries[q["match_id"]] = dict(
            report_path=str(folder.resolve()),
            report_manifest_sha256=digest((folder / "manifest.json").read_bytes()),
            source_manifest_sha256=q["source_manifest_sha256"],
            status=q["status"],
            metric_outcomes={k: v["support"] for k, v in q["metric_eligibility"].items()},
            exclusion_counts=q["label_exclusion_counts"],
            material_failures=q["material_failures"],
        )
    proof = json.loads(independent.read_bytes())
    if (
        set(entries) != expected
        or proof.get("status") != "PASS"
        or proof.get("reports")
        != {str(mid): e["report_manifest_sha256"] for mid, e in entries.items()}
        or proof.get("policy") != accepted
        or proof.get("verifier_sha256")
        != digest(Path("scripts/verify_accepted_corpus.py").read_bytes())
    ):
        raise ValueError("Independent proof must cover exact accepted six pilot reports")
    if any(
        e["status"] != "PASS"
        or e["material_failures"]
        or any(e["metric_outcomes"][k] == "blocked" for k in REQUIRED)
        for e in entries.values()
    ):
        raise ValueError("All relevant pilot domains must pass before expansion")
    gate = dict(
        version=GATE_VERSION,
        policy=accepted,
        status="PASS",
        required_domains=list(REQUIRED),
        proposal_sha256=PROPOSAL_SHA256,
        upstream_revision=REVISION,
        pilot_matches=entries,
        independent_verification_path=str(independent.resolve()),
        independent_verification_sha256=digest(independent.read_bytes()),
        independent_verifier_sha256=digest(Path("scripts/verify_accepted_corpus.py").read_bytes()),
        historical_gate_changed=False,
        exact_time_certified=False,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and output.read_text() != encode(gate):
        raise ValueError("Existing accepted gate cannot be overwritten")
    if not output.exists():
        output.write_text(encode(gate))
    return output


def verify_gate(gate_path: Path, rawroot: Path) -> dict:
    """Recheck every source/report/proof binding before each expansion acquisition."""
    if gate_path.is_symlink():
        raise ValueError("Symlink accepted gate")
    gate = json.loads(gate_path.read_bytes())
    expected = {str(i) for i in scope(PROPOSAL)["pilot_new_match_ids"]}
    if (
        gate.get("version") != GATE_VERSION
        or gate.get("policy") != policy()
        or gate.get("status") != "PASS"
        or gate.get("proposal_sha256") != PROPOSAL_SHA256
        or gate.get("upstream_revision") != REVISION
        or set(gate.get("pilot_matches", {})) != expected
        or gate.get("required_domains") != list(REQUIRED)
    ):
        raise ValueError("Accepted gate identity/status/scope mismatch")
    proof_path = Path(gate["independent_verification_path"])
    if (
        proof_path.is_symlink()
        or digest(proof_path.read_bytes()) != gate["independent_verification_sha256"]
    ):
        raise ValueError("Independent accepted proof changed")
    proof = json.loads(proof_path.read_bytes())
    if (
        proof.get("status") != "PASS"
        or proof.get("policy") != policy()
        or proof.get("reports")
        != {mid: e["report_manifest_sha256"] for mid, e in gate["pilot_matches"].items()}
    ):
        raise ValueError("Incomplete independent accepted proof")
    if proof.get("verifier_sha256") != gate["independent_verifier_sha256"]:
        raise ValueError("Independent verifier identity mismatch")
    if gate["independent_verifier_sha256"] != digest(
        Path("scripts/verify_accepted_corpus.py").read_bytes()
    ):
        raise ValueError("Independent verifier changed since gate creation")
    for mid, e in gate["pilot_matches"].items():
        folder = Path(e["report_path"])
        verify_artifact(folder)
        if digest((folder / "manifest.json").read_bytes()) != e["report_manifest_sha256"]:
            raise ValueError("Accepted report changed")
        verify(rawroot / REVISION / mid, PROPOSAL)
        if (
            digest((rawroot / REVISION / mid / "manifest.json").read_bytes())
            != e["source_manifest_sha256"]
        ):
            raise ValueError("Pilot source changed")
        q = json.loads((folder / "quality.json").read_bytes())
        if (
            e["metric_outcomes"] != {k: v["support"] for k, v in q["metric_eligibility"].items()}
            or e["exclusion_counts"] != q["label_exclusion_counts"]
            or e["source_manifest_sha256"] != q["source_manifest_sha256"]
            or e["status"] != q["status"]
            or e["material_failures"] != q["material_failures"]
        ):
            raise ValueError("Accepted gate metric/exclusion binding changed")
        _, ref = reference(Path(q["reference_raw_path"]))
        if ref != q["reference"]:
            raise ValueError("Reviewed metadata/terms changed")
        if (
            q["status"] != "PASS"
            or q["material_failures"]
            or any(q["metric_eligibility"][k]["support"] == "blocked" for k in REQUIRED)
            or q["policy"] != policy()
        ):
            raise ValueError("Pilot metric decision changed")
    return gate


def main() -> None:
    """Reassess existing pilots; no acquisition and no modification of historical gates."""
    import argparse

    from fil.research.corpus_expansion import immutable_json, independent

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-raw", type=Path, required=True)
    parser.add_argument("--pipeline-revision", required=True)
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/statsbomb-corpus"))
    parser.add_argument("--output", type=Path, default=Path("data/interim/accepted-corpus"))
    a = parser.parse_args()
    reports = [
        audit_match(a.raw_root, mid, a.reference_raw, a.output / "quality", a.pipeline_revision)
        for mid in scope(PROPOSAL)["pilot_new_match_ids"]
    ]
    run = a.output / "runs" / a.pipeline_revision / "pilot"
    listing = run / "reports.json"
    immutable_json(listing, [str(p.resolve()) for p in reports])
    proof = independent(reports, a.reference_raw, run / "pilot")
    gate = create_gate(reports, proof, run / "accepted-gate.json")
    verify_gate(gate, a.raw_root)
    print(encode(dict(gate=str(gate.resolve()), pilot_reports=str(listing.resolve()))))


if __name__ == "__main__":
    main()
