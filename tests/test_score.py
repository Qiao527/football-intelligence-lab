"""TEST-ONLY football edge cases. No fixture is an observed match result."""

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pyarrow as pa
import pytest

from fil.ingestion import normalize
from fil.ingestion.statsbomb_adapter import to_canonical
from fil.ingestion.statsbomb_score import official_score, scoring_signals
from fil.metrics import score_artifacts as art
from fil.metrics.score import (
    DECISION_SCHEMA,
    SCORE_SCHEMA,
    OfficialScore,
    ScoreError,
    reconstruct_score,
)
from fil.metrics.score_cli import main
from fil.schema import SourceContext
from fil.time.artifacts import build_clock_artifact
from fil.time.clock import CLOCK_SCHEMA, derive_clock

REV = "a" * 40
DIGEST = "b" * 64


def event(
    index: int,
    period: int,
    stamp: str,
    kind: str,
    team: int = 1,
    outcome: str = "Goal",
    penalty: bool = False,
) -> dict:
    e = {
        "id": str(UUID(int=index)),
        "index": index,
        "period": period,
        "timestamp": stamp if "." in stamp else stamp + ".000",
        "minute": 0,
        "second": 0,
        "type": {"id": 1, "name": kind},
        "team": {"id": team, "name": "TEST ONLY"},
        "possession_team": {"id": 3 - team, "name": "TEST OTHER"},
        "player": {"id": 10 + team, "name": "TEST ONLY"},
        "test_only": True,
    }
    if kind == "Shot":
        e["shot"] = {
            "outcome": {"id": 1, "name": outcome},
            "type": {"id": 1, "name": "Penalty" if penalty else "Open Play"},
        }
    return e


def clock(events: list[dict]) -> pa.Table:
    ctx = SourceContext(
        "TEST_ONLY", "c" * 64, "d" * 40, "e" * 64, REV, 1, 2, 3, "data/events/1.json"
    )
    return derive_clock(to_canonical(events, ctx), REV, DIGEST)[0]


def run(events: list[dict], home: int, away: int) -> tuple:
    return reconstruct_score(
        clock(events), scoring_signals(events), OfficialScore(1, 1, 2, home, away), REV, DIGEST
    )


@pytest.fixture
def events() -> list[dict]:
    e = [
        event(1, 1, "00:00:00", "Half Start"),
        event(2, 1, "00:47:00", "Own Goal For", 1),
        event(3, 1, "00:47:00", "Own Goal Against", 2),
        event(4, 1, "00:47:00", "Half End"),
        event(5, 2, "00:00:00", "Half Start"),
        event(6, 2, "00:00:00", "Shot", 2),
        event(7, 2, "00:10:00", "Shot", 1, penalty=True),
        event(8, 2, "00:11:00", "Shot", 2, outcome="Saved", penalty=True),
        event(9, 2, "00:50:00", "Half End"),
    ]
    e[1].pop("player")
    e[1]["related_events"] = [e[2]["id"]]
    e[2]["related_events"] = [e[1]["id"]]
    return e


def test_independent_score_sequence_and_lineage(events: list) -> None:
    before = copy.deepcopy(events)
    states, decisions, qa = run(events, 2, 1)
    assert states.schema.equals(SCORE_SCHEMA, check_metadata=True)
    assert decisions.schema.equals(DECISION_SCHEMA, check_metadata=True)
    rows = states.to_pylist()
    assert [(r["score_home_after"], r["score_away_after"]) for r in rows] == [
        (0, 0),
        (1, 0),
        (1, 0),
        (1, 0),
        (1, 0),
        (1, 1),
        (2, 1),
        (2, 1),
        (2, 1),
    ]
    assert rows[1]["score_home_before"] == 0 and rows[2]["score_home_before"] == 1
    own = decisions.to_pylist()[0]
    assert own["source_event_ids"] == [events[1]["id"], events[2]["id"]]
    assert own["actor_player_id"] == 12 and own["actor_team_id"] == 2
    assert own["beneficiary_team_id"] == 1
    assert rows[1]["display_clock"] == "45+2:00.000"
    assert rows[4]["display_clock"] == "45:00.000"
    assert rows[3]["chronological_ms"] == rows[4]["chronological_ms"]
    assert rows[1]["score_decision_id"] == rows[2]["score_decision_id"]
    assert (
        states.select(CLOCK_SCHEMA.names)
        .replace_schema_metadata(CLOCK_SCHEMA.metadata)
        .equals(clock(events), check_metadata=True)
    )
    assert [json.loads(r["source_record_json"]) for r in rows] == before == events
    assert qa["merged_own_goal_pairs"] == 1 and qa["match_play_penalty_goals"] == 1
    assert qa["shootout_score"] is None and qa["warnings"] == []
    assert qa["scoring_source_records"] == 5 and decisions.num_rows == 4


@pytest.mark.parametrize("mode", ["reverse", "one_way", "for_only", "against_only"])
def test_own_goal_representation_forms(events: list, mode: str) -> None:
    if mode == "reverse":
        a, b = events[1], events[2]
        for k in ("type", "team", "player"):
            av, bv = a.pop(k, None), b.pop(k, None)
            if av is not None:
                b[k] = av
            if bv is not None:
                a[k] = bv
    elif mode == "one_way":
        events[1].pop("related_events")
    else:
        remove = 2 if mode == "for_only" else 1
        events.pop(remove)
        for e in events:
            e.pop("related_events", None)
    _, decisions, qa = run(events, 2, 1)
    own = decisions.to_pylist()[0]
    assert own["beneficiary_team_id"] == 1
    assert own["actor_player_id"] == (None if mode == "for_only" else 12)
    assert bool(qa["warnings"]) == (mode in {"for_only", "against_only"})


@pytest.mark.parametrize(
    "mode",
    ["unlinked", "same_team", "different_time", "self", "missing_link", "three", "shot_link"],
)
def test_ambiguous_own_goals_fail(events: list, mode: str) -> None:
    if mode == "unlinked":
        events[1].pop("related_events")
        events[2].pop("related_events")
    elif mode == "same_team":
        events[2]["team"]["id"] = 1
    elif mode == "different_time":
        events[2]["timestamp"] = "00:47:00.001"
        events[3]["timestamp"] = "00:47:00.001"
    elif mode == "self":
        events[1]["related_events"].append(events[1]["id"])
    elif mode == "missing_link":
        events[1]["related_events"].append(str(UUID(int=999)))
    elif mode == "three":
        events.insert(3, event(10, 1, "00:47:00", "Own Goal For"))
        events[1]["related_events"].append(events[3]["id"])
        for i, e in enumerate(events, 1):
            e["index"] = i
    else:
        events[1]["related_events"].append(events[5]["id"])
    with pytest.raises(ScoreError):
        run(events, 2, 1)


def test_same_time_unrelated_normal_goals_are_not_deduplicated(events: list) -> None:
    events[1]["type"]["name"] = events[2]["type"]["name"] = "Shot"
    for e in events[1:3]:
        e.pop("related_events")
        e["shot"] = {"type": {"id": 1, "name": "Open Play"}, "outcome": {"id": 1, "name": "Goal"}}
    _, decisions, qa = run(events, 2, 2)
    assert decisions.num_rows == 5 and qa["merged_own_goal_pairs"] == 0


def test_goalkeeper_duplicate_representation_does_not_score(events: list) -> None:
    events.insert(7, event(10, 2, "00:10:00", "Goal Keeper", 2))
    events[7]["goalkeeper"] = {"type": {"id": 1, "name": "Penalty Conceded"}}
    events[6]["related_events"] = [events[7]["id"]]
    for i, e in enumerate(events, 1):
        e["index"] = i
    states, _, qa = run(events, 2, 1)
    assert qa["match_play_goals"] == 3
    assert states.to_pylist()[7]["score_decision_id"] is None


@pytest.mark.parametrize("extra", [False, True])
def test_extra_time_penalties_and_shootout_separate(events: list, extra: bool) -> None:
    if extra:
        events.extend(
            [
                event(10, 3, "00:00:00", "Half Start"),
                event(11, 3, "00:16:00", "Shot", 2, penalty=True),
                event(12, 3, "00:16:00", "Half End"),
                event(13, 4, "00:00:00", "Half Start"),
                event(14, 4, "00:15:00", "Half End"),
            ]
        )
    start = len(events) + 1
    events.extend(
        [
            event(start, 5, "00:00:00", "Shot", 1, penalty=True),
            event(start + 1, 5, "00:00:00", "Shot", 2, "Saved", True),
            event(start + 2, 5, "00:00:01", "Shot", 2, penalty=True),
        ]
    )
    states, decisions, qa = run(events, 2, 2 if extra else 1)
    assert qa["shootout_score"] == [1, 1]
    assert qa["match_play_goals"] == (4 if extra else 3)
    assert qa["match_play_penalty_goals"] == (2 if extra else 1)
    last = states.to_pylist()[-1]
    assert last["chronological_ms"] is None
    assert last["score_home_after"] == 2 and last["shootout_home_after"] == 1
    assert len([r for r in decisions.to_pylist() if r["domain"] == "shootout"]) == 3


def test_nonpenalty_or_own_goal_in_shootout_rejected(events: list) -> None:
    for kind in ("Shot", "Own Goal For"):
        with pytest.raises(ScoreError):
            run([*events, event(10, 5, "00:00:00", kind)], 2, 1)


@pytest.mark.parametrize(
    "change", ["shot", "outcome", "type", "unknown_outcome", "unknown_type", "team", "bad_links"]
)
def test_bad_scoring_source_never_infers_goals(events: list, change: str) -> None:
    e = events[5]
    if change in {"outcome", "type"}:
        e["shot"].pop(change)
    elif change in {"shot", "team"}:
        e.pop(change)
    elif change == "bad_links":
        e["related_events"] = None
    else:
        e["shot"]["outcome" if change == "unknown_outcome" else "type"]["name"] = "TEST FUTURE"
    with pytest.raises(ScoreError):
        scoring_signals(events)


@pytest.mark.parametrize(
    "field,value",
    [
        ("match_id", 0),
        ("home_score", None),
        ("away_score", -1),
        ("home_score", True),
        ("home_team_id", 2),
    ],
)
def test_invalid_official_metadata(field: str, value: object) -> None:
    kwargs = dict(match_id=1, home_team_id=1, away_team_id=2, home_score=2, away_score=1)
    kwargs[field] = value
    with pytest.raises(ScoreError):
        OfficialScore(**kwargs)


def test_official_record_selection() -> None:
    m = {
        "match_id": 1,
        "home_team": {"home_team_id": 1},
        "away_team": {"away_team_id": 2},
        "home_score": 2,
        "away_score": 1,
    }
    assert official_score([m], 1) == OfficialScore(1, 1, 2, 2, 1)
    for records in ([], [m, m], [{}], [{"match_id": 1}]):
        with pytest.raises(ScoreError):
            official_score(records, 1)


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "duplicate_signal",
        "unknown_team",
        "wrong_kind",
        "wrong_player",
        "wrong_match",
        "duplicate_row",
        "unordered",
        "incomplete",
        "no_final_marker",
        "revision",
        "digest",
    ],
)
def test_invalid_reconstruction_inputs(events: list, change: str) -> None:
    table = clock(events)
    signals = scoring_signals(events)
    official = OfficialScore(1, 1, 2, 2, 1)
    revision, digest = REV, DIGEST
    if change == "missing":
        signals = signals[1:]
    elif change == "duplicate_signal":
        signals += signals[:1]
    elif change == "unknown_team":
        signals = (replace(signals[0], team_id=999), *signals[1:])
    elif change == "wrong_kind":
        signals = (replace(signals[0], kind="shot"), *signals[1:])
    elif change == "wrong_player":
        signals = (replace(signals[0], player_id=999), *signals[1:])
    elif change == "wrong_match":
        official = replace(official, match_id=2)
    elif change == "duplicate_row":
        table = pa.concat_tables([table, table.slice(0, 1)])
    elif change == "unordered":
        table = table.take(list(reversed(range(table.num_rows))))
    elif change == "incomplete":
        table = table.slice(0, 4)
        signals = signals[:2]
    elif change == "no_final_marker":
        table = table.slice(0, table.num_rows - 1)
    elif change == "revision":
        revision = "short"
    else:
        digest = "short"
    with pytest.raises(ScoreError):
        reconstruct_score(table, signals, official, revision, digest)


def test_final_mismatch_blocks_publication(events: list) -> None:
    with pytest.raises(ScoreError, match="score_reconciliation_failed"):
        run(events, 3, 1)


@pytest.fixture
def bundles(tmp_path: Path, events: list, monkeypatch: pytest.MonkeyPatch) -> tuple:
    """Offline integration through real normalization/clock code; source-audit boundary mocked."""
    raw = tmp_path / "raw"
    raw.mkdir()
    payloads = {
        "data/events/1.json": events,
        "data/matches/2/3.json": [
            {
                "match_id": 1,
                "home_team": {"home_team_id": 1},
                "away_team": {"away_team_id": 2},
                "home_score": 2,
                "away_score": 1,
            }
        ],
    }
    entries = []
    for name, value in payloads.items():
        path = raw / name
        path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps(value).encode()
        path.write_bytes(body)
        entries.append(
            {
                "path": name,
                "sha256": hashlib.sha256(body).hexdigest(),
                "size_bytes": len(body),
                "source_url": "TEST_ONLY_OFFLINE",
            }
        )
    manifest = {
        "source": "TEST_ONLY",
        "upstream_revision": "d" * 40,
        "files": entries,
        "quality": {
            "event_count_raw": len(events),
            "identity": {"match_id": 1, "competition_id": 2, "season_id": 3},
        },
    }
    (raw / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(normalize, "verify_source_bundle", lambda p: copy.deepcopy(manifest))
    canonical = normalize.build_dataset(raw, tmp_path / "canonical", REV)
    clock_folder = build_clock_artifact(raw, canonical, tmp_path / "clocks", REV)
    return raw, canonical, clock_folder


def test_artifact_idempotent_rebuild_and_immutability(bundles: tuple, tmp_path: Path) -> None:
    snapshot = {
        p: (p.read_bytes(), p.stat().st_mtime_ns)
        for root in bundles
        for p in root.rglob("*")
        if p.is_file()
    }
    folder = art.build_score_artifact(*bundles, tmp_path / "out", REV)
    first = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    assert art.build_score_artifact(*bundles, tmp_path / "out", REV) == folder
    assert first == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    other = art.build_score_artifact(*bundles, tmp_path / "other", REV)
    for name in ("score_events.parquet", "decisions.parquet", "quality.json"):
        assert (folder / name).read_bytes() == (other / name).read_bytes()
    assert snapshot == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in snapshot}
    assert art.verify_score_artifact(*bundles, folder)["row_count"] == 9


@pytest.mark.parametrize(
    "change",
    [
        "qa",
        "state",
        "decision",
        "manifest",
        "missing",
        "extra",
        "symlink",
        "raw",
        "metadata",
        "clock",
    ],
)
def test_artifact_tampering_never_silently_repaired(
    bundles: tuple, tmp_path: Path, change: str
) -> None:
    folder = art.build_score_artifact(*bundles, tmp_path / "out", REV)
    target = {
        "qa": folder / "quality.json",
        "state": folder / "score_events.parquet",
        "decision": folder / "decisions.parquet",
        "manifest": folder / "manifest.json",
        "raw": bundles[0] / "data/events/1.json",
        "metadata": bundles[0] / "data/matches/2/3.json",
        "clock": bundles[2] / "clock_events.parquet",
    }.get(change)
    if target:
        target.write_bytes(target.read_bytes() + b"CORRUPTED TEST DATA")
    elif change == "missing":
        (folder / "decisions.parquet").unlink()
    elif change == "extra":
        (folder / "extra").touch()
    else:
        path = folder / "quality.json"
        path.unlink()
        path.symlink_to(bundles[0] / "manifest.json")
    snapshot = {p: p.read_bytes() for p in folder.iterdir() if p.is_file()}
    with pytest.raises((ValueError, KeyError, pa.ArrowException)):
        art.build_score_artifact(*bundles, tmp_path / "out", REV)
    assert snapshot == {p: p.read_bytes() for p in snapshot}


def test_output_cannot_modify_inputs(bundles: tuple) -> None:
    for root in bundles:
        with pytest.raises(ScoreError, match="immutable"):
            art.build_score_artifact(*bundles, root / "out", REV)


def test_failed_reconciliation_leaves_no_output(
    bundles: tuple, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(art, "official_score", lambda *a: OfficialScore(1, 1, 2, 99, 0))
    with pytest.raises(ScoreError, match="score_reconciliation_failed"):
        art.build_score_artifact(*bundles, tmp_path / "out", REV)
    assert not (tmp_path / "out").exists()


def test_cli_build_verify_and_failure(
    bundles: tuple, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    args = [
        "--raw-bundle",
        str(bundles[0]),
        "--canonical-dataset",
        str(bundles[1]),
        "--clock-dataset",
        str(bundles[2]),
    ]
    assert (
        main(["build", *args, "--pipeline-revision", REV, "--output-root", str(tmp_path / "out")])
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert main(["verify", *args, "--score-dataset", result["score_dataset"]]) == 0
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        main(["verify", *args, "--score-dataset", str(tmp_path / "missing")])
    assert exc.value.code == 1


def test_no_goals_is_verified_zero_not_a_missing_observation(events: list) -> None:
    events = [e for e in events if e["type"]["name"] in {"Half Start", "Half End"}]
    states, decisions, qa = run(events, 0, 0)
    assert decisions.num_rows == 0 and decisions.schema.equals(DECISION_SCHEMA)
    assert qa["match_play_goals"] == 0 and qa["official_score"] == [0, 0]
    assert all(r["score_home_after"] == r["score_away_after"] == 0 for r in states.to_pylist())


def test_signal_input_order_does_not_change_output(events: list) -> None:
    expected = run(events, 2, 1)
    actual = reconstruct_score(
        clock(events),
        tuple(reversed(scoring_signals(events))),
        OfficialScore(1, 1, 2, 2, 1),
        REV,
        DIGEST,
    )
    assert expected[0].equals(actual[0], check_metadata=True)
    assert expected[1].equals(actual[1], check_metadata=True)
    assert expected[2] == actual[2]


def test_missing_scorer_stays_null(events: list) -> None:
    events[5].pop("player")
    _, decisions, qa = run(events, 2, 1)
    assert decisions.to_pylist()[1]["actor_player_id"] is None
    assert qa["null_actor_player_decisions"] == 1


@pytest.mark.parametrize(
    "outcome", ["Blocked", "Off T", "Post", "Saved", "Wayward", "Saved Off Target", "Saved to Post"]
)
def test_penalty_misses_never_award_goals(events: list, outcome: str) -> None:
    events[7]["shot"]["outcome"]["name"] = outcome
    _, decisions, qa = run(events, 2, 1)
    miss = decisions.to_pylist()[-1]
    assert miss["kind"] == "penalty" and miss["scored"] is False
    assert qa["match_play_goals"] == 3


def test_failed_staged_verification_cleans_bundle(
    bundles: tuple, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object) -> None:
        raise ScoreError("TEST ONLY stage verification failure")

    monkeypatch.setattr(art, "verify_score_artifact", fail)
    with pytest.raises(ScoreError, match="stage verification"):
        art.build_score_artifact(*bundles, tmp_path / "out", REV)
    assert not list((tmp_path / "out").rglob("manifest.json"))
    assert not list((tmp_path / "out").rglob(".fil-score-*"))


def test_reverse_lookup_for_every_decision_source_id(bundles: tuple, tmp_path: Path) -> None:
    import pyarrow.parquet as pq

    folder = art.build_score_artifact(*bundles, tmp_path / "out", REV)
    originals = {e["id"]: e for e in json.loads((bundles[0] / "data/events/1.json").read_bytes())}
    states = {
        r["event_id"]: r for r in pq.ParquetFile(folder / "score_events.parquet").read().to_pylist()
    }
    for decision in pq.ParquetFile(folder / "decisions.parquet").read().to_pylist():
        for source_id in decision["source_event_ids"]:
            assert states[source_id]["score_decision_id"] == decision["decision_id"]
            assert normalize.lookup_event(bundles[0], bundles[1], source_id) == originals[source_id]


@pytest.mark.parametrize(
    "member,column,value",
    [
        ("score_events.parquet", "score_home_after", 999),
        ("decisions.parquet", "beneficiary_team_id", 999),
    ],
)
def test_structurally_valid_parquet_tamper_is_detected(
    bundles: tuple, tmp_path: Path, member: str, column: str, value: int
) -> None:
    import pyarrow.parquet as pq

    folder = art.build_score_artifact(*bundles, tmp_path / "out", REV)
    table = pq.ParquetFile(folder / member).read()
    rows = table.to_pylist()
    rows[0][column] = value
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), folder / member)
    # Even updating the manifest digest cannot make a recomputed semantic mismatch valid.
    manifest = json.loads((folder / "manifest.json").read_bytes())
    manifest["files"][member] = {
        "sha256": hashlib.sha256((folder / member).read_bytes()).hexdigest(),
        "size_bytes": (folder / member).stat().st_size,
    }
    (folder / "manifest.json").write_bytes(art._json(manifest))
    with pytest.raises(ScoreError, match="Recomputed score table differs"):
        art.verify_score_artifact(*bundles, folder)
