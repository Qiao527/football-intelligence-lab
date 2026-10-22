"""TEST_ONLY multi-match, exposure and scientific evaluation failure contracts."""

import copy
import json

import pyarrow as pa
import pytest

from fil.research.corpus import MatchEvidence, assemble
from fil.research.evaluation import (
    baseline_predictions,
    check_feature_lineage,
    chronological_split,
    cluster_interval,
    evaluate,
    fit_baselines,
    negative_control,
    required_clusters,
)
from fil.research.exposure import chronology
from tests import test_tactics
from tests.test_tactics import score_table

source_events = test_tactics.source_events


def example(table, mid=1, name="TEST PLAYER"):
    table = table.set_column(
        table.schema.get_field_index("match_id"),
        "match_id",
        pa.array([mid] * table.num_rows, pa.int64()),
    )
    actors = {
        (r["team_id"], r["player_id"]) for r in table.to_pylist() if r["player_id"] is not None
    }
    roster = [dict(team_id=t, player_id=p, player_name=name, positions=[]) for t, p in actors]
    return MatchEvidence(
        table, dict(match_id=mid, match_date="2000-01-01", source_manifest_sha256="e" * 64), roster
    )


def test_multimatch_identity_not_names_and_no_event_loss(source_events):
    first = example(score_table(source_events))
    second = example(first.events, 2, "TEST ALIAS")
    authorisations = {("statsbomb_open_data", i, "e" * 64) for i in (1, 2)}
    table, report = assemble([first, second], authorisations=authorisations)
    assert table.num_rows == 2 * first.events.num_rows
    assert table["event_id"].to_pylist() == first.events["event_id"].to_pylist() * 2
    assert all(
        {"TEST ALIAS", "TEST PLAYER", "TEST ONLY"} <= set(p["aliases"])
        for p in report["identities"]
    )
    assert all({m["match_id"] for m in p["memberships"]} == {1, 2} for p in report["identities"])
    assert report["identity_conflicts"]  # TEST actor IDs repeat across opponent teams.
    assert len({p["identity_key"] for p in report["identities"]}) == len(
        {r["player_id"] for r in first.roster}
    )
    assert report["generalisation_status"] == "insufficient_evidence"
    incomplete = MatchEvidence(
        first.events, first.metadata, [r for r in first.roster if r["player_id"] != 11]
    )
    _, missing = assemble([incomplete], authorisations=authorisations)
    assert missing["matches"][0]["unrostered_actors"]
    assert any(p["provider_player_id"] == 11 for p in missing["identities"])

    with pytest.raises(ValueError, match="Duplicate corpus"):
        assemble([first, first], authorisations=authorisations)
    with pytest.raises(ValueError, match="authorisation"):
        assemble([first])
    altered = first.events.set_column(0, first.events.column_names[0], first.events.column(0))
    altered = altered.replace_schema_metadata({b"TEST": "different"})
    with pytest.raises(ValueError, match="schema"):
        assemble([first, example(altered, 2)], authorisations=authorisations)


def census_fixture():
    raw = []

    def add(kind, ms, team=1, player=None, **detail):
        index = len(raw) + 1
        e = dict(
            id=f"TEST-{index}",
            index=index,
            period=1,
            timestamp="00:00:00.000",
            type={"name": kind},
            team={"id": team},
            **detail,
        )
        if player is not None:
            e["player"] = {"id": player}
        raw.append(
            dict(
                event_id=e["id"],
                provider_index=index,
                period=1,
                period_elapsed_ms=ms,
                event_type=kind,
                team_id=team,
                player_id=player,
                source_record_json=json.dumps(e),
            )
        )

    for t in (1, 2):
        add(
            "Starting XI",
            0,
            t,
            tactics={
                "lineup": [
                    {"player": {"id": t * 100 + i}, "position": {"id": 1}} for i in range(11)
                ]
            },
        )
    add("Half Start", 0)
    add("Player Off", 1000, 1, 100)
    add("Player On", 2000, 1, 100)
    add("Substitution", 3000, 1, 101, substitution={"replacement": {"id": 111}})
    add("Half End", 10000)
    roster = [dict(team_id=t, player_id=t * 100 + i) for t in (1, 2) for i in range(12)]
    return raw, roster


def test_recorded_exposure_temporary_off_and_substitution():
    raw, roster = census_fixture()
    result = chronology(pa.Table.from_pylist(raw), roster)
    rows = {r["player_id"]: r for r in result["players"]}
    assert result["status"] == "recorded_chronology_consistent"
    assert rows[100]["provisional_recorded_seconds"] == 9
    assert rows[101]["provisional_recorded_seconds"] == 3
    assert rows[111]["provisional_recorded_seconds"] == 7
    assert rows[211]["provisional_recorded_seconds"] is None
    assert all(r["minutes_played"] is None and not r["per90_eligible"] for r in rows.values())
    assert result["intervals"][0]["entry_event_ids"]
    assert [r["action"] for r in result["transitions"]] == [
        "player_off",
        "player_on",
        "substitution",
    ]


@pytest.mark.parametrize(
    "defect", ["missing_end", "bad_sub", "unpaired_off", "outside_actor", "duplicate_xi"]
)
def test_uncertified_exposure_is_null(defect):
    raw, roster = census_fixture()
    if defect == "missing_end":
        raw.pop()
    if defect == "bad_sub":
        e = json.loads(raw[5]["source_record_json"])
        e["substitution"]["replacement"]["id"] = 999
        raw[5]["source_record_json"] = json.dumps(e)
    if defect == "unpaired_off":
        raw = [r for r in raw if r["event_type"] != "Player On"]
    if defect == "outside_actor":
        raw[3]["event_type"] = "Pass"
        raw[3]["player_id"] = 999
    if defect == "duplicate_xi":
        raw.append(copy.deepcopy(raw[0]))
    r = chronology(pa.Table.from_pylist(raw), roster)
    assert r["issues"] and r["status"] == "insufficient_evidence"
    assert all(p["provisional_recorded_seconds"] is None for p in r["players"])


def test_dismissal_not_replaced_or_inferred_from_yellow():
    raw, roster = census_fixture()
    e = json.loads(raw[3]["source_record_json"])
    e["type"]["name"] = "Foul Committed"
    e["foul_committed"] = {"card": {"name": "Red Card"}}
    raw[3].update(event_type="Foul Committed", source_record_json=json.dumps(e))
    raw = [r for r in raw if r["event_type"] != "Player On"]
    r = chronology(pa.Table.from_pylist(raw), roster)
    assert not r["issues"]
    assert (
        next(p for p in r["players"] if p["player_id"] == 100)["provisional_recorded_seconds"] == 1
    )
    assert r["transitions"][0]["action"] == "dismissal"


def test_match_partition_and_feature_leakage():
    rows = [dict(source="TEST_ONLY", match_id=i, match_date=f"2000-01-0{i}") for i in (1, 2, 3)]
    split = chronological_split(rows, "2000-01-01", "2000-01-02")
    assert split == {
        "train": {("TEST_ONLY", 1)},
        "validation": {("TEST_ONLY", 2)},
        "test": {("TEST_ONLY", 3)},
    }
    with pytest.raises(ValueError, match="Insufficient"):
        chronological_split(rows[:1], "2000-01-01", "2000-01-02")
    with pytest.raises(ValueError, match="Duplicate"):
        chronological_split(rows + rows[:1], "2000-01-01", "2000-01-02")
    events = [
        dict(source="TEST_ONLY", match_id=1, period=1, event_id=str(i), provider_index=i)
        for i in (1, 2, 3)
    ]
    check_feature_lineage(events, ["1", "2"], 2, "3")
    with pytest.raises(ValueError, match="Future"):
        check_feature_lineage(events, ["3"], 2, "3")
    events[2]["period"] = 2
    with pytest.raises(ValueError, match="Future"):
        check_feature_lineage(events, ["1"], 2, "3")


def forecast_rows():
    return [
        dict(
            source="TEST_ONLY",
            match_id=m,
            team_id=1,
            player_id=11,
            period=1,
            event_id=str(i),
            outcome=i % 2,
            context="TEST_STATE",
            baseline=0.5,
            candidate=0.9 if i % 2 else 0.1,
        )
        for m in (1, 2, 3)
        for i in range(4)
    ]


def test_good_numeric_scores_do_not_validate_science():
    rows = forecast_rows()
    r = evaluate(rows)
    assert r["scores"]["candidate"]["equal_match_brier"] == pytest.approx(0.01)
    assert r["equal_match_brier_improvement"] == pytest.approx(0.24)
    assert r["match_bootstrap_95_interval"] == pytest.approx([0.24, 0.24])
    assert not r["scientifically_validated"] and r["status"] == "exploratory"
    assert evaluate(rows[:4])["match_bootstrap_95_interval"] is None
    assert any(
        b["n"] == 0 and b["observed_frequency"] is None
        for b in r["scores"]["candidate"]["calibration"]
    )
    worse = [dict(row, candidate=1 - row["outcome"]) for row in rows]
    w = evaluate(worse)
    assert w["equal_match_brier_improvement"] < 0
    assert w["scores"]["candidate"]["equal_match_log_loss"] is None
    assert w["scores"]["candidate"]["infinite_log_loss_predictions"] == len(worse)
    with pytest.raises(ValueError, match="Duplicate"):
        evaluate(rows + rows[:1])
    with pytest.raises(ValueError, match="probability"):
        evaluate([dict(rows[0], candidate=None)])


def test_equal_match_weighting_and_training_only_prior():
    rows = forecast_rows()
    model = fit_baselines(rows[:8])
    assert model["prior"] == 0.5
    with pytest.raises(ValueError, match="leakage"):
        baseline_predictions(model, rows[:1])
    predictions = baseline_predictions(model, [dict(r, context="UNSEEN") for r in rows[8:]])
    assert all(p["candidate"] == 0.5 and not p["context_supported"] for p in predictions)
    assert evaluate(predictions)["equal_match_brier_improvement"] == 0
    with pytest.raises(ValueError, match="two training"):
        fit_baselines(rows[:4])
    # Four records in one match cannot outweigh one record in another match.
    weighted = [dict(rows[0], baseline=1, candidate=1, outcome=0)] + [
        dict(rows[4 + i], baseline=0, candidate=0, outcome=0) for i in range(4)
    ]
    assert evaluate(weighted)["scores"]["baseline"]["equal_match_brier"] == 0.5


def test_negative_control_and_sample_planning():
    rows = forecast_rows()
    prior = copy.deepcopy(rows)
    shuffled = negative_control(rows, 7)
    assert shuffled == negative_control(rows, 7) and rows == prior
    assert sum(r["outcome"] for r in shuffled) == sum(r["outcome"] for r in rows)
    assert any(a["outcome"] != b["outcome"] for a, b in zip(rows, shuffled, strict=True))
    assert all(r["experimental_label_permutation"] for r in shuffled)
    assert required_clusters([0.1], 0.01)["required_clusters"] is None
    assert required_clusters([0.1, 0.1], 0.01)["required_clusters"] is None
    assert required_clusters([-0.1, 0.1, 0.3], 0.01)["required_clusters"] > 100
    with pytest.raises(ValueError):
        required_clusters([0, 1], 0)
    assert cluster_interval([1]) is None


def test_case_is_not_a_ranking_and_preserves_spatial_unknowns(source_events):
    from fil.research.case import investigate

    for e in source_events:
        e["possession"] = e["index"]  # TEST_ONLY one-record native groups.
        e["possession_team"] = dict(e["team"])
    source_events[1].pop("location")
    source_events[1]["pass"].pop("end_location")
    table = score_table(source_events)
    m = example(table)
    # TEST actor 11 has one team; actor 12 is contradictory in this fixture.
    result = investigate(table, dict(home_team_id=1, away_team_id=2), m.roster, player_id=11)
    assert result["status"] == "inconclusive" and not result["scientifically_validated"]
    assert result["player_baselines"]["all_completed_moves"]["n"] == 3
    assert result["player_baselines"]["progression_gain_10"]["n"] == 2
    assert result["player_moves"][0]["delta_x"] is None
    assert result["player_moves"][0]["distance_gain"] is None
    assert result["conventional"]["shot_events"] == 0
    with pytest.raises(ValueError, match="ambiguous"):
        investigate(table, dict(home_team_id=1, away_team_id=2), m.roster, player_id=12)


def test_period_breaks_and_shootout_not_player_exposure():
    raw, roster = census_fixture()
    for number, kind, t in [(8, "Half Start", 0), (9, "Half End", 5000), (10, "Pass", 1000)]:
        source = dict(
            id=f"TEST-{number}",
            index=number,
            period=2 if number != 10 else 5,
            timestamp="00:00:00.000",
            type={"name": kind},
            team={"id": 1},
        )
        raw.append(
            dict(
                event_id=source["id"],
                provider_index=number,
                period=source["period"],
                period_elapsed_ms=t,
                event_type=kind,
                team_id=1,
                player_id=None,
                source_record_json=json.dumps(source),
            )
        )
    result = chronology(pa.Table.from_pylist(raw), roster)
    assert not result["issues"]
    assert (
        next(p for p in result["players"] if p["player_id"] == 100)["provisional_recorded_seconds"]
        == 14
    )
    assert all(i["period"] in (1, 2) for i in result["intervals"])


def test_repeat_team_player_dependence_is_reported_not_solved():
    from fil.research.evaluation import dependence_audit

    groups = {"train": {("TEST_ONLY", 1)}, "test": {("TEST_ONLY", 2)}}
    meta = [
        dict(source="TEST_ONLY", match_id=i, team_ids=[1, i + 1], player_ids=[11, i + 20])
        for i in (1, 2)
    ]
    report = dependence_audit(groups, meta)
    assert report["overlap"]["train__test"]["shared_team_ids"] == [("TEST_ONLY", 1)]
    assert report["overlap"]["train__test"]["shared_player_ids"] == [("TEST_ONLY", 11)]
    assert not report["independence_certified"]
    meta[1]["player_ids"] = None
    assert dependence_audit(groups, meta)["overlap"]["train__test"]["shared_player_ids"] is None
    with pytest.raises(ValueError, match="overlap"):
        dependence_audit(dict(train={("TEST_ONLY", 1)}, test={("TEST_ONLY", 1)}), meta)


def test_research_artifact_idempotence_corruption_and_rights(source_events, tmp_path, monkeypatch):
    import hashlib

    from fil.research import __main__ as cli
    from fil.research.case import investigate

    configs = {k: str(tmp_path / k) for k in ("raw", "canonical", "clock", "score")}
    for value in configs.values():
        from pathlib import Path

        Path(value).mkdir()
    body = b"TEST_ONLY manifest"
    from pathlib import Path

    Path(configs["raw"]).joinpath("manifest.json").write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    table = score_table(source_events)
    table = table.set_column(
        table.schema.get_field_index("source_manifest_sha256"),
        table.schema.field("source_manifest_sha256"),
        pa.array([digest] * table.num_rows),
    )
    match = example(table)
    match.metadata.update(source_manifest_sha256=digest, home_team_id=1, away_team_id=2)
    auth = {("statsbomb_open_data", 1, digest)}
    monkeypatch.setattr(cli, "AUTHORISED", auth)
    monkeypatch.setattr(cli, "load_match", lambda c: (table, match.metadata))
    monkeypatch.setattr(cli, "load_roster", lambda *a: match.roster)
    monkeypatch.setattr(cli, "assemble", lambda matches: assemble(matches, authorisations=auth))
    monkeypatch.setattr(cli, "investigate", lambda e, m, r: investigate(e, m, r, 11))
    folder = cli.prepare([configs], tmp_path / "out", "a" * 40)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    assert cli.prepare([configs], tmp_path / "out", "a" * 40) == folder
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
    (folder / "events.parquet").write_bytes(b"TEST CORRUPTION")
    with pytest.raises(ValueError, match="differs"):
        cli.prepare([configs], tmp_path / "out", "a" * 40)
    with pytest.raises(ValueError, match="outside"):
        cli.prepare([configs], tmp_path / "raw" / "output", "a" * 40)
    monkeypatch.setattr(cli, "AUTHORISED", set())
    with pytest.raises(ValueError, match="authorisation"):
        cli.prepare([configs], tmp_path / "different", "a" * 40)
