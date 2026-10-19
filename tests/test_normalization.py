"""Offline TEST-ONLY objects, never real match observations."""

import copy
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from fil.ingestion import normalize as n
from fil.ingestion.statsbomb import AcquisitionError
from fil.ingestion.statsbomb_adapter import to_canonical
from fil.schema import EVENT_SCHEMA, SchemaError, SourceContext, validate_table

PIPELINE = "1" * 40


@pytest.fixture
def events() -> list[dict]:
    return [
        {
            "id": "aaaaaaaa-0000-4000-8000-000000000001",
            "index": 1,
            "period": 1,
            "minute": 47,
            "second": 3,
            "timestamp": "00:47:03.000",
            "type": {"id": 30, "name": "Pass"},
            "team": {"id": 1, "name": "TEST HOME"},
            "player": {"id": 2, "name": "TEST PLAYER"},
            "location": [20, 30],
            "possession": 7,
            "possession_team": {"id": 3, "name": "TEST OTHER"},
            "under_pressure": False,
            "duration": 0,
            "related_events": [],
            "pass": {
                "end_location": [40, 50],
                "recipient": {"id": 4, "name": "TEST RECEIVER"},
                "future_attribute": {"untouched": [True, None, "TEST ONLY"]},
            },
        },
        {
            "id": "aaaaaaaa-0000-4000-8000-000000000002",
            "index": 2,
            "period": 2,
            "minute": 45,
            "second": 0,
            "timestamp": "00:00:00.000",
            "type": {"id": 18, "name": "Half Start"},
        },
        {
            "id": "aaaaaaaa-0000-4000-8000-000000000003",
            "index": 3,
            "period": 2,
            "minute": 45,
            "second": 0,
            "timestamp": "00:00:00.000",
            "type": {"id": 9999, "name": "TEST FUTURE EVENT"},
            "future_nested": {"complete": [1, None, {"test": "保留"}]},
        },
    ]


@pytest.fixture
def context() -> SourceContext:
    return SourceContext(
        "TEST_ONLY", "a" * 64, "b" * 40, "c" * 64, PIPELINE, 1, 2, 3, "data/events/1.json"
    )


def test_all_records_preserved_with_nullable_semantics(
    events: list, context: SourceContext
) -> None:
    original = copy.deepcopy(events)
    table = to_canonical(events, context)
    assert table.schema.equals(EVENT_SCHEMA, check_metadata=True)
    assert table.num_rows == len(events)
    assert events == original
    rows = table.to_pylist()
    assert [json.loads(r["source_record_json"]) for r in rows] == original
    assert rows[0]["team_id"] != rows[0]["possession_team_id"]
    assert rows[0]["pass_outcome"] is None
    assert rows[0]["under_pressure"] is False and rows[0]["duration_s"] == 0.0
    assert rows[0]["related_event_ids"] == [] and rows[1]["related_event_ids"] is None
    assert rows[1]["player_id"] is None and rows[1]["x"] is None
    assert rows[1]["under_pressure"] is None
    assert rows[2]["quality_flags"] == ["unrecognized_event_type"]
    assert rows[0]["x"] == 20.0 and rows[0]["end_x"] == 40.0
    assert "chronological_s" not in table.column_names
    assert "period_elapsed_s" not in table.column_names
    assert [r["provider_minute"] for r in rows] == [47, 45, 45]


def test_duplicate_ids(events: list, context: SourceContext) -> None:
    events[1]["id"] = events[0]["id"].upper()
    with pytest.raises(SchemaError, match="Duplicate"):
        to_canonical(events, context)


@pytest.mark.parametrize("key", ["id", "index", "period", "minute", "second", "timestamp", "type"])
def test_missing_required(events: list, context: SourceContext, key: str) -> None:
    del events[0][key]
    with pytest.raises(SchemaError):
        to_canonical(events, context)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("id", "not-a-uuid"),
        ("index", True),
        ("index", "1"),
        ("index", 1.0),
        ("period", 0),
        ("period", 6),
        ("minute", -1),
        ("second", 60),
        ("second", "2"),
        ("timestamp", "bad"),
        ("timestamp", "00:99:00.000"),
        ("type", []),
        ("team", {"id": "1", "name": "TEST"}),
        ("player", {"id": 1}),
        ("location", []),
        ("location", [1]),
        ("location", [1, None]),
        ("location", [True, 2]),
        ("location", [float("nan"), 1]),
        ("duration", "3"),
        ("under_pressure", 0),
        ("related_events", "not-list"),
        ("related_events", ["invalid-uuid"]),
        ("pass", []),
        ("pass", None),
        ("future_attribute", float("inf")),
    ],
)
def test_malformed(events: list, context: SourceContext, key: str, value: object) -> None:
    events[0][key] = value
    with pytest.raises(SchemaError):
        to_canonical(events, context)


@pytest.mark.parametrize("indexes", [[2, 1, 3], [1, 1, 3]])
def test_no_silent_reordering(events: list, context: SourceContext, indexes: list) -> None:
    for event, index in zip(events, indexes, strict=True):
        event["index"] = index
    with pytest.raises(SchemaError, match="increasing"):
        to_canonical(events, context)


def test_shot_is_source_copy_only(events: list, context: SourceContext) -> None:
    events[0]["type"] = {"id": 16, "name": "Shot"}
    events[0]["shot"] = {
        "statsbomb_xg": 0.123,
        "end_location": [120, 30, 1.5],
        "outcome": {"id": 97, "name": "TEST OUTCOME"},
        "type": {"id": 1, "name": "TEST SHOT TYPE"},
    }
    row = to_canonical(events, context).to_pylist()[0]
    assert row["shot_xg"] == events[0]["shot"]["statsbomb_xg"]
    assert row["end_z"] == 1.5 and row["shot_outcome"] == "TEST OUTCOME"
    assert row["pass_outcome"] is None
    assert json.loads(row["source_record_json"]) == events[0]
    del events[0]["shot"]["statsbomb_xg"]
    assert to_canonical(events, context)["shot_xg"].to_pylist()[0] is None


def test_schema_validation(events: list, context: SourceContext) -> None:
    table = to_canonical(events, context)
    with pytest.raises(SchemaError, match="schema"):
        validate_table(table.drop(["event_id"]))
    rows = table.to_pylist()
    rows[0]["source"] = None
    with pytest.raises(SchemaError, match="Null required"):
        validate_table(pa.Table.from_pylist(rows, schema=EVENT_SCHEMA))


@pytest.fixture
def raw_bundle(tmp_path: Path, events: list, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Simulate FIL-002's verified boundary with TEST-ONLY data; no live network."""
    root = tmp_path / "raw"
    path = root / "data/events/1.json"
    path.parent.mkdir(parents=True)
    body = (json.dumps(events, indent=3) + "\n").encode()
    path.write_bytes(body)
    manifest = {
        "source": "TEST_ONLY",
        "upstream_revision": "b" * 40,
        "files": [
            {
                "path": "data/events/1.json",
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
            }
        ],
        "quality": {
            "identity": {"match_id": 1, "competition_id": 2, "season_id": 3},
            "event_count_raw": len(events),
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(n, "verify_source_bundle", lambda bundle: copy.deepcopy(manifest))
    return root


def test_rebuild_idempotence_and_full_lineage(raw_bundle: Path, tmp_path: Path) -> None:
    snapshot = {str(p): p.read_bytes() for p in raw_bundle.rglob("*") if p.is_file()}
    dataset = n.build_dataset(raw_bundle, tmp_path / "first", PIPELINE)
    first = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in dataset.iterdir()}
    assert n.build_dataset(raw_bundle, tmp_path / "first", PIPELINE) == dataset
    assert first == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in dataset.iterdir()}
    second = n.build_dataset(raw_bundle, tmp_path / "second", PIPELINE)
    assert (dataset / "events.parquet").read_bytes() == (second / "events.parquet").read_bytes()
    assert (dataset / "quality.json").read_bytes() == (second / "quality.json").read_bytes()
    rows = pq.ParquetFile(dataset / "events.parquet").read().to_pylist()
    originals = json.loads((raw_bundle / "data/events/1.json").read_bytes())
    for row, original in zip(rows, originals, strict=True):
        assert n.lookup_event(raw_bundle, dataset, row["event_id"]) == original
        assert (
            row["source_manifest_sha256"]
            == hashlib.sha256((raw_bundle / "manifest.json").read_bytes()).hexdigest()
        )
    report = json.loads((dataset / "quality.json").read_bytes())
    assert report["raw_count"] == report["processed_count"] == len(originals)
    assert report["excluded_count"] == 0 and report["exclusions"] == []
    assert report["unrecognized_type_count"] == 1 and report["null_counts"]["player_id"] == 2
    assert snapshot == {str(p): p.read_bytes() for p in raw_bundle.rglob("*") if p.is_file()}


@pytest.mark.parametrize("kind", ["report", "manifest", "parquet", "extra", "missing", "symlink"])
def test_corruption_not_replaced(raw_bundle: Path, tmp_path: Path, kind: str) -> None:
    dataset = n.build_dataset(raw_bundle, tmp_path / "output", PIPELINE)
    if kind == "report":
        (dataset / "quality.json").write_text("{}")
    elif kind == "manifest":
        path = dataset / "manifest.json"
        value = json.loads(path.read_bytes())
        value["files"]["events.parquet"]["sha256"] = "bad"
        path.write_text(json.dumps(value))
    elif kind == "parquet":
        table = pq.ParquetFile(dataset / "events.parquet").read()
        rows = table.to_pylist()
        rows[0]["team_name"] = "CORRUPTED TEST TEAM"
        pq.write_table(pa.Table.from_pylist(rows, schema=EVENT_SCHEMA), dataset / "events.parquet")
    elif kind == "extra":
        (dataset / "unexpected").touch()
    elif kind == "missing":
        (dataset / "events.parquet").unlink()
    else:
        path = dataset / "quality.json"
        backup = tmp_path / "report"
        backup.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(backup)
    before = (dataset / "manifest.json").read_bytes()
    with pytest.raises(SchemaError):
        n.build_dataset(raw_bundle, tmp_path / "output", PIPELINE)
    assert (dataset / "manifest.json").read_bytes() == before


def test_changed_raw_fails(raw_bundle: Path, tmp_path: Path) -> None:
    path = raw_bundle / "data/events/1.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(SchemaError, match="changed"):
        n.build_dataset(raw_bundle, tmp_path / "out", PIPELINE)
    assert not (tmp_path / "out").exists()


def test_source_failure_not_bypassed(
    raw_bundle: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(bundle: Path) -> None:
        raise AcquisitionError("TEST_ONLY hash failure")

    monkeypatch.setattr(n, "verify_source_bundle", fail)
    with pytest.raises(AcquisitionError):
        n.build_dataset(raw_bundle, tmp_path / "out", PIPELINE)
    assert not (tmp_path / "out").exists()


def test_lookup_missing_id(raw_bundle: Path, tmp_path: Path) -> None:
    dataset = n.build_dataset(raw_bundle, tmp_path / "out", PIPELINE)
    with pytest.raises(SchemaError, match="not found"):
        n.lookup_event(raw_bundle, dataset, "not-a-source-id")


def test_cli(raw_bundle: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert (
        n.main(
            [
                "build",
                "--raw-bundle",
                str(raw_bundle),
                "--output-root",
                str(tmp_path / "out"),
                "--pipeline-revision",
                PIPELINE,
            ]
        )
        == 0
    )
    dataset = json.loads(capsys.readouterr().out)["dataset"]
    assert n.main(["verify", "--raw-bundle", str(raw_bundle), "--dataset", dataset]) == 0
    capsys.readouterr()
    assert (
        n.main(
            [
                "lookup",
                "--raw-bundle",
                str(raw_bundle),
                "--dataset",
                dataset,
                "--event-id",
                "aaaaaaaa-0000-4000-8000-000000000001",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["id"] == "aaaaaaaa-0000-4000-8000-000000000001"
    with pytest.raises(SystemExit) as exc:
        n.main(["build", "--raw-bundle", str(raw_bundle), "--pipeline-revision", "invalid"])
    assert exc.value.code == 1


@pytest.mark.parametrize("body", [b'{"id": 1, "id": 2}', b'{"x": NaN}'])
def test_ambiguous_json_rejected(body: bytes) -> None:
    with pytest.raises(SchemaError):
        n._json(body)


def test_output_cannot_touch_raw_tree(raw_bundle: Path) -> None:
    before = sorted(str(p.relative_to(raw_bundle)) for p in raw_bundle.rglob("*"))
    with pytest.raises(SchemaError, match="immutable raw"):
        n.build_dataset(raw_bundle, raw_bundle / "derived", PIPELINE)
    assert before == sorted(str(p.relative_to(raw_bundle)) for p in raw_bundle.rglob("*"))


def test_source_manifest_count_must_reconcile(
    raw_bundle: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = raw_bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["quality"]["event_count_raw"] += 1
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(n, "verify_source_bundle", lambda bundle: copy.deepcopy(manifest))
    with pytest.raises(SchemaError, match="count mismatch"):
        n.build_dataset(raw_bundle, tmp_path / "out", PIPELINE)
    assert not (tmp_path / "out").exists()


def test_failed_publish_cleans_staging(
    raw_bundle: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("TEST ONLY failed publication")

    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises(OSError):
        n.build_dataset(raw_bundle, tmp_path / "out", PIPELINE)
    assert not list((tmp_path / "out").rglob("events.parquet"))
    assert not list((tmp_path / "out").rglob(".fil-normalize-*"))


def test_canonical_primary_key_is_independently_validated(
    events: list, context: SourceContext
) -> None:
    rows = to_canonical(events, context).to_pylist()
    rows[1]["event_id"] = rows[0]["event_id"]
    with pytest.raises(SchemaError, match="Duplicate canonical"):
        validate_table(pa.Table.from_pylist(rows, schema=EVENT_SCHEMA))
