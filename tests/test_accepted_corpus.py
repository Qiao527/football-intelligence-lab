"""TEST_ONLY gate bindings; no network acquisition or physical-time certification."""

import copy
import json
from pathlib import Path

import pytest

from fil.research import accepted_corpus as c
from fil.research.acquisition import acquire, digest
from fil.research.pilot import encode


def fake_evidence(tmp, monkeypatch, blocked=False):
    reports = []
    root = tmp / "raw"
    for mid in (8649, 8650, 8651, 8652, 8655, 8656):
        raw = root / c.REVISION / str(mid)
        raw.mkdir(parents=True)
        (raw / "manifest.json").write_text("TEST_ONLY")
        folder = tmp / str(mid)
        folder.mkdir()
        q = dict(
            match_id=mid,
            policy=c.policy(),
            status="PASS",
            material_failures=[],
            metric_eligibility={k: dict(support="fully_supported") for k in c.REQUIRED},
            label_exclusion_counts={},
            source_manifest_sha256=digest(b"TEST_ONLY"),
            reference_raw_path=str(tmp / "TEST_ONLY_REFERENCE"),
            reference={},
        )
        if blocked and mid == 8656:
            q["metric_eligibility"]["score"]["support"] = "blocked"
        (folder / "quality.json").write_text(encode(q))
        (folder / "manifest.json").write_text(
            encode(dict(files={"quality.json": digest((folder / "quality.json").read_bytes())}))
        )
        reports.append(folder)
    proof = tmp / "independent.json"
    proof.write_text(
        encode(
            dict(
                status="PASS",
                policy=c.policy(),
                reports={str(p.name): digest((p / "manifest.json").read_bytes()) for p in reports},
                verifier_sha256=digest(Path("scripts/verify_accepted_corpus.py").read_bytes()),
            )
        )
    )
    monkeypatch.setattr(c, "verify", lambda *a: {})
    monkeypatch.setattr(c, "reference", lambda *a: ([], {}))
    return reports, proof, root


def test_new_gate_is_distinct_immutable_and_binds_all_six_reports(tmp_path, monkeypatch):
    reports, proof, raw = fake_evidence(tmp_path, monkeypatch)
    gate = c.create_gate(reports, proof, tmp_path / "accepted.json")
    before = gate.read_bytes()
    result = c.verify_gate(gate, raw)
    assert result["version"] == c.GATE_VERSION and result["status"] == "PASS"
    assert not result["historical_gate_changed"] and not result["exact_time_certified"]
    c.create_gate(reports, proof, gate)
    assert gate.read_bytes() == before
    (reports[0] / "quality.json").write_text("CHANGED_TEST_ONLY")
    with pytest.raises(ValueError, match="changed"):
        c.verify_gate(gate, raw)


@pytest.mark.parametrize("bad", ["missing", "metric", "proof", "policy", "raw"])
def test_no_accepted_policy_waiver_of_material_or_identity_failure(tmp_path, monkeypatch, bad):
    reports, proof, raw = fake_evidence(tmp_path, monkeypatch, blocked=bad == "metric")
    if bad == "missing":
        reports.pop()
    if bad == "proof":
        obj = json.loads(proof.read_bytes())
        obj["reports"].pop("8656")
        proof.write_text(encode(obj))
    if bad in ("missing", "metric", "proof"):
        with pytest.raises(ValueError):
            c.create_gate(reports, proof, tmp_path / "gate.json")
        return
    gate = c.create_gate(reports, proof, tmp_path / "gate.json")
    if bad == "policy":
        obj = json.loads(gate.read_bytes())
        obj["policy"]["anchor"] = "0" * 40
        gate.write_text(encode(obj))
    if bad == "raw":
        (raw / c.REVISION / "8656/manifest.json").write_text("CHANGED")
    with pytest.raises(ValueError):
        c.verify_gate(gate, raw)


def test_old_blocked_artifact_cannot_be_promoted_by_new_argument(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(encode(dict(status="BLOCKED")))
    before = copy.deepcopy(path.read_bytes())
    with pytest.raises(ValueError, match="identity/status/scope"):
        acquire(7525, tmp_path / "raw", c.PROPOSAL, "a" * 40, accepted_gate=path)
    assert path.read_bytes() == before and not (tmp_path / "raw").exists()
    with pytest.raises(ValueError, match="mix historical"):
        acquire(7525, tmp_path / "raw", c.PROPOSAL, "a" * 40, accepted_gate=path, pilot_gate=path)


def test_policy_and_study_are_bound_to_accepted_file_identities(monkeypatch):
    assert c.policy()["anchor"] == "a6f64008a352689620971de4887cd48a431d43c9"
    monkeypatch.setattr(c, "POLICY_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="policy file changed"):
        c.policy()
