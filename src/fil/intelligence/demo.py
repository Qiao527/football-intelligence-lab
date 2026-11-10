"""Self-authored fictional matches. No provider records or fitted probabilities.

The StatsBomb-shaped fields exercise the same adapter as local research data.
Every weight is illustrative, never calibrated xG or scientific evidence.
"""

import hashlib
import json

MATCHES = {
    "demo-1": ("Northbridge FC", "Harbour Athletic"),
    "demo-2": ("Atlas United", "Riverside FC"),
    "demo-3": ("Beacon City", "Westhaven Town"),
}


def load_demo(match_id: str) -> tuple[list[dict], dict, dict]:
    """Generate repeatable fictional actions; reports are computed elsewhere."""
    home, away = MATCHES[match_id]
    variant = list(MATCHES).index(match_id)
    rows = []

    def action(period, minute, possession, team, kind, **extra):
        i = len(rows) + 1
        row = dict(
            id=f"{match_id}-action-{i:03d}",
            index=i,
            period=period,
            timestamp=f"00:{minute:02d}:{i % 30:02d}.000",
            minute=minute + (45 if period == 2 else 0),
            second=i % 30,
            possession=possession,
            possession_team={"id": team, "name": home if team == 901 else away},
            team={"id": team, "name": home if team == 901 else away},
            type={"name": kind},
            play_pattern={"name": "From Corner" if possession % 4 == 0 else "Regular Play"},
            **extra,
        )
        if kind not in {"Half Start", "Half End"}:
            row["player"] = {"id": team * 10 + i % 4, "name": f"Fictional player {i % 4 + 1}"}
        rows.append(row)

    for period in (1, 2):
        action(period, 0, period * 100, 901, "Half Start")
        for unit in range(1, 9):
            team = 901 if (unit + variant) % 2 else 902
            possession = period * 100 + unit
            minute = unit * 4
            for move in range(3):
                action(
                    period,
                    minute,
                    possession,
                    team,
                    "Pass",
                    location=[25 + move * 20, 25 + unit % 4 * 8],
                    **{
                        "pass": {
                            "end_location": [45 + move * 20, 30],
                            "recipient": {
                                "id": team * 10 + (len(rows) + 2) % 4,
                                "name": "Fictional recipient",
                            },
                        }
                    },
                )
            if not (variant == 2 and period == 2) and unit % 3 != 0:
                n = 2 if unit == 4 + variant else 1
                for shot in range(n):
                    goal = (unit + period + variant + shot) % 5 == 0
                    weight = round(0.06 + ((unit * 3 + period + variant + shot) % 9) * 0.045, 3)
                    action(
                        period,
                        minute,
                        possession,
                        team,
                        "Shot",
                        location=[92 + unit, 28 + unit],
                        shot={
                            "statsbomb_xg": weight,
                            "outcome": {"name": "Goal" if goal else "Saved"},
                            "type": {"name": "Open Play"},
                        },
                    )
        action(period, 45, period * 100 + 9, 902, "Half End")
    metadata = dict(
        match_id=100001 + variant,
        match_date="Fictional fixture",
        home_team={"home_team_id": 901, "home_team_name": home},
        away_team={"away_team_id": 902, "away_team_name": away},
        home_score=sum(
            e["type"]["name"] == "Shot"
            and e["team"]["id"] == 901
            and e["shot"]["outcome"]["name"] == "Goal"
            for e in rows
        ),
        away_score=sum(
            e["type"]["name"] == "Shot"
            and e["team"]["id"] == 902
            and e["shot"]["outcome"]["name"] == "Goal"
            for e in rows
        ),
    )
    identity = dict(
        mode="synthetic",
        source="Self-authored fictional demonstration",
        source_revision="fil-fictional-fixtures-1",
        raw_sha256=hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
        physical_time_certified=False,
        rights="Self-authored synthetic demonstration; contains no provider records.",
    )
    return rows, metadata, identity
