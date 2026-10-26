"""Exact source accounting and bounded review questions, never a relevance oracle.

All match-play Shots enter the baseline. A native membership is the tuple
(period, possession ID, possession team); it is an annotation, not certified
continuous control. Deletion is arithmetic, not a counterfactual match.
"""

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

from fil.intelligence import VERSION
from fil.research.eligibility import ordered_score

CLAIM_STANDARDS = {
    "Match fact": "Original records and an explicit reproducible definition can suffice.",
    "Repeated pattern": "Needs distinct episodes, opportunities, context and counterexamples.",
    "Explanatory hypothesis": "Needs discriminating evidence against competing explanations.",
    "General capability": "Needs independent longitudinal evidence and construct validity.",
}
LIMITATIONS = [
    "Football usefulness has not been independently evaluated. Baseline-reproducible facts "
    "are review aids, not demonstrated novel discoveries.",
    "Native possession membership is a provider annotation, not continuous team control.",
    "No physical direction, off-ball movement, perception, tactical intention or causal "
    "player contribution is inferred.",
    "No certified physical minutes, per-90 ability, stable player quality or general rule.",
    "All existing real matches are development-exposed; no independent confirmation.",
]


def native(event: dict) -> tuple | None:
    """Keep missing native possession membership unresolved, not a zero-valued group."""
    owner = (event.get("possession_team") or {}).get("id")
    possession = event.get("possession")
    if type(possession) is not int or type(owner) is not int:
        return None
    return event["period"], possession, owner


def weight(event: dict) -> Decimal | None:
    value = event["shot"].get("statsbomb_xg")
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Invalid shot weight") from exc
    if not result.is_finite() or not 0 <= result <= 1:
        raise ValueError("Invalid shot weight; expected finite probability in [0,1]")
    return result


def validate(raw: list[dict], metadata: dict) -> dict:
    """Validate identity/order and reuse the independently tested score reconciler."""
    if not raw or any(not isinstance(e.get("id"), str) or not e["id"] for e in raw):
        raise ValueError("Nonempty original event identities required")
    if len({e["id"] for e in raw}) != len(raw):
        raise ValueError("Duplicate original event ID")
    teams = {metadata[s][s + "_id"] for s in ("home_team", "away_team")}
    if len(teams) != 2:
        raise ValueError("Distinct team identities required")
    if any(
        type(e.get("index")) is not int
        or e["index"] < 1
        or type(e.get("period")) is not int
        or e["period"] not in (1, 2, 3, 4, 5)
        or (e.get("team") or {}).get("id") not in teams
        for e in raw
    ):
        raise ValueError("Invalid source order, period or team identity")
    if any(
        a["index"] >= b["index"] or a["period"] > b["period"]
        for a, b in zip(raw, raw[1:], strict=False)
    ):
        raise ValueError("Source sequence reversed")
    for e in raw:
        if e["type"]["name"] == "Pass" and not isinstance(e.get("pass"), dict):
            raise ValueError("Missing provider pass semantics")
        if e["type"]["name"] == "Shot":
            weight(e)
    return ordered_score(raw, metadata)


def analyze(
    raw: list[dict],
    metadata: dict,
    identity: dict,
    *,
    period: int | None = None,
    team: int | None = None,
) -> dict:
    """Compute the report from actions, with all exclusions and exact evidence IDs.

    Priority cards are selected by explicit arithmetic influence, not by an
    importance score. Every eligible group remains in the comparison baseline.
    Missing xG blocks sums for the selection; known-only totals never imply zero.
    """
    score = validate(raw, metadata)
    if identity.get("mode") not in ("synthetic", "local"):
        raise ValueError("Explicit synthetic or local source classification required")
    teams = [metadata[s][s + "_id"] for s in ("home_team", "away_team")]
    if period is not None and period not in (1, 2, 3, 4):
        raise ValueError("Only match-play period filters are supported")
    if team is not None and team not in teams:
        raise ValueError("Unknown team filter")
    rows = [
        e
        for e in raw
        if e["period"] < 5
        and (period is None or e["period"] == period)
        and (team is None or e["team"]["id"] == team)
    ]
    shots = [e for e in rows if e["type"]["name"] == "Shot"]
    missing = [e["id"] for e in shots if weight(e) is None]
    sums_available = not missing

    def total(es):
        return str(sum((weight(e) for e in es), Decimal(0))) if sums_available else None

    def delta(es):
        return (
            str(
                sum(
                    (weight(e) * (1 if e["team"]["id"] == teams[0] else -1) for e in es), Decimal(0)
                )
            )
            if sums_available
            else None
        )

    # Team is part of the group key: opponent annotations do not become owner Shots.
    groups = defaultdict(list)
    excluded_membership = []
    for e in shots:
        n = native(e)
        if n is None or n[2] not in teams:
            excluded_membership.append(e["id"])
        else:
            groups[n + (e["team"]["id"],)].append(e)
    context = defaultdict(list)
    for e in raw:
        context[native(e)].append(e["id"])
    units = []
    for key, es in sorted(groups.items()):
        ids = {e["id"] for e in es}
        other = [e for e in shots if e["id"] not in ids]
        units.append(
            dict(
                key=list(key),
                team_id=key[3],
                period=key[0],
                possession_id=key[1],
                owner_team_id=key[2],
                shot_count=len(es),
                shot_weight=total(es),
                event_ids=[e["id"] for e in es],
                context_event_ids=context[key[:3]],
                complement_event_ids=[e["id"] for e in other],
                complement_difference=delta(other),
                phase_labels=sorted(
                    {(e.get("play_pattern") or {}).get("name") or "Unknown" for e in es}
                ),
            )
        )
    phases = []
    for tid in teams:
        labels = sorted(
            {
                (e.get("play_pattern") or {}).get("name") or "Unknown"
                for e in shots
                if e["team"]["id"] == tid
            }
        )
        for label in labels:
            es = [
                e
                for e in shots
                if e["team"]["id"] == tid
                and ((e.get("play_pattern") or {}).get("name") or "Unknown") == label
            ]
            phases.append(
                dict(
                    team_id=tid,
                    phase=label,
                    shot_count=len(es),
                    shot_weight=total(es),
                    event_ids=[e["id"] for e in es],
                )
            )
    cards = []
    if sums_available and units:
        # A UI page size, not an eligibility or football relevance threshold.
        priorities = sorted(units, key=lambda u: (-Decimal(u["shot_weight"]), u["key"]))
        for u in priorities[:3]:
            label = "Multi-shot membership" if u["shot_count"] > 1 else "Single-shot membership"
            cards.append(
                dict(
                    id="unit-" + "-".join(map(str, u["key"])),
                    title=label,
                    scope="Match fact",
                    source_status="Source arithmetic verified",
                    independent_relevance=None,
                    baseline_reproducible=True,
                    observation=(
                        f"{u['shot_count']} recorded Shot(s) in native membership "
                        f"{u['possession_id']} contribute {u['shot_weight']} "
                        "to this selection's shot-weight sum."
                    ),
                    unit=u,
                    question="Would reviewing these actions change the analyst's account of "
                    "chance creation, or merely repeat the ordinary shot ledger?",
                    alternatives=[
                        "A single annotated chance can dominate a small sample.",
                        "Phase, score context and unequal opportunities may explain totals.",
                        "Multiple Shots in one membership need not reflect a repeated tactic.",
                    ],
                    falsifier="If the full ledger already answers the analyst's question equally "
                    "well, this card adds no demonstrated analytical value.",
                )
            )
    passes = [e for e in rows if e["type"]["name"] == "Pass"]
    return dict(
        version=VERSION,
        match_id=metadata["match_id"],
        provenance=identity,
        selection=dict(period=period, team_id=team),
        source_event_count=len(raw),
        selected_event_count=len(rows),
        selected_event_ids=[e["id"] for e in rows],
        score=score["match_play"],
        shootout=score["shootout"],
        shootout_reconciliation=score["shootout_official_reconciliation"],
        excluded_shootout_event_ids=[e["id"] for e in raw if e["period"] == 5],
        shots=[
            dict(
                event_id=e["id"],
                index=e["index"],
                period=e["period"],
                timestamp=e["timestamp"],
                team_id=e["team"]["id"],
                player=(e.get("player") or {}).get("name", "Unknown"),
                outcome=e["shot"]["outcome"]["name"],
                weight=str(weight(e)) if weight(e) is not None else None,
                location=e.get("location"),
                native=list(native(e)) if native(e) else None,
            )
            for e in shots
        ],
        shot_count=len(shots),
        shot_weight=total(shots),
        home_minus_away=delta(shots),
        team_totals=[
            dict(
                team_id=t,
                shot_count=sum(e["team"]["id"] == t for e in shots),
                shot_weight=total([e for e in shots if e["team"]["id"] == t]),
            )
            for t in teams
        ],
        pass_count=len(passes),
        completed_pass_count=sum("outcome" not in e.get("pass", {}) for e in passes),
        unknown_pass_outcome_ids=[
            e["id"]
            for e in passes
            if "outcome" in e.get("pass", {}) and e["pass"]["outcome"] is None
        ],
        phase_totals=phases,
        native_units=units,
        review_cards=cards,
        missing_shot_weight_ids=missing,
        unresolved_membership_shot_ids=excluded_membership,
        selected_event_types=dict(Counter(e["type"]["name"] for e in rows)),
        abstention=(
            "No recorded Shots in this selection."
            if not shots
            else "Missing shot weights: accounting cards withheld; source ledger retained."
            if missing
            else "No eligible native memberships; source ledger retained."
            if not units
            else None
        ),
        insight_status="Independent football usefulness unmeasured",
        validated_tactical_patterns=[],
        validated_explanations=[],
        validated_capabilities=[],
        claim_standards=CLAIM_STANDARDS,
        limitations=LIMITATIONS,
        definitions=dict(
            shot_weight="Source shot.statsbomb_xg for real data; uncalibrated illustrative "
            "weights for fictional fixtures. Match-play periods 1–4 only.",
            completed_pass="StatsBomb Pass with absent outcome; explicit null is unresolved.",
            priority="Descending native-membership Shot-weight total; at most three cards. "
            "All groups remain available. No football importance or novelty ranking.",
            complement="Remove listed Shot IDs from this selection and re-sum. "
            "Arithmetic accounting only, never a simulated alternative match.",
            spatial="Unflipped raw provider coordinates; physical direction uncertified.",
        ),
    )
