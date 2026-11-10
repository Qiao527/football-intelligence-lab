"""TEST_ONLY algebra and comparison design counterexamples; no empirical football outcomes."""

from copy import deepcopy
from fractions import Fraction

import pytest

from fil.research.comparison_design import (
    analyse,
    context,
    graph,
    leave_match_out,
    observations,
    topology,
)


def exact_rank(edges):
    columns = sorted({n for edge in edges for n in edge})
    rows = [[Fraction(int(n in e)) for n in columns] for e in edges]
    rank = 0
    for col in range(len(columns)):
        pivot = next((i for i in range(rank, len(rows)) if rows[i][col]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        value = rows[rank][col]
        rows[rank] = [v / value for v in rows[rank]]
        for i in range(rank + 1, len(rows)):
            value = rows[i][col]
            rows[i] = [a - value * b for a, b in zip(rows[i], rows[rank], strict=True)]
        rank += 1
    return rank


@pytest.mark.parametrize(
    "edges",
    [
        [],
        [("p:1", "c:a")],
        [("p:1", "c:a"), ("p:2", "c:a")],
        [("p:1", "c:a"), ("p:1", "c:b"), ("p:2", "c:a"), ("p:2", "c:b")],
        [("p:1", "c:a"), ("p:2", "c:b")],
        [("p:1", "c:a"), ("p:1", "c:a"), ("p:2", "c:b")],
    ],
)
def test_exact_rank_theorem_matches_independent_fraction_elimination(edges):
    result = topology(edges)
    assert result["exact_rank"] == exact_rank(edges)
    assert result["vertices"] - result["exact_rank"] == result["nullity"]
    for component in result["components"]:
        values = {n: (1 if n.startswith("p:") else -1) for n in component}
        assert all(values.get(a, 0) + values.get(b, 0) == 0 for a, b in edges)


def test_missing_crossing_and_bridge_effect_cannot_be_repaired_by_more_rows():
    disconnected = [("p:1", "c:a"), ("p:2", "c:b")]
    assert topology(disconnected) == topology(disconnected * 100)
    assert topology(disconnected)["across_component_player_contrasts"] == 1
    crossed = disconnected + [("p:1", "c:b")]
    assert topology(crossed)["across_component_player_contrasts"] == 0
    assert topology(crossed)["exact_rank"] == exact_rank(crossed)


def row(pid=1, mid=1, team=10, cell="0:0", role=5, i=0):
    return dict(
        record_id=f"TEST_ONLY_{pid}_{mid}_{i}",
        event_id=f"TEST_ONLY_{pid}_{mid}_{i}",
        player_id=pid,
        match_id=mid,
        team_id=team,
        native_cell=cell,
        position_id=role,
        period=1,
        score_state="level",
        unknown_outcome=False,
        memberships=dict(pass_attempt=True, verified_completed=True, chain_release=True),
    )


def test_context_missing_role_does_not_create_fake_shared_role():
    r = row(role=None)
    assert context(r, "team") == (10,)
    assert context(r, "native_context") == (10, 1, 1, "level", "0:0")
    assert context(r, "known_position_context") is None
    result = graph([r, row(pid=2, role=None)], "known_position_context")
    assert result["observations"] == 0 and result["dropped_record_ids"]
    assert result["unobserved_population_players"] == [1, 2]
    assert not result["direct_pairs"]


def test_position_fragmentation_is_not_automatically_better_comparison():
    rows = [row(pid=pid, role=pid, i=i) for pid in (1, 2) for i in range(5)]
    coarse = graph(rows, "native_context")
    fine = graph(rows, "known_position_context")
    assert coarse["pairs_with_at_least5_context"] == 1
    assert fine["pairs_with_shared_context"] == 0
    assert len(fine["components"]) > len(coarse["components"])


def test_nominal_and_repeated_support_use_independent_match_ids():
    rows = [row(pid=pid, mid=mid, i=i) for pid in (1, 2) for mid in (1, 2) for i in range(5)]
    result = graph(rows, "native_context")
    assert result["pairs_with_at_least5_in_two_matches"] == 1
    assert result["direct_pairs"][0]["supported_match_ids"] == [1, 2]
    insufficient = [r for r in rows if r["player_id"] == 1 or r["record_id"].endswith("_0")]
    for design in ("team", "team_match", "native_context"):
        assert graph(insufficient, design)["pairs_with_at_least5_in_two_matches"] == 0


def test_leave_match_out_keeps_lost_players_in_original_universe():
    rows = [row(pid=1, mid=1), row(pid=2, mid=1), row(pid=1, mid=2), row(pid=3, mid=2)]
    omitted = leave_match_out(rows)
    first = next(r for r in omitted if r["excluded_match_id"] == 1)
    assert first["missing_player_ids"] == [2]
    assert first["originally_supported_contrasts_lost"] == 2


def test_duplicate_records_and_empty_population_fail_without_changing_estimand():
    with pytest.raises(ValueError, match="Duplicate"):
        analyse([row(), row()], {1})
    r = row()
    r["memberships"]["chain_release"] = False
    with pytest.raises(ValueError, match="Empty declared population"):
        analyse([r], {1})


def test_release_context_and_unknown_attempt_selection_are_not_first_pass_context():
    pass1 = dict(
        id="TEST_ONLY_A",
        index=1,
        period=1,
        timestamp="00:00:00.000",
        type={"name": "Pass"},
        team={"id": 10},
        player={"id": 1},
        location=[1, 1],
        **{"pass": {"recipient": {"id": 2}, "end_location": [21, 1]}},
    )
    pass2 = dict(pass1, id="TEST_ONLY_B", index=2, player={"id": 2}, location=[81, 1])
    unknown = dict(pass1, id="TEST_ONLY_U", index=3, **{"pass": {"outcome": None}})
    players = [dict(player_id=i, team_id=10, native_position_evidence=[]) for i in (1, 2)]
    parent = dict(
        players=players,
        team_ids=[10, 20],
        chains=[
            dict(chain_id="TEST_ONLY_A/TEST_ONLY_B", pass_event_ids=["TEST_ONLY_A", "TEST_ONLY_B"])
        ],
        passes=[
            dict(
                event_id=e["id"],
                score_state="level",
                prior_goal_event_ids=[],
                exclusion_reasons=["unknown_outcome"] if e["id"] == "TEST_ONLY_U" else [],
            )
            for e in (pass1, pass2, unknown)
        ],
    )
    before = deepcopy(parent)
    output = observations(
        parent, dict(match_id=99, source_manifest_sha256="a" * 64), [pass1, pass2, unknown]
    )
    assert parent == before
    assert output[1]["native_cell"] == "4:0" and output[1]["memberships"]["chain_release"]
    assert output[2]["unknown_outcome"] and output[2]["memberships"]["pass_attempt"]
    assert not output[2]["memberships"]["verified_completed"]
    assert output[2]["position_id"] is None


def test_all_three_by_three_binary_designs_agree_with_exact_elimination():
    possible = [(f"p:{i}", f"c:{j}") for i in range(3) for j in range(3)]
    for mask in range(1 << len(possible)):
        edges = [edge for k, edge in enumerate(possible) if mask & (1 << k)]
        assert topology(edges)["exact_rank"] == exact_rank(edges)


def test_changed_protocol_blocks_source_processing(tmp_path, monkeypatch):
    import fil.research.comparison_design as module

    changed = tmp_path / "protocol.md"
    changed.write_text("TEST_ONLY_CHANGED")
    monkeypatch.setattr(module, "PROTOCOL", changed)
    with pytest.raises(ValueError, match="Frozen comparison protocol changed"):
        module.run(tmp_path / "missing", tmp_path / "output", "a" * 40)
    assert not (tmp_path / "output").exists()
