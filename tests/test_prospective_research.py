"""TEST_ONLY target/forecast/dependence contracts, never evidence of football usefulness."""

import copy
import json

import pytest

from fil.research.figshare_metadata import inventory, read_response
from fil.research.possession_target import label_segments, label_support, possession_weights
from fil.research.prospective import (
    components,
    fit_weighted_baseline,
    paired_uncertainty,
    partition_plan,
    predict_weighted,
)


def source(types=("Pass", "Shot"), close=True):
    raw = []
    for n, kind in enumerate(types, 1):
        raw.append(
            dict(
                id=f"TEST-{n}",
                index=n,
                period=1,
                timestamp="00:00:01.000",
                team=dict(id=1),
                possession=1,
                possession_team=dict(id=1),
                type=dict(name=kind),
                **(
                    {"pass": {}}
                    if kind == "Pass"
                    else {"shot": dict(statsbomb_xg=0.1)}
                    if kind == "Shot"
                    else {}
                ),
            )
        )
    if close:
        raw.append(
            dict(
                id="TEST-CLOSE",
                index=len(raw) + 1,
                period=1,
                team=dict(id=2),
                possession=2,
                possession_team=dict(id=2),
                type=dict(name="Pressure"),
                timestamp="00:00:02.000",
            )
        )
    return raw


def labels(raw):
    return label_segments(raw, "a" * 64, 999)


@pytest.mark.parametrize("close", [True, False])
def test_short_observed_positive_is_confirmed_even_without_terminal_boundary(close):
    raw = source(close=close)
    before = copy.deepcopy(raw)
    r = labels(raw)[0]
    assert raw == before and r["outcome"] == 1
    assert r["later_shot_event_ids"] == ["TEST-2"]
    assert r["feature_event_ids"] == ["TEST-1"]
    assert r["complete_terminal_chance_evidence"] == close
    assert r["complete_later_shot_xg_sum"] == (0.1 if close else None)
    assert not r["physical_timing_certified"]


def test_negative_requires_closure_unknown_is_not_zero_and_own_goal_is_not_shot():
    assert labels(source(("Pass", "Own Goal Against")))[0]["outcome"] == 0
    r = labels(source(("Pass",), close=False))[0]
    assert r["outcome"] is None and r["observation_state"] == "unresolved_or_censored"
    assert labels(source(("Shot", "Pass")))[0]["outcome"] == 0  # prior Shot excluded


@pytest.mark.parametrize("problem", ["owner", "cross_period", "unassigned", "reuse"])
def test_membership_ambiguity_does_not_turn_observed_shot_into_certified_attribution(problem):
    raw = source(("Pass", "Carry", "Shot"))
    if problem == "owner":
        raw[1]["possession_team"]["id"] = 2
    elif problem == "cross_period":
        for e in raw[1:]:
            e["period"] = 2
    elif problem == "unassigned":
        raw[1]["possession"] = None
    else:
        raw[1]["possession"] = 90
    assert labels(raw)[0]["outcome"] is None


def test_paired_half_end_negative_does_not_select_later_timestamp_or_skip_unassigned_records():
    raw = source(("Pass",), close=False)
    for i, team in [(2, 1), (3, 2)]:
        raw.append(
            dict(
                id=f"TEST-{i}",
                index=i,
                period=1,
                timestamp=f"00:00:02.{i}00",
                team=dict(id=team),
                possession=1,
                possession_team=dict(id=1),
                type=dict(name="Half End"),
                related_events=[f"TEST-{5 - i}"],
            )
        )
    r = labels(raw)[0]
    assert r["outcome"] == 0 and r["closure_evidence_ids"] == ["TEST-2", "TEST-3"]
    raw[-1]["half_end"] = dict(early_video_end=True)
    assert labels(raw)[0]["outcome"] is None
    raw[-1].pop("half_end")
    raw.insert(1, dict(raw[0], id="TEST-UNASSIGNED", possession=None))
    for i, e in enumerate(raw, 1):
        e["index"] = i
    # Original source IDs/links retained; the gap must not be bridged to claim negative.
    assert labels(raw)[0]["outcome"] is None


def test_missing_xg_keeps_positive_but_total_unknown_and_shootouts_excluded():
    raw = source()
    raw[1]["shot"] = {}
    r = labels(raw)[0]
    assert r["outcome"] == 1 and r["missing_shot_xg_event_ids"] == ["TEST-2"]
    assert r["complete_later_shot_xg_sum"] is None
    for e in raw:
        e["period"] = 5
    r = labels(raw)[0]
    assert r["outcome"] is None


def test_duplicate_order_and_identity_are_not_silently_sorted_or_dropped():
    raw = source()
    raw[1]["index"] = raw[0]["index"]
    with pytest.raises(ValueError, match="order"):
        labels(raw)
    raw[1]["id"] = raw[0]["id"]
    with pytest.raises(ValueError, match="unique"):
        labels(raw)


def test_possession_weighting_prevents_long_annotation_chains_domination():
    rows = labels(source(("Pass", "Carry", "Shot")))
    rows.append(dict(rows[0], possession_id=9, cutoff_event_id="TEST-OTHER"))
    rows.append(dict(rows[0], outcome=None, cutoff_event_id="TEST-CENSORED"))
    weighted = possession_weights(rows)
    assert [r["within_match_possession_weight"] for r in weighted] == [0.25, 0.25, 0.5, None]
    with pytest.raises(ValueError, match="Duplicate"):
        possession_weights(rows + [rows[0]])
    support = label_support(rows)
    assert support["unweighted_all_cutoff_prevalence_bounds"] == [0.75, 1]
    assert support["max_positive_cutoffs_sharing_one_shot"] == 3
    assert support["distinct_linked_shots"] == 1
    assert not support["independent_observations_certified"]


def test_component_resampling_keeps_unequal_component_size_in_match_estimand():
    ms = [
        dict(source="statsbomb_open_data", match_id=i, team_ids=t, player_ids=[])
        for i, t in [(1, [1, 2]), (2, [2, 3]), (3, [4, 5])]
    ]
    effects = [
        dict(source=m["source"], match_id=m["match_id"], effect=float(i)) for i, m in enumerate(ms)
    ]
    r = paired_uncertainty(effects, ms)
    assert r["equal_match_effect"] == 1
    assert r["component_interval"] == [0.5, 2]
    assert not r["inferential_independence_certified"]


def test_frozen_future_partition_is_whole_match_and_excludes_all_exposed_matches():
    ids = list(range(1000, 1057))  # TEST_ONLY metadata; no source payload.
    proposal = dict(expansion_new_match_ids=ids, files=[], metadata_source_sha256="a" * 64)
    metadata = [
        dict(
            match_id=m,
            match_date=day,
            home_team=dict(home_team_id=1),
            away_team=dict(away_team_id=2),
        )
        for m, day in zip(
            ids, ["2018-06-26"] * 30 + ["2018-07-01"] * 20 + ["2018-07-02"] * 7, strict=True
        )
    ]
    plan = partition_plan(proposal, metadata)
    assert {k: len(v) for k, v in plan["partitions"].items()} == dict(
        train=30, validation=20, test=7
    )
    assert not plan["event_payloads_opened"] and not plan["evaluated"]
    assert plan["expansion_gate"] == "BLOCKED"
    proposal["expansion_new_match_ids"][-1] = 8655
    with pytest.raises(ValueError, match="57 unacquired"):
        partition_plan(proposal, metadata)


def test_proposed_metric_artifact_cannot_unlock_original_expansion_executor(tmp_path):
    from pathlib import Path

    from fil.research.acquisition import acquire, scope

    proposal = Path("docs/research/statsbomb_corpus_proposal.json")
    mid = scope(proposal)["expansion_new_match_ids"][0]
    gate = tmp_path / "proposal.json"
    gate.write_text(
        json.dumps(dict(expansion_gate="BLOCKED", policy_status="PROPOSED_NOT_ACCEPTED"))
    )
    with pytest.raises(ValueError, match="Pilot gate failed"):
        acquire(mid, tmp_path / "raw", proposal, "a" * 40, pilot_gate=gate)
    assert not (tmp_path / "raw").exists()


def training_rows():
    return [
        dict(
            source="statsbomb_open_data",
            match_id=m,
            cutoff_event_id=f"TEST-{m}-{i}",
            possession_id=i,
            partition="train",
            outcome=y,
            within_match_possession_weight=0.5,
            feature_indices=[i + 1],
            cutoff_provider_index=i + 1,
            features=dict(context="EMPTY_POSITIVES"),
        )
        for m in (100, 200)
        for i, y in enumerate((0, 0))
    ]


def test_training_only_shrinkage_avoids_hard_zero_and_preserves_missing_fallback():
    train = training_rows()
    before = copy.deepcopy(train)
    model = fit_weighted_baseline(train, "context", 1)
    assert train == before and 0 < model["bins"]["EMPTY_POSITIVES"] < 1
    held = [dict(train[0], match_id=300, features=dict(context=None))]
    assert predict_weighted(model, held) == [model["prior"]]
    with pytest.raises(ValueError, match="overlap"):
        predict_weighted(model, train)
    with pytest.raises(ValueError, match="overlap"):
        predict_weighted(json.loads(json.dumps(model)), train)
    train[0]["partition"] = "test"
    with pytest.raises(ValueError, match="Training-only"):
        fit_weighted_baseline(train, "context", 1)


def test_future_feature_and_incorrect_cluster_weights_are_rejected():
    train = training_rows()
    train[0]["feature_indices"] = [999]
    with pytest.raises(ValueError, match="Future"):
        fit_weighted_baseline(train, "context", 1)
    train = training_rows()
    train[0]["within_match_possession_weight"] = 0.75
    with pytest.raises(ValueError, match="unit-weight"):
        fit_weighted_baseline(train, "context", 1)


def test_team_player_transitive_components_do_not_become_independent_matches():
    ms = [
        dict(source="statsbomb_open_data", match_id=i, team_ids=t, player_ids=p)
        for i, t, p in [(1, [1, 2], [10]), (2, [2, 3], [20]), (3, [4, 5], [20])]
    ]
    graph = components(ms)
    assert len(graph["components"]) == 1 and not graph["missing_identity"]
    effects = [dict(source=m["source"], match_id=m["match_id"], effect=0.001) for m in ms]
    r = paired_uncertainty(effects, ms)
    assert r["component_interval"] is None
    assert r["component_interval_status"] == "withheld_single_component"
    ms[0]["player_ids"] = None
    assert (
        paired_uncertainty(effects, ms)["component_interval_status"]
        == "withheld_incomplete_identity"
    )
    assert paired_uncertainty(effects[:1], ms[:1])["match_bootstrap_conditional_interval"] is None


def test_figshare_exact_file_versions_and_licence_inheritance_are_not_approval():
    collection = dict(id=4415000, version=2)
    articles = [
        dict(
            id=111,
            version=3,
            doi="TEST_ONLY_DOI",
            authors=[dict(name="TEST")],
            license=dict(name="CC BY 4.0", url="https://creativecommons.org/licenses/by/4.0/"),
            files=[
                dict(
                    id=222,
                    size=100,
                    name="TEST_ONLY.zip",
                    computed_md5="a" * 32,
                    supplied_md5="b" * 32,
                )
            ],
        )
    ]
    result = inventory(collection, articles)
    f = result["files"][0]
    assert f["article_version"] == 3 and f["size_bytes"] == 100
    assert f["license_scope"] == "article_metadata_inheritance"
    assert f["acquired_payload_sha256"] is None and not f["acquired"]
    assert f["metadata_issues"] == ["provider_checksum_fields_disagree"]
    assert not result["acquisition_authorized"] and not result["inventory_complete"]
    articles[0]["license"] = None
    assert (
        "missing_article_license" in inventory(collection, articles)["files"][0]["metadata_issues"]
    )
    with pytest.raises(ValueError, match="Duplicate"):
        inventory(collection, articles + articles)


@pytest.mark.parametrize(
    "url",
    [
        "https://processed.example/v2/articles/111",
        "https://api.figshare.com/v2/file/download/222",
        "https://api.figshare.com.evil.example/v2/articles/111",
    ],
)
def test_metadata_parser_never_accepts_archives_or_mirror_origins(url):
    with pytest.raises(ValueError, match="metadata URL"):
        read_response(url, b"{}")
    assert read_response("https://api.figshare.com/v2/articles/111/versions/3", b"{}") == {}
    assert json.loads(b"{}") == {}
