"""Reconcile only unchanged self-authored demonstration fixtures."""

from fil.intelligence.demo import MATCHES, load_demo


def synthetic_score(raw: list[dict], metadata: dict) -> dict:
    """Refuse anything other than an exact built-in fixture before counting its goals."""
    if not any((raw, metadata) == load_demo(mid)[:2] for mid in MATCHES):
        raise ValueError("Only the built-in fictional matches are supported")
    teams = [metadata[side][side + "_id"] for side in ("home_team", "away_team")]
    totals = [0, 0]
    decisions = []
    for event in raw:
        if event["type"]["name"] != "Shot":
            continue
        scored = event["shot"]["outcome"]["name"] == "Goal"
        beneficiary = event["team"]["id"]
        totals[teams.index(beneficiary)] += int(scored)
        decisions.append(
            {
                "source_event_ids": [event["id"]],
                "provider_index": event["index"],
                "period": event["period"],
                "beneficiary_team_id": beneficiary,
                "scored": scored,
                "domain": "match_play",
            }
        )
    if totals != [metadata["home_score"], metadata["away_score"]]:
        raise ValueError("Fictional score disagrees with fixture")
    return {
        "match_play": totals,
        "shootout": [0, 0],
        "decisions": decisions,
        "shootout_official_reconciliation": "unavailable",
        "physical_timing_certified": False,
    }
