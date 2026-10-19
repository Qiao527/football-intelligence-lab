"""Offline TEST-ONLY records. None of these objects are real match observations."""

import copy
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from fil.ingestion import statsbomb as sb

STAMP = "2026-10-19T00:00:00+00:00"
PIPELINE = "a" * 40


@pytest.fixture(autouse=True)
def prohibit_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unit tests must not contact the network")

    monkeypatch.setattr(sb, "urlopen", forbidden)


def repin(pin: dict, raw: dict[str, bytes]) -> None:
    """Pin test-only bytes so structural validation is tested independently of hashing."""
    pin["files"] = [
        {"path": name, "size_bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        for name, body in raw.items()
    ]


@pytest.fixture
def sample() -> tuple[dict, dict[str, bytes]]:
    identity = {
        "match_id": 1,
        "competition_id": 2,
        "competition_name": "TEST ONLY",
        "season_id": 3,
        "season_name": "TEST SEASON",
        "match_date": "2000-01-01",
        "home_team_id": 4,
        "home_team_name": "TEST HOME",
        "away_team_id": 5,
        "away_team_name": "TEST AWAY",
        "competition_stage": "TEST",
    }
    event = {
        "id": "00000000-0000-4000-8000-000000000001",
        "index": 1,
        "period": 1,
        "timestamp": "00:00:00.000",
        "type": {"id": 1, "name": "TEST"},
        "unknown_provider_field": {"preserve": [None, 17, "verbatim"]},
    }
    objects = {
        "data/competitions.json": [
            {
                "competition_id": 2,
                "season_id": 3,
                "competition_name": "TEST ONLY",
                "season_name": "TEST SEASON",
            }
        ],
        "data/matches/2/3.json": [
            {
                "match_id": 1,
                "match_date": "2000-01-01",
                "competition": {"competition_id": 2, "competition_name": "TEST ONLY"},
                "season": {"season_id": 3, "season_name": "TEST SEASON"},
                "home_team": {"home_team_id": 4, "home_team_name": "TEST HOME"},
                "away_team": {"away_team_id": 5, "away_team_name": "TEST AWAY"},
                "competition_stage": {"name": "TEST"},
            }
        ],
        "data/events/1.json": [event],
        "data/lineups/1.json": [
            {"team_id": 4, "team_name": "TEST HOME", "lineup": [{}]},
            {"team_id": 5, "team_name": "TEST AWAY", "lineup": [{}]},
        ],
    }
    raw = {k: json.dumps(v, indent=3).encode() + b"\n" for k, v in objects.items()}
    raw.update({"README.md": b"TEST ONLY terms", "LICENSE.pdf": b"%PDF-TEST ONLY license stub"})
    pin = {
        "revision": "b" * 40,
        "repository": "https://github.com/hudl/open-data",
        "match": identity,
    }
    repin(pin, raw)
    return pin, raw


def acquire_sample(tmp_path: Path, pin: dict, raw: dict[str, bytes]) -> Path:
    by_url = {sb.source_url(name, pin): body for name, body in raw.items()}
    return sb.acquire(
        tmp_path, PIPELINE, fetch=lambda url, limit: by_url[url], acquired_at=STAMP, pin=pin
    )


def test_manifest_and_original_records(tmp_path: Path, sample: tuple) -> None:
    pin, raw = sample
    before = copy.deepcopy(raw)
    bundle = acquire_sample(tmp_path, pin, raw)
    manifest = sb.verify_bundle(bundle, pin)
    assert raw == before
    for entry in manifest["files"]:
        original = before[entry["path"]]
        assert (bundle / entry["path"]).read_bytes() == original
        assert entry["sha256"] == hashlib.sha256(original).hexdigest()
        assert entry["size_bytes"] == len(original)
        assert pin["revision"] in entry["source_url"]
        assert entry["source_url"] == entry["final_url"]
    assert manifest["quality"]["identity"] == pin["match"]
    assert manifest["quality"]["event_count_raw"] == 1  # TEST ONLY, not a real match count
    assert manifest["acquired_at_utc"] == STAMP
    assert manifest["pipeline_git_sha"] == PIPELINE
    assert manifest["usage"]["redistribution_approved"] is False
    assert manifest["rights_gate_status"] == "PENDING_OWNER_CONFIRMATION"
    assert manifest["normalizer_version"] is None


def test_deterministic_repetition_without_network_or_rewrite(tmp_path: Path, sample: tuple) -> None:
    pin, raw = sample
    bundle = acquire_sample(tmp_path, pin, raw)
    before = {
        str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in bundle.rglob("*") if p.is_file()
    }

    def forbidden(url: str, limit: int) -> bytes:
        raise AssertionError("Cached acquire must be offline")

    assert sb.acquire(tmp_path, "c" * 40, fetch=forbidden, pin=pin) == bundle
    assert before == {
        str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in bundle.rglob("*") if p.is_file()
    }
    assert sb.build_manifest(raw, PIPELINE, STAMP, pin) == sb.build_manifest(
        raw, PIPELINE, STAMP, pin
    )


@pytest.mark.parametrize("body", [b"not json", b"{}", b"[]", b"[null]", b"\xff"])
def test_malformed_events_fail_before_publication(
    tmp_path: Path, sample: tuple, body: bytes
) -> None:
    pin, raw = sample
    raw["data/events/1.json"] = body
    repin(pin, raw)
    with pytest.raises(sb.AcquisitionError):
        acquire_sample(tmp_path, pin, raw)
    assert not list(tmp_path.rglob("manifest.json"))


@pytest.mark.parametrize("change", ["duplicate", "missing", "empty", "invalid", "index", "period"])
def test_invalid_event_identity(sample: tuple, change: str) -> None:
    pin, raw = sample
    rows = json.loads(raw["data/events/1.json"])
    if change == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif change == "missing":
        del rows[0]["id"]
    else:
        key, value = {
            "empty": ("id", ""),
            "invalid": ("id", "not-a-uuid"),
            "index": ("index", True),
            "period": ("period", 9),
        }[change]
        rows[0][key] = value
    raw["data/events/1.json"] = json.dumps(rows).encode()
    repin(pin, raw)
    with pytest.raises(sb.AcquisitionError):
        sb.build_manifest(raw, PIPELINE, STAMP, pin)


@pytest.mark.parametrize("kind", ["hash", "size", "missing"])
def test_changed_or_missing_source(tmp_path: Path, sample: tuple, kind: str) -> None:
    pin, raw = sample
    if kind == "hash":
        raw["README.md"] = raw["README.md"].replace(b"TEST", b"FAIL")
    elif kind == "size":
        raw["README.md"] += b"changed"
    else:
        del raw["README.md"]
    with pytest.raises(sb.AcquisitionError):
        sb.build_manifest(raw, PIPELINE, STAMP, pin)
    assert not list(tmp_path.rglob("manifest.json"))


@pytest.mark.parametrize("kind", ["match", "competition", "lineup", "missing_field"])
def test_cross_record_metadata_checks(sample: tuple, kind: str) -> None:
    pin, raw = sample
    name = {
        "match": "data/matches/2/3.json",
        "missing_field": "data/matches/2/3.json",
        "competition": "data/competitions.json",
        "lineup": "data/lineups/1.json",
    }[kind]
    value = json.loads(raw[name])
    if kind == "match":
        value[0]["home_team"]["home_team_name"] = "WRONG TEST TEAM"
    elif kind == "missing_field":
        del value[0]["season"]
    elif kind == "competition":
        value[0]["competition_name"] = "WRONG TEST COMPETITION"
    else:
        value[0]["team_id"] = 999
    raw[name] = json.dumps(value).encode()
    repin(pin, raw)
    with pytest.raises(sb.AcquisitionError):
        sb.build_manifest(raw, PIPELINE, STAMP, pin)


@pytest.mark.parametrize("target", ["raw", "manifest", "extra", "missing", "symlink"])
def test_corrupted_cache_is_not_replaced(tmp_path: Path, sample: tuple, target: str) -> None:
    pin, raw = sample
    bundle = acquire_sample(tmp_path, pin, raw)
    path = bundle / "README.md"
    if target == "raw":
        path.write_bytes(b"CORRUPTION")
    elif target == "manifest":
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["quality"]["event_count_raw"] = 9000
        manifest_path.write_text(json.dumps(manifest))
    elif target == "extra":
        (bundle / "unexpected").touch()
    else:
        path.unlink()
        if target == "symlink":
            elsewhere = tmp_path / "outside"
            elsewhere.write_bytes(raw["README.md"])
            path.symlink_to(elsewhere)
    snapshot = (bundle / "manifest.json").read_bytes()
    with pytest.raises(sb.AcquisitionError):
        acquire_sample(tmp_path, pin, raw)
    assert (bundle / "manifest.json").read_bytes() == snapshot


def test_unavailable_source_leaves_no_bundle(tmp_path: Path, sample: tuple) -> None:
    pin, _ = sample

    def unavailable(url: str, limit: int) -> bytes:
        raise OSError("TEST ONLY unavailable")

    with pytest.raises(sb.AcquisitionError, match="unavailable"):
        sb.acquire(tmp_path, PIPELINE, fetch=unavailable, pin=pin)
    assert not list(tmp_path.rglob("manifest.json"))


@pytest.mark.parametrize(
    "stamp", ["not-a-date", "2026-10-19T00:00:00", "2026-10-19T01:00:00+01:00"]
)
def test_timestamp_must_be_utc(sample: tuple, stamp: str) -> None:
    pin, raw = sample
    with pytest.raises(sb.AcquisitionError):
        sb.build_manifest(raw, PIPELINE, stamp, pin)


@pytest.mark.parametrize(
    "failure", [URLError("TEST ONLY"), HTTPError("test", 404, "test", {}, None)]
)
def test_http_unavailable_is_explicit(monkeypatch: pytest.MonkeyPatch, failure: Exception) -> None:
    def unavailable(*args: object, **kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(sb, "urlopen", unavailable)
    with pytest.raises(sb.AcquisitionError, match="unavailable"):
        sb.download("https://raw.githubusercontent.com/TEST-ONLY", 5)


@pytest.mark.parametrize("mode", ["oversize", "redirect", "status"])
def test_http_response_limits(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    class Response:
        status = 503 if mode == "status" else 200

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def geturl(self) -> str:
            return "https://wrong.example" if mode == "redirect" else "https://example.test"

        def read(self, size: int) -> bytes:
            return b"TOO-LARGE"[:size]

    monkeypatch.setattr(sb, "urlopen", lambda *a, **kw: Response())
    with pytest.raises(sb.AcquisitionError):
        sb.download("https://example.test", 5)


def test_verify_cli_failure(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as error:
        sb.main(["verify", str(tmp_path / "missing")])
    assert error.value.code == 1


def test_invalid_manifest_json(tmp_path: Path, sample: tuple) -> None:
    pin, raw = sample
    bundle = acquire_sample(tmp_path, pin, raw)
    (bundle / "manifest.json").write_text("not JSON")
    with pytest.raises(sb.AcquisitionError, match="manifest JSON"):
        sb.verify_bundle(bundle, pin)


def test_failed_publish_does_not_leave_partial_bundle(
    tmp_path: Path, sample: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    pin, raw = sample

    def fail_rename(*args: object, **kwargs: object) -> None:
        raise OSError("TEST ONLY publication failure")

    monkeypatch.setattr(Path, "rename", fail_rename)
    with pytest.raises(sb.AcquisitionError, match="nothing overwritten"):
        acquire_sample(tmp_path, pin, raw)
    assert not list(tmp_path.rglob("manifest.json"))
    assert not list(tmp_path.rglob(".fil-acquire-*"))
