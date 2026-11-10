"""TEST-ONLY event clocks; no test objects represent observed match results."""

import copy
import json
from pathlib import Path
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from fil.ingestion.statsbomb_adapter import to_canonical
from fil.schema import EVENT_SCHEMA, SourceContext
from fil.time import artifacts as art
from fil.time.__main__ import main
from fil.time.clock import (
    CLOCK_SCHEMA,
    ClockError,
    PeriodRange,
    clock_report,
    derive_clock,
    display_clock,
    parse_period_timestamp,
    partition_period,
    segments_from_chronological,
    select_scope,
    select_segments,
)

REV = "a" * 40
DIGEST = "b" * 64


def canonical(spec: list[tuple[int, str, str]]) -> pa.Table:
    """Build strictly labeled synthetic schema inputs while preserving sequence and timestamps."""
    events = []
    for index, (period, stamp, kind) in enumerate(spec, 1):
        event = {
            "id": str(UUID(int=index)),
            "index": index,
            "period": period,
            "timestamp": stamp,
            "minute": 0,
            "second": 0,
            "type": {"id": 1, "name": kind},
            "test_only": True,
        }
        if kind == "Shot":
            event["shot"] = {"type": {"id": 1, "name": "TEST PENALTY"}, "statsbomb_xg": 0.123}
        events.append(event)
    context = SourceContext(
        "TEST_ONLY", "c" * 64, "d" * 40, "e" * 64, "f" * 40, 1, 2, 3, "data/events/1.json"
    )
    return to_canonical(events, context)


@pytest.fixture
def base() -> pa.Table:
    return canonical(
        [
            (1, "00:00:00.000", "Half Start"),
            (1, "00:44:59.900", "TEST EVENT"),
            (1, "00:45:00.000", "TEST EVENT"),
            (1, "00:47:00.000", "Shot"),
            (1, "00:47:01.000", "Half End"),
            (2, "00:00:00.000", "Half Start"),
            (2, "00:00:00.000", "TEST EVENT"),
            (2, "00:44:59.000", "TEST EVENT"),
            (2, "00:45:00.000", "TEST EVENT"),
            (2, "00:50:00.000", "Shot"),
            (2, "00:50:01.000", "Half End"),
        ]
    )


@pytest.mark.parametrize(
    ("stamp", "ms"),
    [
        ("00:00:00", 0),
        ("00:00:00.001", 1),
        ("00:00:00.1", 100),
        ("00:00:00.12", 120),
        ("00:44:59.9", 2699900),
        ("00:45:00.000", 2700000),
        ("00:47:00.000", 2820000),
        ("01:00:00.000", 3600000),
    ],
)
def test_exact_duration_parser(stamp: str, ms: int) -> None:
    assert parse_period_timestamp(stamp) == ms


@pytest.mark.parametrize(
    "stamp",
    [
        None,
        1,
        -1,
        "-00:00:01.000",
        "00:60:00.000",
        "00:00:60.000",
        "0:00:00.000",
        "00:00:00.0001",
        "00:00:00.",
        "NaN",
        " 00:00:00.000",
        "00:00:00.000Z",
    ],
)
def test_bad_timestamp(stamp: object) -> None:
    with pytest.raises(ClockError):
        parse_period_timestamp(stamp)


@pytest.mark.parametrize(
    ("period", "ms", "label"),
    [
        (1, 2699900, "44:59.900"),
        (1, 2700000, "45:00.000"),
        (1, 2700001, "45+0:00.001"),
        (1, 2820000, "45+2:00.000"),
        (2, 0, "45:00.000"),
        (2, 2699000, "89:59.000"),
        (2, 2700000, "90:00.000"),
        (2, 3000000, "90+5:00.000"),
        (3, 0, "90:00.000"),
        (3, 900000, "105:00.000"),
        (3, 1020000, "105+2:00.000"),
        (4, 0, "105:00.000"),
        (4, 960000, "120+1:00.000"),
        (5, 1, "SO 0:00.001"),
    ],
)
def test_display_clock(period: int, ms: int, label: str) -> None:
    assert display_clock(period, ms) == label


def test_stoppage_h2_and_traceability(base: pa.Table) -> None:
    before = base.to_pylist()
    table, periods = derive_clock(base, REV, DIGEST)
    assert table.schema.equals(CLOCK_SCHEMA, check_metadata=True)
    original = table.select(EVENT_SCHEMA.names).replace_schema_metadata(EVENT_SCHEMA.metadata)
    assert original.equals(base, check_metadata=True)
    assert base.to_pylist() == before
    assert periods[0].duration_ms == 2821000
    assert periods[1].offset_ms == 2821000
    rows = table.to_pylist()
    assert rows[3]["chronological_ms"] < rows[5]["chronological_ms"]
    assert rows[3]["display_clock"] == "45+2:00.000"
    assert rows[5]["display_clock"] == "45:00.000"
    assert rows[4]["chronological_ms"] == rows[5]["chronological_ms"]  # terminal boundary
    h2 = select_segments(table, (PeriodRange(2, 0, 900000),))
    assert h2["period"].to_pylist() == [2, 2]
    assert rows[3]["event_id"] not in h2["event_id"].to_pylist()
    assert table["canonical_manifest_sha256"].to_pylist() == [DIGEST] * len(rows)
    # Source minute was intentionally zero in TEST ONLY inputs; it is not a clock input.
    assert table["provider_minute"].to_pylist() == [0] * len(rows)
    assert rows[5]["period_elapsed_ms"] == 0 and rows[5]["chronological_estimated"] is False


def test_missing_half_end_is_estimated_and_propagated() -> None:
    source = canonical(
        [
            (1, "00:47:00.000", "TEST EVENT"),
            (2, "00:00:00.000", "Half Start"),
            (2, "00:45:00.000", "Half End"),
        ]
    )
    table, periods = derive_clock(source, REV, DIGEST)
    assert periods[0].end_estimated is True
    assert periods[0].duration_ms == 2820000
    assert "half_start_missing" in periods[0].warnings
    assert periods[1].offset_ms == 2820000 and periods[1].offset_estimated is True
    assert table["chronological_estimated"].to_pylist() == [False, True, True]
    assert table["period_end_estimated"].to_pylist() == [True, False, False]


def test_missing_final_marker_does_not_falsify_offset(base: pa.Table) -> None:
    source = base.to_pylist()
    source[-1]["event_type"] = "TEST EVENT"
    table, periods = derive_clock(pa.Table.from_pylist(source, schema=EVENT_SCHEMA), REV, DIGEST)
    assert periods[1].end_estimated and not periods[1].offset_estimated
    assert table["chronological_estimated"].to_pylist() == [False] * table.num_rows


@pytest.mark.parametrize(
    "spec",
    [
        [(2, "00:45:00.000", "Half End")],
        [(1, "00:45:00.000", "Half End"), (3, "00:15:00.000", "Half End")],
        [
            (1, "00:45:00.000", "Half End"),
            (2, "00:45:00.000", "Half End"),
            (1, "00:46:00.000", "TEST EVENT"),
        ],
        [(1, "00:02:00.000", "TEST EVENT"), (1, "00:01:00.000", "Half End")],
        [(1, "00:01:00.000", "Half End"), (1, "00:02:00.000", "TEST EVENT")],
        [(1, "00:00:01.000", "Half Start"), (1, "00:45:00.000", "Half End")],
        [(1, "00:00:00.000", "Half Start")],
        [(1, "00:45:00.000", "Half End"), (1, "00:45:01.000", "Half End")],
        [(1, "00:45:00.000", "Half End"), (5, "00:00:00.000", "Shot")],
    ],
)
def test_inconsistent_periods_fail_closed(spec: list) -> None:
    with pytest.raises(ClockError):
        derive_clock(canonical(spec), REV, DIGEST)


def test_duplicate_matching_markers_are_preserved() -> None:
    source = canonical(
        [
            (1, "00:00:00.000", "Half Start"),
            (1, "00:00:00.000", "Half Start"),
            (1, "00:45:00.000", "Half End"),
            (1, "00:45:00.000", "Half End"),
        ]
    )
    table, info = derive_clock(source, REV, DIGEST)
    assert table.num_rows == 4
    assert len(info[0].half_start_event_ids) == len(info[0].half_end_event_ids) == 2
    assert not info[0].end_estimated


@pytest.fixture
def extended() -> pa.Table:
    spec = []
    for p, end in [
        (1, "00:47:00.000"),
        (2, "00:50:00.000"),
        (3, "00:16:00.000"),
        (4, "00:17:00.000"),
    ]:
        spec.extend(
            [(p, "00:00:00.000", "Half Start"), (p, "00:00:00.000", "Shot"), (p, end, "Half End")]
        )
    spec.extend([(5, "00:00:00.000", "Shot"), (5, "00:00:10.000", "Shot")])
    return derive_clock(canonical(spec), REV, DIGEST)[0]


def test_extra_time_and_shootout_separate(extended: pa.Table) -> None:
    assert set(select_scope(extended)["period"].to_pylist()) == {1, 2, 3, 4}
    assert set(select_scope(extended, "regular")["period"].to_pylist()) == {1, 2}
    assert set(select_scope(extended, "extra")["period"].to_pylist()) == {3, 4}
    shootout = select_scope(extended, "shootout")
    assert shootout.num_rows == 2
    assert shootout["chronological_ms"].to_pylist() == [None, None]
    assert shootout["chronological_s"].to_pylist() == [None, None]
    assert shootout["chronological_estimated"].to_pylist() == [None, None]
    assert shootout["shot_xg"].to_pylist() == [0.123, 0.123]  # source copy only
    assert shootout["is_shootout"].to_pylist() == [True, True]
    assert select_scope(extended)["is_shootout"].to_pylist() == [False] * 12
    rows = extended.to_pylist()
    p3 = next(r for r in rows if r["period"] == 3)
    p4 = next(r for r in rows if r["period"] == 4)
    assert p3["period_offset_ms"] == 2820000 + 3000000
    assert p4["period_offset_ms"] == 2820000 + 3000000 + 960000
    assert p3["display_clock"] == "90:00.000" and p4["display_clock"] == "105:00.000"
    with pytest.raises(ClockError, match="explicitly"):
        select_segments(extended, (PeriodRange(5, 0, 10000, True),))


def test_no_extra_time_required_for_shootout() -> None:
    source = canonical(
        [
            (1, "00:45:00.000", "Half End"),
            (2, "00:45:00.000", "Half End"),
            (5, "00:00:00.000", "Shot"),
        ]
    )
    table, periods = derive_clock(source, REV, DIGEST)
    assert periods[-1].duration_ms == 0 and periods[-1].offset_ms is None
    assert select_scope(table).num_rows == 2
    bins = partition_period(table, 5)
    assert select_segments(table, bins, include_shootout=True).num_rows == 1


@pytest.mark.parametrize("width", [500, 1000, 900000])
def test_half_open_partition_covers_every_event_exactly_once(width: int) -> None:
    source = canonical(
        [
            (1, "00:00:00.000", "Half Start"),
            (1, "00:00:00.999", "TEST EVENT"),
            (1, "00:00:01.000", "TEST EVENT"),
            (1, "00:00:01.000", "TEST EVENT"),
            (1, "00:00:02.000", "Half End"),
        ]
    )
    table, _ = derive_clock(source, REV, DIGEST)
    bins = partition_period(table, 1, width)
    ids = [eid for b in bins for eid in select_segments(table, (b,))["event_id"].to_pylist()]
    assert len(ids) == len(set(ids)) == table.num_rows
    assert set(ids) == set(table["event_id"].to_pylist())
    assert bins[-1].include_terminal and all(not b.include_terminal for b in bins[:-1])
    if width == 1000:
        assert select_segments(table, (bins[0],)).num_rows == 2
        assert select_segments(table, (bins[1],)).num_rows == 3


@pytest.mark.parametrize(
    ("start", "end", "terminal"),
    [
        (0, 2821000, False),
        (2821000, 2821001, False),
        (2820000, 2821001, False),
        (1, 5822000, True),
        (0, 5822000, False),
    ],
)
def test_chronological_conversion_equals_direct_half_open_selection(
    base: pa.Table,
    start: int,
    end: int,
    terminal: bool,
) -> None:
    table, _ = derive_clock(base, REV, DIGEST)
    segments = segments_from_chronological(table, start, end, include_terminal=terminal)
    actual = select_segments(table, segments)["event_id"].to_pylist()
    expected = [
        r["event_id"]
        for r in table.to_pylist()
        if start <= r["chronological_ms"] < end or (terminal and r["chronological_ms"] == end)
    ]
    assert actual == expected


@pytest.mark.parametrize(
    "args",
    [
        (0, 0, 1, False),
        (1, -1, 1, False),
        (1, 1, 0, False),
        (1, 0, 0, False),
        (1, 0.1, 1, False),
        (1, 0, True, False),
        (1, 0, 1, "yes"),
    ],
)
def test_invalid_typed_ranges(args: tuple) -> None:
    with pytest.raises(ClockError):
        PeriodRange(*args)


def test_bad_filter_ranges_and_empty_window(base: pa.Table) -> None:
    table, _ = derive_clock(base, REV, DIGEST)
    for segments in [
        (PeriodRange(3, 0, 1),),
        (PeriodRange(1, 0, 3000000),),
        (PeriodRange(1, 0, 1, True),),
        (PeriodRange(1, 0, 2), PeriodRange(1, 1, 3)),
    ]:
        with pytest.raises(ClockError):
            select_segments(table, segments)
    assert select_segments(table, (PeriodRange(2, 1, 2),)).num_rows == 0
    assert select_segments(table, ()).num_rows == 0
    with pytest.raises(ClockError):
        select_scope(table, "unknown")
    for start, end in [(2, 1), (-1, 10), (0, 99999999)]:
        with pytest.raises(ClockError):
            segments_from_chronological(table, start, end)
    with pytest.raises(ClockError):
        segments_from_chronological(table, 0, 1, include_terminal=True)
    for width in [0, -1, True, 1.5]:
        with pytest.raises(ClockError):
            partition_period(table, 1, width)


@pytest.fixture
def inputs(tmp_path: Path, base: pa.Table, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Simulated FIL-003 verification boundary, with TEST-ONLY canonical records."""
    raw, canonical_dir = tmp_path / "raw", tmp_path / "canonical"
    raw.mkdir()
    canonical_dir.mkdir()
    (raw / "test_only").write_text("TEST ONLY raw preservation check")
    pq.write_table(base, canonical_dir / "events.parquet")
    manifest = {
        "files": {
            "events.parquet": {
                "sha256": art._hash(canonical_dir / "events.parquet"),
                "size_bytes": (canonical_dir / "events.parquet").stat().st_size,
            }
        }
    }
    (canonical_dir / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(art, "verify_dataset", lambda raw, canonical: copy.deepcopy(manifest))
    return raw, canonical_dir


def test_artifact_idempotence_trace_and_regular_parquet(inputs: tuple, tmp_path: Path) -> None:
    raw, canonical_dir = inputs
    before = {str(p): p.read_bytes() for root in inputs for p in root.rglob("*") if p.is_file()}
    folder = art.build_clock_artifact(raw, canonical_dir, tmp_path / "out", REV)
    snapshot = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    art.verify_clock_artifact(raw, canonical_dir, folder)
    assert art.build_clock_artifact(raw, canonical_dir, tmp_path / "out", REV) == folder
    assert snapshot == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    second = art.build_clock_artifact(raw, canonical_dir, tmp_path / "other", REV)
    assert (folder / "clock_events.parquet").read_bytes() == (
        second / "clock_events.parquet"
    ).read_bytes()
    assert (folder / "quality.json").read_bytes() == (second / "quality.json").read_bytes()
    table = pq.ParquetFile(folder / "clock_events.parquet").read()
    assert table.schema.equals(CLOCK_SCHEMA, check_metadata=True)
    assert before == {
        str(p): p.read_bytes() for root in inputs for p in root.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("kind", ["table", "report", "manifest", "missing", "extra", "symlink"])
def test_corruption_not_silently_rebuilt(inputs: tuple, tmp_path: Path, kind: str) -> None:
    raw, canonical_dir = inputs
    folder = art.build_clock_artifact(raw, canonical_dir, tmp_path / "out", REV)
    if kind == "table":
        (folder / "clock_events.parquet").write_bytes(b"TEST CORRUPTION")
    elif kind == "report":
        (folder / "quality.json").write_text("{}")
    elif kind == "manifest":
        p = folder / "manifest.json"
        obj = json.loads(p.read_bytes())
        obj["row_count"] += 1
        p.write_text(json.dumps(obj))
    elif kind == "missing":
        (folder / "quality.json").unlink()
    elif kind == "extra":
        (folder / "unexpected").touch()
    else:
        p = folder / "quality.json"
        p.unlink()
        p.symlink_to(raw / "test_only")
    before = (folder / "manifest.json").read_bytes()
    with pytest.raises((ClockError, pa.ArrowException)):
        art.build_clock_artifact(raw, canonical_dir, tmp_path / "out", REV)
    assert (folder / "manifest.json").read_bytes() == before


def test_inputs_are_never_output_destinations(inputs: tuple) -> None:
    raw, canonical_dir = inputs
    for root in inputs:
        with pytest.raises(ClockError, match="immutable"):
            art.build_clock_artifact(raw, canonical_dir, root / "derived", REV)
        assert not (root / "derived").exists()


def test_cli(inputs: tuple, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    raw, canonical_dir = inputs
    common = ["--raw-bundle", str(raw), "--canonical-dataset", str(canonical_dir)]
    assert (
        main(["build", *common, "--output-root", str(tmp_path / "out"), "--pipeline-revision", REV])
        == 0
    )
    folder = json.loads(capsys.readouterr().out)["clock_dataset"]
    assert main(["verify", *common, "--clock-dataset", folder]) == 0
    assert json.loads(capsys.readouterr().out)["technical_verification"] == "PASS"
    with pytest.raises(SystemExit) as exc:
        main(["build", *common, "--pipeline-revision", "not-a-sha"])
    assert exc.value.code == 1


def test_clock_report_reconciles_scope_and_bins(base: pa.Table) -> None:
    table, periods = derive_clock(base, REV, DIGEST)
    report = clock_report(table, periods)
    assert report["row_count"] == report["scope_counts"]["match_play"] == base.num_rows
    assert (
        sum(sum(counts) for counts in report["fifteen_minute_period_bin_counts"].values())
        == base.num_rows
    )
    assert report["scope_counts"]["shootout"] == 0


def test_string_flags_cannot_enable_shootout_or_terminal(base: pa.Table) -> None:
    table, _ = derive_clock(base, REV, DIGEST)
    with pytest.raises(ClockError):
        select_segments(table, (), include_shootout="false")
    with pytest.raises(ClockError):
        segments_from_chronological(table, 0, 100, include_terminal="false")


@pytest.mark.parametrize(
    ("revision", "digest"), [("bad", DIGEST), (REV, "bad"), ("A" * 40, DIGEST)]
)
def test_implementation_and_provenance_hash_shapes(
    base: pa.Table, revision: str, digest: str
) -> None:
    with pytest.raises(ClockError):
        derive_clock(base, revision, digest)


def test_mixed_match_input_fails(base: pa.Table) -> None:
    rows = base.to_pylist()
    rows[-1]["match_id"] = 999
    with pytest.raises(ClockError, match="one verified"):
        derive_clock(pa.Table.from_pylist(rows, schema=EVENT_SCHEMA), REV, DIGEST)


def test_upstream_verification_must_pass(
    inputs: tuple, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw, canonical_dir = inputs

    def unavailable(*args: object) -> None:
        raise ClockError("TEST ONLY source verification failure")

    monkeypatch.setattr(art, "verify_dataset", unavailable)
    with pytest.raises(ClockError):
        art.build_clock_artifact(raw, canonical_dir, tmp_path / "out", REV)
    assert not (tmp_path / "out").exists()


def test_changed_canonical_bytes_fail_before_output(inputs: tuple, tmp_path: Path) -> None:
    raw, canonical_dir = inputs
    path = canonical_dir / "events.parquet"
    path.write_bytes(path.read_bytes() + b"TEST CORRUPTION")
    with pytest.raises(ClockError, match="changed"):
        art.build_clock_artifact(raw, canonical_dir, tmp_path / "out", REV)
    assert not (tmp_path / "out").exists()


def test_failed_clock_publication_cleans_staging(
    inputs: tuple,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw, canonical_dir = inputs

    def fail(*args: object, **kwargs: object) -> None:
        raise OSError("TEST ONLY publication failure")

    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises(OSError):
        art.build_clock_artifact(raw, canonical_dir, tmp_path / "out", REV)
    assert not list((tmp_path / "out").rglob("clock_events.parquet"))
    assert not list((tmp_path / "out").rglob(".fil-clock-*"))
