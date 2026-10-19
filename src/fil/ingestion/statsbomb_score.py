"""StatsBomb-only scoring semantics over original provider records; never edits inputs."""

from fil.metrics.score import OfficialScore, ScoreError, ScoringSignal

_SHOT_OUTCOMES = {
    "Goal",
    "Blocked",
    "Off T",
    "Post",
    "Saved",
    "Wayward",
    "Saved Off Target",
    "Saved to Post",
}


def official_score(matches: list[dict], match_id: int) -> OfficialScore:
    """Read official team identity/final score from exactly one original metadata record."""
    try:
        rows = [m for m in matches if m["match_id"] == match_id]
        if len(rows) != 1:
            raise ScoreError("Expected one official match record")
        m = rows[0]
        return OfficialScore(
            m["match_id"],
            m["home_team"]["home_team_id"],
            m["away_team"]["away_team_id"],
            m["home_score"],
            m["away_score"],
        )
    except (KeyError, TypeError) as exc:
        raise ScoreError("Malformed official score metadata") from exc


def scoring_signals(events: list[dict]) -> tuple[ScoringSignal, ...]:
    """Shots (including misses) and own goals only; goalkeeper echoes never award goals."""
    result = []
    try:
        for e in events:
            name = e["type"]["name"]
            if name not in {"Shot", "Own Goal For", "Own Goal Against"}:
                continue
            if name == "Shot":
                shot = e["shot"]
                outcome = shot["outcome"]["name"]
                shot_type = shot["type"]["name"]
                if outcome not in _SHOT_OUTCOMES or shot_type not in {
                    "Open Play",
                    "Free Kick",
                    "Corner",
                    "Kick Off",
                    "Penalty",
                    "Other",
                }:
                    raise ScoreError("Unsupported shot outcome/type: score semantics unresolved")
                kind, scored, penalty = "shot", outcome == "Goal", shot_type == "Penalty"
            else:
                kind = "own_for" if name == "Own Goal For" else "own_against"
                scored, penalty = True, False
            links = e.get("related_events", [])
            if not isinstance(links, list) or any(not isinstance(i, str) for i in links):
                raise ScoreError("Malformed related event IDs")
            player = e.get("player")
            result.append(
                ScoringSignal(
                    e["id"],
                    kind,
                    e["team"]["id"],
                    player["id"] if player is not None else None,
                    scored,
                    penalty,
                    tuple(links),
                )
            )
    except (KeyError, TypeError) as exc:
        raise ScoreError("Malformed provider scoring fields; never infer missing outcomes") from exc
    return tuple(result)
