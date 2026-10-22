"""Bounded accepted StatsBomb acquisition; segregate development and held-out payloads."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from fil.research.accepted_corpus import PROPOSAL, audit_match, policy, verify_gate
from fil.research.acquisition import REVISION, acquire, digest
from fil.research.integrity_review import verify_artifact
from fil.research.pilot import encode


def immutable_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = encode(value)
    if path.exists() and path.read_text() != body:
        raise ValueError("Immutable acquisition/evaluation record changed")
    if not path.exists():
        path.write_text(body)


def frozen_plan(review_pointer: Path) -> tuple[dict, str]:
    folder = Path(json.loads(review_pointer.read_bytes())["bundle"])
    manifest = verify_artifact(folder)
    if manifest["implementation_sha"] != policy()["anchor"]:
        raise ValueError("Expected exact PR17 frozen plan anchor")
    path = folder / "future_partitions.json"
    return json.loads(path.read_bytes()), digest(path.read_bytes())


def independent(reports: list[Path], original: Path, prefix: Path) -> Path:
    listing = prefix.with_suffix(".reports.json")
    immutable_json(listing, [str(p.resolve()) for p in reports])
    r = subprocess.run(
        [sys.executable, "scripts/verify_accepted_corpus.py", str(listing), str(original)],
        capture_output=True,
        text=True,
    )
    if r.returncode:
        raise ValueError("Independent corpus verification failed: " + r.stdout + r.stderr)
    result = json.loads(r.stdout)
    if result["status"] != "PASS":
        raise ValueError("Independent reconciliation not passing")
    proof = prefix.with_suffix(".independent.json")
    immutable_json(proof, result)
    return proof


def expand(
    gate: Path,
    review: Path,
    original: Path,
    root: Path,
    output: Path,
    implementation: str,
    phase: str,
    batch_size: int = 6,
    model_freeze: Path | None = None,
    model_proof: Path | None = None,
) -> Path:
    """Acquire only the named partition, validate each source, independently audit each batch."""
    accepted_gate = verify_gate(gate, root)
    plan, plan_hash = frozen_plan(review)
    if phase not in ("development", "test") or not 1 <= batch_size <= 6:
        raise ValueError("Named phase and bounded batch size 1–6 required")
    partitions = ("train", "validation") if phase == "development" else ("test",)
    items = [
        (name, m)
        for name in partitions
        for m in sorted(plan["partitions"][name], key=lambda m: (m["match_date"], m["match_id"]))
    ]
    if phase == "test":
        if model_freeze is None:
            raise ValueError("Freeze development models before opening test payloads")
        verify_artifact(model_freeze)
        freeze = json.loads((model_freeze / "freeze.json").read_bytes())
        if model_proof is None:
            raise ValueError("Independent development-model verification required before test")
        proof = json.loads(model_proof.read_bytes())
        if (
            proof.get("status") != "PASS"
            or proof.get("test_evaluated") is not False
            or proof.get("model_manifest_sha256")
            != digest((model_freeze / "manifest.json").read_bytes())
            or proof.get("verifier_sha256")
            != digest(Path("scripts/verify_corpus_baselines.py").read_bytes())
        ):
            raise ValueError("Independent development-model proof mismatch")
        if (
            freeze.get("plan_sha256") != plan_hash
            or freeze.get("policy") != policy()
            or not freeze.get("frozen_before_test_acquisition")
            or freeze.get("test_match_ids") != sorted(m["match_id"] for _, m in items)
        ):
            raise ValueError("Model freeze does not bind this exact held-out partition")
    run = output / "runs" / implementation / phase
    reports, batches = [], []
    for number, start in enumerate(range(0, len(items), batch_size), 1):
        current = []
        for _name, item in items[start : start + batch_size]:
            mid = item["match_id"]
            acquire(mid, root, PROPOSAL, implementation, accepted_gate=gate)
            folder = audit_match(root, mid, original, output / "quality", implementation)
            q = json.loads((folder / "quality.json").read_bytes())
            current.append(folder)
            print(
                f"{phase} batch {number}: {mid} source verified; research={q['status']}", flush=True
            )
        proof = independent(current, original, run / f"batch-{number:02}")
        batches.append(
            dict(
                reports=[str(p.resolve()) for p in current],
                proof=str(proof.resolve()),
                proof_sha256=digest(proof.read_bytes()),
            )
        )
        reports.extend(current)
        immutable_json(run / f"batch-{number:02}.json", batches[-1])
        print(f"{phase} batch {number}: independent verification PASS", flush=True)
    index = run / "index.json"
    immutable_json(
        index,
        dict(
            version="fil-accepted-corpus-expansion-1",
            phase=phase,
            policy=policy(),
            plan_sha256=plan_hash,
            approved_gate_path=str(gate.resolve()),
            approved_gate_sha256=digest(gate.read_bytes()),
            gate_version=accepted_gate["version"],
            batches=batches,
            reports=[str(p.resolve()) for p in reports],
            source_revision=REVISION,
            model_freeze=str(model_freeze.resolve()) if model_freeze else None,
            model_freeze_manifest_sha256=digest((model_freeze / "manifest.json").read_bytes())
            if model_freeze
            else None,
            model_proof_sha256=digest(model_proof.read_bytes()) if model_proof else None,
        ),
    )
    return index


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gate", type=Path, required=True)
    p.add_argument("--frozen-review", type=Path, required=True)
    p.add_argument("--reference-raw", type=Path, required=True)
    p.add_argument("--phase", choices=("development", "test"), required=True)
    p.add_argument("--pipeline-revision", required=True)
    p.add_argument("--model-freeze", type=Path)
    p.add_argument("--model-proof", type=Path)
    p.add_argument("--raw-root", type=Path, default=Path("data/raw/statsbomb-corpus"))
    p.add_argument("--output", type=Path, default=Path("data/interim/accepted-corpus"))
    a = p.parse_args()
    index = expand(
        a.gate,
        a.frozen_review,
        a.reference_raw,
        a.raw_root,
        a.output,
        a.pipeline_revision,
        a.phase,
        model_freeze=a.model_freeze,
        model_proof=a.model_proof,
    )
    print(encode(dict(index=str(index.resolve()))))


if __name__ == "__main__":
    main()
