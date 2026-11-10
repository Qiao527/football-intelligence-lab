"""Offline product contracts using only self-authored fictional events."""

import copy
import json
from fractions import Fraction
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from fil.intelligence import engine, sources
from fil.intelligence.demo import MATCHES, load_demo


@pytest.mark.parametrize("mid", MATCHES)
def test_complete_baseline_exact_independent_arithmetic_and_preservation(mid):
    raw, meta, identity = load_demo(mid)
    original = copy.deepcopy(raw)
    report = engine.analyze(raw, meta, identity)
    shots = [e for e in raw if e["type"]["name"] == "Shot" and e["period"] < 5]
    expected = sum(Fraction(str(e["shot"]["statsbomb_xg"])) for e in shots)
    assert Fraction(report["shot_weight"]) == expected
    assert report == engine.analyze(raw, meta, identity)
    assert raw == original
    assert report["source_event_count"] == len(raw)
    assert report["selected_event_ids"] == [e["id"] for e in raw]
    assert {i for u in report["native_units"] for i in u["event_ids"]} == {e["id"] for e in shots}
    for unit in report["native_units"]:
        included = set(unit["event_ids"])
        other = [e for e in shots if e["id"] not in included]
        delta = sum(
            Fraction(str(e["shot"]["statsbomb_xg"])) * (1 if e["team"]["id"] == 901 else -1)
            for e in other
        )
        assert Fraction(unit["complement_difference"]) == delta
        assert included <= set(unit["context_event_ids"])
        assert not included.intersection(unit["complement_event_ids"])
    assert all(
        c["scope"] == "Match fact"
        and c["independent_relevance"] is None
        and c["baseline_reproducible"]
        for c in report["review_cards"]
    )
    assert report["validated_tactical_patterns"] == []
    assert report["validated_explanations"] == report["validated_capabilities"] == []


def test_dynamic_input_changes_results_not_a_stored_report():
    raw, meta, identity = load_demo("demo-1")
    before = engine.analyze(raw, meta, identity)
    shot = next(e for e in raw if e["type"]["name"] == "Shot")
    shot["shot"]["statsbomb_xg"] = 0.999
    after = engine.analyze(raw, meta, identity)
    assert before["shot_weight"] != after["shot_weight"]
    assert before["selected_event_ids"] == after["selected_event_ids"]
    assert before["score"] == after["score"]
    assert after["review_cards"][0]["unit"]["event_ids"] == [shot["id"]]


def test_missing_weight_blocks_sums_not_source_evidence():
    raw, meta, identity = load_demo("demo-1")
    shot = next(e for e in raw if e["type"]["name"] == "Shot")
    shot["shot"].pop("statsbomb_xg")
    report = engine.analyze(raw, meta, identity)
    assert report["missing_shot_weight_ids"] == [shot["id"]]
    assert report["shot_weight"] is None and report["home_minus_away"] is None
    assert report["review_cards"] == [] and report["shot_count"] == 14
    assert all(r["shot_weight"] is None for r in report["team_totals"])
    assert "Missing shot weights" in report["abstention"]


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf"), "bad", True])
def test_invalid_weights_fail_closed(value):
    raw, meta, identity = load_demo("demo-1")
    next(e for e in raw if e["type"]["name"] == "Shot")["shot"]["statsbomb_xg"] = value
    with pytest.raises(ValueError, match="Invalid shot weight"):
        engine.analyze(raw, meta, identity)


@pytest.mark.parametrize("defect", ["duplicate", "order", "team", "score", "pass", "mode"])
def test_material_defects_fail_closed(defect):
    raw, meta, identity = load_demo("demo-1")
    if defect == "duplicate":
        raw[1]["id"] = raw[0]["id"]
    elif defect == "order":
        raw[0], raw[1] = raw[1], raw[0]
    elif defect == "team":
        raw[1]["team"]["id"] = 999
    elif defect == "score":
        meta["home_score"] += 1
    elif defect == "pass":
        next(e for e in raw if e["type"]["name"] == "Pass").pop("pass")
    else:
        identity["mode"] = "unverified_provider"
    with pytest.raises(ValueError):
        engine.analyze(raw, meta, identity)


def test_missing_membership_phase_and_explicit_null_pass_are_retained():
    raw, meta, identity = load_demo("demo-1")
    shot = next(e for e in raw if e["type"]["name"] == "Shot")
    shot["possession"] = None
    shot["play_pattern"] = {"name": None}
    p = next(e for e in raw if e["type"]["name"] == "Pass")
    p["pass"]["outcome"] = None
    report = engine.analyze(raw, meta, identity)
    assert report["unresolved_membership_shot_ids"] == [shot["id"]]
    assert shot["id"] in {s["event_id"] for s in report["shots"]}
    assert report["unknown_pass_outcome_ids"] == [p["id"]]
    assert report["completed_pass_count"] == 47
    assert "Unknown" in {r["phase"] for r in report["phase_totals"]}


def test_filters_no_shots_and_invalid_selection():
    raw, meta, identity = load_demo("demo-3")
    report = engine.analyze(raw, meta, identity, period=2, team=901)
    assert report["score"] == [meta["home_score"], meta["away_score"]]
    assert report["shot_count"] == 0 and report["shot_weight"] == "0"
    assert report["review_cards"] == [] and "No recorded Shots" in report["abstention"]
    assert report["selected_event_count"] == sum(
        e["period"] == 2 and e["team"]["id"] == 901 for e in raw
    )
    for selection in ({"period": 5}, {"team": 999}):
        with pytest.raises(ValueError):
            engine.analyze(raw, meta, identity, **selection)


def test_shootout_preserved_but_excluded_from_match_play():
    raw, meta, identity = load_demo("demo-1")
    shot = copy.deepcopy(next(e for e in raw if e["type"]["name"] == "Shot"))
    shot.update(id="TEST_ONLY_SHOOTOUT", index=len(raw) + 1, period=5)
    shot["shot"]["type"]["name"] = "Penalty"
    shot["shot"]["outcome"]["name"] = "Goal"
    before = engine.analyze(raw, meta, identity)
    raw.append(shot)
    after = engine.analyze(raw, meta, identity)
    assert after["shot_weight"] == before["shot_weight"]
    assert after["score"] == before["score"]
    assert after["excluded_shootout_event_ids"] == [shot["id"]]
    assert after["source_event_count"] == len(raw)
    assert after["shootout_reconciliation"] == "unavailable"


def test_provider_own_goal_perspectives_count_once():
    raw, meta, identity = load_demo("demo-1")
    template = copy.deepcopy(raw[-1])
    first, second = copy.deepcopy(template), copy.deepcopy(template)
    first.update(
        id="TEST_OWN_AGAINST",
        index=len(raw) + 1,
        type={"name": "Own Goal Against"},
        related_events=["TEST_OWN_FOR"],
    )
    second.update(
        id="TEST_OWN_FOR",
        index=len(raw) + 2,
        type={"name": "Own Goal For"},
        team={"id": 901, "name": "TEST_ONLY"},
        related_events=["TEST_OWN_AGAINST"],
    )
    raw.extend([first, second])
    meta["home_score"] += 1
    report = engine.analyze(raw, meta, identity)
    assert report["score"] == [meta["home_score"], meta["away_score"]]
    assert report["shot_count"] == 14
    assert first["id"] in report["selected_event_ids"]


def test_source_boundary_defaults_to_demo_and_never_acquires():
    assert len(sources.catalog()) == 3
    assert all(r["mode"] == "synthetic" for r in sources.catalog())
    with pytest.raises(ValueError, match="explicitly configured"):
        sources.load("8658")
    for module in (sources, engine):
        body = Path(module.__file__).read_text()
        assert "urlopen" not in body and "requests." not in body


def test_local_library_tamper_rejected_before_analytics(tmp_path):
    original = tmp_path / "bound.json"
    original.write_text("TEST_ONLY")
    obj = {
        "version": sources.LIBRARY_VERSION,
        "source_revision": sources.REVISION,
        "bindings": {str(original): "0" * 64},
    }
    with pytest.raises(ValueError, match="binding changed"):
        sources.catalog(obj)


@pytest.mark.parametrize(
    "defect", ["reference_extra", "reference_symlink", "quality_dir", "raw_dir"]
)
def test_cache_fingerprint_rejects_changed_bundle_membership(tmp_path, monkeypatch, defect):
    reference, quality, raw = [tmp_path / k for k in ("reference", "quality", "raw")]
    for root in (reference, quality, raw):
        root.mkdir()
        (root / "manifest.json").write_text("TEST_ONLY")
    (reference / "payload.json").write_text("TEST_ONLY")
    monkeypatch.setattr(sources, "PIN", {"files": [{"path": "payload.json"}]})
    monkeypatch.setattr(sources, "_paths", lambda *args: (quality, raw, {}))
    library = {"reference": str(reference)}
    before = sources.fingerprint(library, 1)
    assert before == sources.fingerprint(library, 1)
    if defect == "reference_extra":
        (reference / "unexpected.json").write_text("TEST_ONLY")
    elif defect == "reference_symlink":
        (reference / "link").symlink_to(raw, target_is_directory=True)
    elif defect == "quality_dir":
        (quality / "unexpected").mkdir()
    else:
        (raw / "unexpected").mkdir()
    with pytest.raises(ValueError, match="membership changed"):
        sources.fingerprint(library, 1)


def app(monkeypatch):
    monkeypatch.delenv("FIL_INTELLIGENCE_LIBRARY", raising=False)
    return AppTest.from_file(
        str(Path(sources.__file__).with_name("app.py")), default_timeout=30
    ).run()


def test_product_ui_report_drilldown_filters_match_change_and_empty(monkeypatch):
    a = app(monkeypatch)
    assert not a.exception and not a.metric
    a.button[0].click().run()
    assert not a.exception
    assert [m.value for m in a.metric] == ["66", "14", "4.575", "48"]
    assert all("deprecated" not in warning.value for warning in a.warning)
    review_button = next(b for b in a.button if b.label.startswith("Inspect original actions"))
    review_button.click().run()
    assert not a.exception and a.radio(key="workspace").value == "Evidence explorer"
    chosen = a.selectbox(key="original_action").value
    assert chosen.startswith("demo-1-action-") and a.code[0].value == chosen
    a.selectbox(key="report_period").select(2).run()
    a.selectbox(key="report_team").select(901).run()
    assert not a.exception
    assert a.metric[1].value == "3"
    next(b for b in a.button if b.label == "Reset filters").click().run()
    assert a.selectbox(key="evidence_scope").value == "Current selection"
    assert a.metric[0].value == "66"
    a.text_input(key="event_search").set_value("NO_SUCH_ORIGINAL_ID").run()
    assert any("No original actions" in i.value for i in a.info)
    a.selectbox(key="match_choice").select("demo-3").run()
    assert not a.metric  # No stale report while a different match is selected.
    a.button[0].click().run()
    a.selectbox(key="report_period").select(2).run()
    assert not a.exception and a.metric[1].value == "0"
    assert any("No recorded Shots" in i.value for i in a.info)
    a.radio(key="workspace").set_value("Baseline & limits").run()
    assert not a.exception
    assert any("Four claims" in i.value for i in a.markdown)


def test_malformed_library_shows_failure_without_demo_fallback(tmp_path, monkeypatch):
    path = tmp_path / "library.json"
    path.write_text(json.dumps({"version": "bad"}))
    monkeypatch.setenv("FIL_INTELLIGENCE_LIBRARY", str(path))
    a = AppTest.from_file(str(Path(sources.__file__).with_name("app.py")), default_timeout=30).run()
    assert not a.exception and not a.metric
    assert any("verification failed" in e.value for e in a.error)


def test_cached_local_report_is_withheld_on_changed_input_and_has_no_export(tmp_path, monkeypatch):
    """TEST_ONLY local adapter: cache hits cannot serve a previously valid report after failure."""
    raw, meta, identity = load_demo("demo-2")
    identity["mode"] = "local"
    path = tmp_path / "TEST_ONLY-library.json"
    path.write_text('{"TEST_ONLY": true}')
    monkeypatch.setenv("FIL_INTELLIGENCE_LIBRARY", str(path))
    original_catalog = sources.catalog()
    monkeypatch.setattr(
        sources,
        "catalog",
        lambda _: original_catalog
        + [
            {
                "id": "100002",
                "title": "TEST_ONLY local fixture",
                "mode": "local",
                "date": "TEST_ONLY",
            }
        ],
    )
    monkeypatch.setattr(sources, "load", lambda *args: (raw, meta, identity))
    monkeypatch.setattr(sources, "fingerprint", lambda *args: "TEST_ONLY-valid-content")
    a = AppTest.from_file(str(Path(sources.__file__).with_name("app.py")), default_timeout=30).run()
    a.radio(key="source_mode").set_value("Local research").run()
    a.button[0].click().run()
    assert not a.exception and a.metric[1].value == "14"
    assert not a.get("download_button")
    a.run()
    assert not a.exception and a.metric[1].value == "14"
    monkeypatch.setattr(sources, "fingerprint", lambda *args: "TEST_ONLY-changed-content")

    def reject(*args):
        raise ValueError("TEST_ONLY source hash mismatch")

    monkeypatch.setattr(sources, "load", reject)
    a.run()
    assert not a.exception and not a.metric
    assert any("source hash mismatch" in e.value for e in a.error)


def test_demo_cli_clears_inherited_research_setting_and_binds_loopback(monkeypatch):
    from fil.intelligence import __main__ as cli

    captured = {}
    monkeypatch.setenv("FIL_INTELLIGENCE_LIBRARY", "/TEST_ONLY/private-library.json")
    monkeypatch.setattr("sys.argv", ["fil.intelligence", "run", "--port", "8599"])

    def launch(cmd, env):
        captured.update(command=cmd, env=env)
        return 0

    monkeypatch.setattr(cli.subprocess, "call", launch)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert captured["env"]["FIL_INTELLIGENCE_LIBRARY"] == ""
    assert "--server.address=127.0.0.1" in captured["command"]
    assert "--browser.gatherUsageStats=false" in captured["command"]
