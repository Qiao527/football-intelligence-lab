"""Evaluate synthetic rules, manually specified structured queries and optional live model."""

import argparse
import json
import os
import runpy
import statistics
import time
from pathlib import Path

from fil.intelligence.openai_scout import OpenAIInterpreter
from fil.intelligence.scout import execute_query, search
from fil.intelligence.scout_fixture import scout_fixture

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "docs/benchmarks/scout-copilot"
grade = runpy.run_path(str(ROOT / "scripts/evaluate_scout.py"))["grade"]


def metrics(rows):
    total = len(rows)
    predicted = sum(bool(r["result"]["abstention"]) for r in rows)
    actual = sum(r["case"]["expected_abstention"] for r in rows)
    true = sum(bool(r["result"]["abstention"]) and r["case"]["expected_abstention"] for r in rows)
    evidence = [r["grades"]["citation_correct"] for r in rows
                if r["grades"]["citation_correct"] is not None]
    latencies = [r["latency_seconds"] for r in rows]
    comparable = [r for r in rows if r["reference_query"]["intent"] not in
                  {"unsupported", "comparison"}]
    constraints = sum(r["result"]["query"] == r["reference_query"]
                      and not r["result"].get("interpretation_error") for r in comparable)
    return {
        "task_success": {"passed": sum(r["grades"]["task_complete"] for r in rows), "total": total},
        "abstention_precision": {"numerator": true, "denominator": predicted,
                                 "value": true / predicted if predicted else None},
        "abstention_recall": {"numerator": true, "denominator": actual,
                              "value": true / actual if actual else None},
        "false_abstentions": sum(bool(r["result"]["abstention"])
                                 and not r["case"]["expected_abstention"] for r in rows),
        "constraint_preservation": {"passed": constraints, "total": len(comparable)},
        "model_proposal_constraint_preservation": (
            {"passed": sum((r.get("provider") or {}).get("parsed_query") == r["reference_query"]
                           for r in comparable), "total": len(comparable)}
            if rows and rows[0]["result"]["interpretation_mode"] == "provider" else None
        ),
        "evidence_correctness": {"passed": sum(evidence), "total": len(evidence)},
        "failures": [r["case"]["id"] for r in rows if not r["grades"]["task_complete"]],
        "latency_seconds": {"median": statistics.median(latencies) if latencies else None,
                            "total": sum(latencies)},
    }


def run_suite(cases, structured, provider=None):
    events, _, identity = scout_fixture()
    rows = {"rules": [], "structured_oracle": [], "live": []}
    for case in cases:
        for method in ("rules", "structured_oracle", "live"):
            if method == "live" and provider is None:
                continue
            start = time.perf_counter()
            result = (search(case["prompt"]) if method == "rules" else
                      execute_query(structured[case["id"]]) if method == "structured_oracle" else
                      search(case["prompt"], provider))
            elapsed = time.perf_counter() - start
            grades = grade(case, result, events)
            if result.get("interpretation_error"):
                grades["task_complete"] = False
            rows[method].append({"case": case, "reference_query": structured[case["id"]],
                                 "result": result,
                                 "grades": grades,
                                 "latency_seconds": elapsed,
                                 "provider": provider.last if method == "live" else None})
    return {"fixture_sha256": identity["raw_sha256"], "case_count": len(cases),
            "methods": {method: {"status": "RUN", "metrics": metrics(results), "outcomes": results,
                                 **({"usage": {"input_tokens": 0, "output_tokens": 0},
                                     "token_cost_usd": 0} if method != "live" else {})}
                        if results else {"status": "NOT RUN", "reason": "No live model requested",
                                         "usage": None, "token_cost_usd": None,
                                         "actual_billed_cost_usd": None}
                        for method, results in rows.items()}}


def summarize_usage(records, rates):
    """Only total and price usage when every record has complete provider accounting."""
    usages = [record["usage"] for record in records if record and record.get("usage")]
    complete = bool(records) and len(usages) == len(records) and all(
        type(u.get("input_tokens")) is int and u["input_tokens"] >= 0
        and type(u.get("output_tokens")) is int and u["output_tokens"] >= 0
        and isinstance(u.get("input_tokens_details"), dict)
        and type(u["input_tokens_details"].get("cached_tokens")) is int
        and 0 <= u["input_tokens_details"]["cached_tokens"] <= u["input_tokens"]
        for u in usages
    )
    if not complete:
        return None, None
    usage = {"input_tokens": sum(u["input_tokens"] for u in usages),
             "cached_input_tokens": sum(u["input_tokens_details"]["cached_tokens"] for u in usages),
             "output_tokens": sum(u["output_tokens"] for u in usages)}
    cost = None
    if all(rate is not None for rate in rates):
        cost = ((usage["input_tokens"] - usage["cached_input_tokens"]) * rates[0]
                + usage["cached_input_tokens"] * rates[1]
                + usage["output_tokens"] * rates[2]) / 1_000_000
    return usage, cost


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live-model", help="Explicit OpenAI model; uses OPENAI_API_KEY")
    parser.add_argument("--suite", choices=("both", "development", "challenge"),
                        help="Defaults to challenge for live; both for offline")
    parser.add_argument("--input-usd-per-million", type=float)
    parser.add_argument("--cached-input-usd-per-million", type=float)
    parser.add_argument("--output-usd-per-million", type=float)
    args = parser.parse_args()
    rates = (args.input_usd_per_million, args.cached_input_usd_per_million,
             args.output_usd_per_million)
    if any(rate is not None and (not 0 <= rate < float("inf")) for rate in rates):
        parser.error("Rates must be finite nonnegative USD per million tokens")
    provider = None
    if args.live_model:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            parser.error("OPENAI_API_KEY unavailable; live evaluation NOT RUN")
        provider = OpenAIInterpreter(key, args.live_model)
    dev = json.loads((BENCH / "cases.json").read_text())
    held = json.loads((BENCH / "heldout.json").read_text())
    annotated = json.loads((BENCH / "dev_structured.json").read_text())
    selection = args.suite or ("challenge" if provider else "both")
    reports = {}
    if selection in {"both", "development"}:
        reports["development"] = run_suite(dev, annotated, provider)
    if selection in {"both", "challenge"}:
        reports["challenge"] = run_suite(
            held, {c["id"]: c["structured_query"] for c in held}, provider
        )
    for report in reports.values():
        live = report["methods"]["live"]
        if live["status"] == "RUN":
            records = [row["provider"] for row in live["outcomes"]]
            live["usage"], live["token_cost_usd"] = summarize_usage(records, rates)
            live["actual_billed_cost_usd"] = None
            live["cost_note"] = (
                "Token cost is estimated from user-supplied rates; actual billing must be "
                "reconciled separately. Missing usage or rates leaves the estimate unknown."
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2) + "\n")
    print(json.dumps({split: {k: {x: y for x, y in v.items() if x != "outcomes"}
                              for k, v in report["methods"].items()}
                      for split, report in reports.items()}, indent=2))


if __name__ == "__main__":
    main()
