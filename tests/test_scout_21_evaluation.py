"""The held-out tasks and explicit-field baseline remain independently inspectable."""

import json
import runpy
from pathlib import Path

from fil.intelligence.scout import search

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "docs/benchmarks/scout-copilot"

eval21 = runpy.run_path(str(ROOT / "scripts/evaluate_scout_21.py"))


def test_holdout_separate_and_baseline_uses_explicit_fields():
    dev = json.loads((BENCH / "cases.json").read_text())
    held = json.loads((BENCH / "heldout.json").read_text())
    assert {c["prompt"] for c in dev}.isdisjoint({c["prompt"] for c in held})
    assert len(held) == len({c["id"] for c in held}) == 16
    report = eval21["run_suite"](held, {c["id"]: c["structured_query"] for c in held})
    assert report["methods"]["structured_oracle"]["metrics"]["task_success"] == {
        "passed": 16, "total": 16
    }
    assert report["methods"]["live"]["status"] == "NOT RUN"
    assert report["methods"]["live"]["token_cost_usd"] is None


def test_heldout_paraphrases_pass_independent_guard_with_validated_fields():
    held = json.loads((BENCH / "heldout.json").read_text())
    for case in held[:4]:
        result = search(case["prompt"], lambda _, q=case["structured_query"]: q)
        assert not result["abstention"], case["id"]
        assert sorted(c["name"] for c in result["candidates"]) == sorted(
            case["expected_candidates"]
        )


def test_token_accounting_requires_complete_usage_and_rates():
    records = [{"usage": {"input_tokens": 100, "input_tokens_details": {"cached_tokens": 20},
                          "output_tokens": 10}}]
    usage, cost = eval21["summarize_usage"](records, (1, 0.5, 2))
    assert usage == {"input_tokens": 100, "cached_input_tokens": 20, "output_tokens": 10}
    assert cost == 110 / 1_000_000
    assert eval21["summarize_usage"](records + [None], (1, 0.5, 2)) == (None, None)
    assert eval21["summarize_usage"](records, (1, None, 2))[1] is None


def test_provider_error_fails_task_and_safe_abstention():
    held = json.loads((BENCH / "heldout.json").read_text())
    case = held[0]

    class BrokenProvider:
        last = None

        def __call__(self, text):
            raise ValueError("invalid provider output")

    report = eval21["run_suite"]([case], {case["id"]: case["structured_query"]}, BrokenProvider())
    live = report["methods"]["live"]
    assert live["metrics"]["task_success"]["passed"] == 0
    assert live["metrics"]["false_abstentions"] == 1
    assert live["metrics"]["constraint_preservation"] == {"passed": 0, "total": 1}
    assert live["outcomes"][0]["result"]["interpretation_error"]


def test_live_cli_requires_spending_limit_before_any_inference(tmp_path):
    import os
    import subprocess
    import sys

    env = {**os.environ, "OPENAI_API_KEY": "test-only-key"}
    base = [sys.executable, str(ROOT / "scripts/evaluate_scout_21.py"),
            "--output", str(tmp_path / "out.json"), "--live-model", "test-model"]
    for flags in ([], ["--spend-limit-usd", "1"], ["--provider-limit-confirmed"],
                  ["--spend-limit-usd", "0", "--provider-limit-confirmed"]):
        result = subprocess.run(base + flags, env=env, capture_output=True, text=True, check=False)
        assert result.returncode == 2
        assert "Configure a positive spending limit" in result.stderr
        assert not (tmp_path / "out.json").exists()
    env.pop("OPENAI_API_KEY")
    result = subprocess.run(base + ["--spend-limit-usd", "1", "--provider-limit-confirmed"],
                            env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "OPENAI_API_KEY unavailable" in result.stderr
    assert not (tmp_path / "out.json").exists()


def test_contribution_offline_and_deepseek_cli_missing_key(tmp_path):
    import os
    import subprocess
    import sys

    report = eval21["run_contribution_suite"]()
    assert len(report["methods"]["rules"]["result"]["candidates"]) == 2
    assert report["methods"]["live"]["status"] == "NOT RUN"
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/evaluate_scout_21.py"),
         "--output", str(tmp_path / "out.json"), "--provider", "deepseek", "--suite",
         "contribution", "--live-model", "deepseek-flash", "--spend-limit-usd", "0.6",
         "--provider-limit-confirmed"], env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "DEEPSEEK_API_KEY unavailable" in result.stderr
    assert not (tmp_path / "out.json").exists()
