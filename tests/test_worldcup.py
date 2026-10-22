"""TEST_ONLY gating, immutability and real-baseline lineage contracts."""

import hashlib
import io
import json
from pathlib import Path

import pyarrow as pa
import pytest

from fil.research import acquisition as acq
from fil.research.baselines import examples, run
from fil.time.clock import ClockError, derive_clock
from tests.test_clock import canonical


def test_approved_enumeration_and_expansion_gate_fail_before_network(tmp_path):
    proposal = Path("docs/research/statsbomb_corpus_proposal.json")
    assert len(acq.scope(proposal)["files"]) == 126
    with pytest.raises(ValueError, match="Expansion"):
        acq.acquire(8654, tmp_path, proposal, "a" * 40)
    with pytest.raises(ValueError, match="Expansion"):
        acq.acquire(999999, tmp_path, proposal, "a" * 40)
    altered = tmp_path / "proposal.json"
    altered.write_bytes(proposal.read_bytes() + b" ")
    with pytest.raises(ValueError, match="enumeration changed"):
        acq.scope(altered)


def test_testonly_download_rebuild_is_immutable_and_corruption_never_repaired(
    tmp_path, monkeypatch
):
    body = b'[{"TEST_ONLY":true}]'
    blob = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
    proposal = dict(
        pilot_new_match_ids=[1],
        expansion_new_match_ids=[],
        files=[
            dict(path=f"data/{kind}/1.json", size_bytes=len(body), upstream_git_blob_sha1=blob)
            for kind in ("events", "lineups")
        ],
    )
    monkeypatch.setattr(acq, "scope", lambda _: proposal)
    calls = []

    def fetch(url, timeout):
        calls.append(url)
        return io.BytesIO(body)

    monkeypatch.setattr(acq.urllib.request, "urlopen", fetch)
    target = acq.acquire(1, tmp_path, tmp_path / "TEST_ONLY", "a" * 40)
    assert len(calls) == 2
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}
    assert acq.acquire(1, tmp_path, tmp_path / "TEST_ONLY", "a" * 40) == target
    assert len(calls) == 2 and before == {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()
    }
    (target / "1.json.events").write_bytes(b"TEST_ONLY_CORRUPT")
    with pytest.raises(ValueError, match="byte/hash"):
        acq.acquire(1, tmp_path, tmp_path / "TEST_ONLY", "a" * 40)
    assert len(calls) == 2


def test_conflicting_team_half_end_evidence_still_fails_closed():
    table = canonical(
        [
            (1, "00:00:00.000", "Half Start"),
            (1, "00:46:10.433", "Half End"),
            (1, "00:46:10.540", "Half End"),
        ]
    )
    with pytest.raises(ClockError, match="conflicting Half End"):
        derive_clock(table, "a" * 40, "b" * 64)


def fixture():
    rows = [
        dict(
            event_id=f"TEST-{i}",
            match_id=1,
            provider_index=i,
            period=1,
            possession_id=1,
            team_id=20,
            possession_team_id=20,
            event_type="Shot" if i == 6 else "Pass",
            x=30.0,
            y=40.0,
            end_x=50.0,
            end_y=60.0,
            score_home_before=1,
            score_away_before=0,
            period_elapsed_ms=i * 1000,
            source_manifest_sha256="e" * 64,
        )
        for i in range(1, 7)
    ]
    window = dict(
        match_id=1,
        cutoff_event_id="TEST-1",
        feature_event_ids=["TEST-1"],
        outcome_event_ids=[f"TEST-{i}" for i in range(2, 7)],
        outcome=1,
    )
    return rows, dict(forecast_windows=[window])


def test_features_are_owner_relative_and_missing_geometry_is_not_zero():
    rows, p = fixture()
    r = examples(pa.Table.from_pylist(rows), p, home_team_id=10)[0]
    assert r["features"]["context"] == "period=1:state=trailing"
    assert r["features"]["location"] == "2:3"
    assert r["features"]["gain_15"] == "True"
    rows[0]["x"] = None
    r = examples(pa.Table.from_pylist(rows), p, home_team_id=10)[0]
    assert r["features"]["location"] == "2:3" and r["features"]["forwardness"] is None
    rows[0]["end_x"] = None
    r = examples(pa.Table.from_pylist(rows), p, home_team_id=10)[0]
    assert r["features"]["location"] is None and r["features"]["gain_5"] is None


@pytest.mark.parametrize("bad", ["period", "owner", "order", "label", "feature", "duplicate"])
def test_future_evidence_and_labels_cannot_change_silently(bad):
    rows, p = fixture()
    if bad == "period":
        rows[-1]["period"] = 2
    if bad == "owner":
        rows[-1]["team_id"] = 10
    if bad == "order":
        rows[-1]["provider_index"] = 1
    if bad == "label":
        p["forecast_windows"][0]["outcome"] = 0
    if bad == "duplicate":
        p["forecast_windows"][0]["outcome_event_ids"][0] = "TEST-6"
    if bad == "feature":
        p["forecast_windows"][0]["feature_event_ids"] = ["TEST-6"]
    with pytest.raises(ValueError):
        examples(pa.Table.from_pylist(rows), p, home_team_id=10)


def test_temporal_baseline_is_training_only_and_single_match_has_no_interval():
    from fil.research.baselines import FEATURES

    rows = []
    meta = []
    for mid, day, ys in [
        (1, "2018-07-06", [0, 1]),
        (2, "2018-07-06", [0, 0]),
        (3, "2018-07-07", [0, 1]),
        (4, "2018-07-10", [1, 1]),
    ]:
        meta.append(
            dict(
                source="statsbomb_open_data",
                match_id=mid,
                match_date=day,
                team_ids=[10, 20],
                player_ids=[100],
            )
        )
        rows.extend(
            dict(
                source="statsbomb_open_data",
                match_id=mid,
                event_id=f"TEST-{i}",
                outcome=y,
                features=dict.fromkeys(FEATURES, "TEST_CONTEXT"),
            )
            for i, y in enumerate(ys)
        )
    result, predictions = run(rows, meta)
    for model in result["results"].values():
        assert model["training_prior"] == 0.25
        assert model["comparisons"]["test"]["match_bootstrap_95_interval"] is None
    assert not result["dependence"]["independence_certified"]
    assert {p["baseline"] for p in predictions} == {0.25}
    rows[-1]["match_id"] = 8658
    with pytest.raises(ValueError, match="Development"):
        run(rows, meta)


def test_pilot_gate_requires_complete_independent_reconciliation(tmp_path):
    from fil.research.pilot import pilot_gate

    ids = acq.scope(Path("docs/research/statsbomb_corpus_proposal.json"))["pilot_new_match_ids"]
    reports = []
    for i in ids:
        folder = tmp_path / str(i)
        folder.mkdir()
        (folder / "quality.json").write_text(
            json.dumps(dict(match_id=i, source_manifest_sha256="e" * 64, material_failures=[]))
        )
        reports.append(folder)
    pending = pilot_gate(reports, tmp_path / "pending.json")
    assert pending["status"] == "PENDING_INDEPENDENT_RECONCILIATION"
    proof = tmp_path / "TEST_ONLY-independent.json"
    proof.write_text(
        json.dumps(
            dict(
                status="PASS",
                passed_pilot_ids=ids[:-1],
                pilot_source_manifests={str(i): "e" * 64 for i in ids},
            )
        )
    )
    assert (
        pilot_gate(reports, tmp_path / "incomplete.json", proof)["status"]
        == "PENDING_INDEPENDENT_RECONCILIATION"
    )
    value = json.loads(proof.read_bytes())
    value["passed_pilot_ids"] = ids
    proof.write_text(json.dumps(value))
    gate = tmp_path / "complete.json"
    assert pilot_gate(reports, gate, proof)["status"] == "PASS"
    proof.write_text(proof.read_text() + " ")
    with pytest.raises(ValueError, match="evidence changed"):
        acq.acquire(
            8654,
            tmp_path,
            Path("docs/research/statsbomb_corpus_proposal.json"),
            "a" * 40,
            pilot_gate=gate,
        )
    q = json.loads((reports[-1] / "quality.json").read_bytes())
    q["material_failures"] = ["TEST_ONLY_CLOCK_CONFLICT"]
    (reports[-1] / "quality.json").write_text(json.dumps(q))
    blocked = tmp_path / "blocked.json"
    assert pilot_gate(reports, blocked, proof)["status"] == "BLOCKED"
    with pytest.raises(ValueError, match="failed or incomplete"):
        acq.acquire(
            8654,
            tmp_path,
            Path("docs/research/statsbomb_corpus_proposal.json"),
            "a" * 40,
            pilot_gate=blocked,
        )
