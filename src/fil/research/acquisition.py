"""Exact owner-approved StatsBomb scope; immutable acquisition, no generic URL fetcher."""

import hashlib
import json
import re
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REVISION = "4b73468fc5b0f1950f9f66fada70ad3a4f9327cb"
PROPOSAL_SHA256 = "bd9357a8bf3c87c808477308770f1e798b7f7b1d98f4468c7fc6c56e9ac17787"
VERSION = "fil-approved-worldcup-acquisition-1"


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def scope(proposal: Path) -> dict:
    body = proposal.read_bytes()
    if digest(body) != PROPOSAL_SHA256:
        raise ValueError("Owner-approved file enumeration changed")
    return json.loads(body)


def verify(folder: Path, proposal: Path) -> dict:
    approved = scope(proposal)
    if folder.is_symlink():
        raise ValueError("Symlink source bundle")
    manifest = json.loads((folder / "manifest.json").read_bytes())
    mid = manifest["match_id"]
    files = [r for r in approved["files"] if r["path"].endswith(f"/{mid}.json")]
    if len(files) != 2 or manifest["upstream_revision"] != REVISION:
        raise ValueError("Source outside approved enumeration")
    expected = {"manifest.json"} | {
        Path(r["path"]).name + "." + r["path"].split("/")[1] for r in files
    }
    if {p.name for p in folder.iterdir()} != expected:
        raise ValueError("Unexpected source bundle members")
    if set(manifest["files"]) != {r["path"] for r in files}:
        raise ValueError("Manifest scope mismatch")
    for r in files:
        item = manifest["files"][r["path"]]
        name = Path(r["path"]).name + "." + r["path"].split("/")[1]
        path = folder / name
        if path.is_symlink():
            raise ValueError("Symlink payload")
        body = path.read_bytes()
        git_hash = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
        if (
            len(body) != r["size_bytes"]
            or git_hash != r["upstream_git_blob_sha1"]
            or digest(body) != item["sha256"]
        ):
            raise ValueError("Source byte/hash mismatch")
        if (
            item["source_url"]
            != f"https://raw.githubusercontent.com/hudl/open-data/{REVISION}/{r['path']}"
        ):
            raise ValueError("Source URL identity mismatch")
    if manifest["proposal_sha256"] != PROPOSAL_SHA256:
        raise ValueError("Source approval identity mismatch")
    return manifest


def acquire(
    mid: int,
    root: Path,
    proposal: Path,
    implementation: str,
    *,
    pilot_gate: Path | None = None,
    accepted_gate: Path | None = None,
) -> Path:
    approved = scope(proposal)
    if not re.fullmatch("[0-9a-f]{40}", implementation):
        raise ValueError("Full implementation SHA required")
    pilot = approved["pilot_new_match_ids"]
    if accepted_gate is not None and pilot_gate is not None:
        raise ValueError("Choose a versioned gate; do not mix historical and accepted gates")
    if mid not in pilot and accepted_gate is not None:
        from fil.research.accepted_corpus import verify_gate

        if mid not in approved["expansion_new_match_ids"]:
            raise ValueError("Match outside exact approved expansion")
        verify_gate(accepted_gate, root)
    elif mid not in pilot:
        if mid not in approved["expansion_new_match_ids"] or pilot_gate is None:
            raise ValueError("Expansion requires passing pilot gate")
        gate = json.loads(pilot_gate.read_bytes())
        if (
            gate.get("status") != "PASS"
            or gate.get("proposal_sha256") != PROPOSAL_SHA256
            or set(gate.get("pilot_matches", {})) != {str(i) for i in pilot}
        ):
            raise ValueError("Pilot gate failed or incomplete")
        independent_path = gate.get("independent_verification_path")
        if not independent_path:
            raise ValueError("Independent pilot reconciliation required")
        independent = Path(independent_path)
        if independent.is_symlink() or digest(independent.read_bytes()) != gate.get(
            "independent_verification_sha256"
        ):
            raise ValueError("Independent pilot evidence changed")
        proof = json.loads(independent.read_bytes())
        if (
            proof.get("status") != "PASS"
            or set(proof.get("passed_pilot_ids", [])) != set(pilot)
            or proof.get("pilot_source_manifests")
            != {i: e["source_manifest_sha256"] for i, e in gate["pilot_matches"].items()}
        ):
            raise ValueError("Incomplete independent pilot reconciliation")
        for i, evidence in gate["pilot_matches"].items():
            raw_folder = root / REVISION / i
            verify(raw_folder, proposal)
            if (
                digest((raw_folder / "manifest.json").read_bytes())
                != evidence["source_manifest_sha256"]
            ):
                raise ValueError("Pilot source changed after review")
            report = Path(evidence["quality_report"])
            if (
                digest(report.read_bytes()) != evidence["quality_sha256"]
                or json.loads(report.read_bytes())["material_failures"]
            ):
                raise ValueError("Pilot quality evidence changed or failed")
    files = [r for r in approved["files"] if r["path"].endswith(f"/{mid}.json")]
    if len(files) != 2:
        raise ValueError("Match outside approved files")
    target = root / REVISION / str(mid)
    if target.exists():
        verify(target, proposal)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=target.parent) as tmp:
        stage = Path(tmp) / str(mid)
        stage.mkdir()
        manifest = dict(
            version=VERSION,
            source="statsbomb_open_data",
            match_id=mid,
            upstream_revision=REVISION,
            proposal_sha256=PROPOSAL_SHA256,
            implementation_sha=implementation,
            fetched_at_utc=datetime.now(UTC).isoformat(),
            owner_authorization=(
                "Conditional approval in FIL conversation, 2026-10-22; exact PR14 scope"
            ),
            rights=(
                "local noncommercial research/empirical baselines only; no redistribution, "
                "external AI upload, deployment, xT/VAEP or model publication"
            ),
            files={},
        )
        for r in files:
            url = f"https://raw.githubusercontent.com/hudl/open-data/{REVISION}/{r['path']}"
            with urllib.request.urlopen(url, timeout=60) as response:
                body = response.read(r["size_bytes"] + 1)
            item = dict(
                source_url=url,
                sha256=digest(body),
                size_bytes=len(body),
                upstream_git_blob_sha1=r["upstream_git_blob_sha1"],
            )
            manifest["files"][r["path"]] = item
            (stage / (Path(r["path"]).name + "." + r["path"].split("/")[1])).write_bytes(body)
        (stage / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        verify(stage, proposal)
        stage.rename(target)
    return target
