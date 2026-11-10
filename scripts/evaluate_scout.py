"""Evaluate the synthetic rules fallback and discovery substring proxy, with raw outcomes."""

import argparse
import json
from pathlib import Path

from fil.intelligence.scout import search
from fil.intelligence.scout_fixture import scout_fixture

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "docs/benchmarks/scout-copilot/cases.json"
# Independent references for this exact authored fixture, not model-generated labels.
COUNTS = {
    "Mara Vale": {"passes": 5, "shots": 1, "defensive_transitions": 2, "build_up_passes": 5},
    "Ivo Moss": {"passes": 2, "shots": 1, "defensive_transitions": 0, "build_up_passes": 2},
    "Tess Rowe": {"passes": 2, "shots": 1, "defensive_transitions": 1, "build_up_passes": 2},
}


def grade(case: dict, result: dict, events: list[dict]) -> dict:
    """Grade the structured response against fixed answers and original authored actions."""
    by_id = {event["id"]: event for event in events}
    names = sorted(c["name"] for c in result["candidates"])
    abstained = bool(result["abstention"])
    candidates_correct = names == sorted(case["expected_candidates"])
    abstention_correct = abstained == case["expected_abstention"]
    citations_correct = True
    numeric_correct = True
    contradiction_correct = True
    explanation_correct = True
    for candidate in result["candidates"]:
        name = candidate["name"]
        reference = COUNTS.get(name)
        numeric_correct &= candidate["counts"] == reference
        if reference:
            expected_text = (
                f"{name} has {reference['defensive_transitions']} authored defensive-transition "
                f"interception(s), {reference['build_up_passes']} build-up pass(es), and "
                f"{reference['shots']} recorded shot(s) in this fictional fixture. "
                "This is a source-record description, not a player rating."
            )
            explanation_correct &= candidate["explanation"] == expected_text
        else:
            explanation_correct = False
        own = [e for e in events if e["player"]["name"] == name]
        own_ids = {e["id"] for e in own}
        support = candidate["supporting_event_ids"]
        opposing = candidate["opposing_event_ids"]
        cited = support + opposing + candidate["context_event_ids"]
        citations_correct &= bool(support) and all(e in by_id and e in own_ids for e in cited)
        citations_correct &= set(candidate["context_event_ids"]) == own_ids
        # The source's only recorded contrary action is an explicitly incomplete pass.
        expected_opposing = {
            e["id"] for e in own if e.get("pass", {}).get("outcome", {}).get("name") == "Incomplete"
        }
        contradiction_correct &= set(opposing) == expected_opposing
        intent = case["expected_intent"]
        if intent == "transition_buildup":
            expected_support = {
                e["id"] for e in own
                if e["demo_phase"] == "defensive_transition"
                or (e["demo_phase"] == "build_up" and e["id"] not in expected_opposing)
            }
        elif intent == "transition":
            expected_support = {e["id"] for e in own if e["demo_phase"] == "defensive_transition"}
        elif intent == "passes":
            expected_support = {
                e["id"] for e in own
                if e["type"]["name"] == "Pass" and e["id"] not in expected_opposing
            }
        elif intent == "shots":
            expected_support = {e["id"] for e in own if e["type"]["name"] == "Shot"}
        else:
            expected_support = own_ids
        citations_correct &= set(support) == expected_support
    tool_correct = result["query"]["intent"] == case["expected_intent"]
    return {
        "tool_selection_correct": tool_correct,
        "candidate_set_correct": candidates_correct,
        "abstention_correct": abstention_correct,
        "citation_correct": citations_correct if result["candidates"] else None,
        "numeric_correct": numeric_correct if result["candidates"] else None,
        "contradiction_correct": contradiction_correct if result["candidates"] else None,
        "explanation_whitelisted": explanation_correct if result["candidates"] else None,
        "task_complete": all((tool_correct, candidates_correct, abstention_correct,
                              citations_correct, numeric_correct, contradiction_correct,
                              explanation_correct)),
    }


def evaluate(cases: list[dict]) -> dict:
    events, _, identity = scout_fixture()
    teams = {e["player"]["name"]: e["team"]["name"] for e in events}
    outcomes = []
    for case in cases:
        result = search(case["prompt"])
        scores = grade(case, result, events)
        # This is exactly the existing discovery search's lowercase substring predicate,
        # applied to the complete request rather than a human-reformulated keyword.
        q = case["prompt"].strip().lower()
        baseline_names = sorted(
            name for name, team in teams.items() if q in f"{name} {team}".lower()
        )
        baseline_complete = (
            not case["expected_abstention"]
            and baseline_names == sorted(case["expected_candidates"])
            and bool(baseline_names)
        )
        outcomes.append({"case": case, "fallback": result, "grades": scores,
                         "discovery_proxy": {"candidate_names": baseline_names,
                                             "task_complete": baseline_complete}})
    def metric(field: str) -> dict:
        values = [row["grades"][field] for row in outcomes if row["grades"][field] is not None]
        return {"passed": sum(values), "total": len(values)}
    return {
        "method": ("Rule-based interpreter and raw-request discovery substring proxy; "
                   "no live model."),
        "fixture_sha256": identity["raw_sha256"],
        "case_count": len(cases),
        "fallback_metrics": {key: metric(key) for key in (
            "tool_selection_correct", "candidate_set_correct", "abstention_correct",
            "citation_correct", "numeric_correct", "contradiction_correct",
            "explanation_whitelisted", "task_complete",
        )},
        "discovery_proxy_task_completion": {
            "passed": sum(row["discovery_proxy"]["task_complete"] for row in outcomes),
            "total": len(outcomes),
        },
        "unsupported_claim_proxy": {
            "flagged": sum(
                row["grades"]["explanation_whitelisted"] is False for row in outcomes
            ),
            "total": sum(
                row["grades"]["explanation_whitelisted"] is not None for row in outcomes
            ),
            "scope": "Exact template check for candidate explanations only; "
            "not semantic evaluation of arbitrary model prose or abstentions.",
        },
        "unsupported_claim_rate": None,
        "unsupported_claim_rate_reason": (
            "Semantic claims in arbitrary text require independent review."
        ),
        "live_model_latency": None, "live_model_cost": None,
        "outcomes": outcomes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(CASES.read_text())
    report = evaluate(cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "outcomes"}, indent=2))


if __name__ == "__main__":
    main()
