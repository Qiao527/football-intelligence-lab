"""Observed player involvement v1, never an ability rating or causal allocation."""

import json
import math
from dataclasses import dataclass

import pyarrow as pa

VERSION = "fil-player-involvement-1"
SCHEMA = pa.schema(
    [
        *[
            (n, pa.string())
            for n in (
                "source",
                "player_name",
                "position_metadata",
                "metadata_status",
                "metadata_source_locator",
                "source_manifest_sha256",
                "metric_version",
            )
        ],
        *[
            (n, pa.int64())
            for n in (
                "match_id",
                "team_id",
                "player_id",
                "selected_events",
                "owner_actions",
                "owner_possessions",
                "passes",
                "completed_passes",
                "failed_passes",
                "unknown_passes",
                "progressive_passes",
                "progressive_carries",
                "owner_progressive_actions",
                "pre_shot_possessions",
                "native_shot_links",
            )
        ],
        *[
            (n, pa.float64())
            for n in (
                "known_pass_completion_fraction",
                "owner_progressions_per100_actions",
                "native_linked_shot_xg",
                "minutes_played",
            )
        ],
        *[
            (n, pa.list_(pa.string()))
            for n in (
                "event_ids",
                "owner_action_ids",
                "completed_pass_ids",
                "progression_ids",
                "pre_shot_action_ids",
                "context_shot_ids",
                "linked_pass_ids",
                "linked_shot_ids",
            )
        ],
        ("possession_ids", pa.list_(pa.int64())),
    ],
    metadata={b"fil.player_metric_version": VERSION.encode()},
)
LINK_SCHEMA = pa.schema(
    [
        ("pass_event_id", pa.string()),
        ("shot_event_id", pa.string()),
        ("status", pa.string()),
        ("reason", pa.string()),
        ("shot_xg", pa.float64()),
    ]
)


@dataclass(frozen=True)
class PlayerFacts:
    players: pa.Table
    links: pa.Table
    quality: dict


def native_shot_links(events: pa.Table) -> pa.Table:
    """Only reciprocal provider pass/shot keys certify a direct shot link."""
    rows = events.select(
        [
            "event_id",
            "team_id",
            "period",
            "provider_index",
            "event_type",
            "source_record_json",
            "shot_xg",
        ]
    ).to_pylist()
    by_id = {r["event_id"]: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError("Duplicate original event IDs")
    source = {r["event_id"]: json.loads(r["source_record_json"]) for r in rows}
    pairs = set()
    for r in rows:
        e = source[r["event_id"]]
        if r["event_type"] == "Pass" and e.get("pass", {}).get("assisted_shot_id"):
            pairs.add((r["event_id"], e["pass"]["assisted_shot_id"]))
        if r["event_type"] == "Shot" and e.get("shot", {}).get("key_pass_id"):
            pairs.add((e["shot"]["key_pass_id"], r["event_id"]))
    result = []
    for pid, sid in sorted(
        pairs, key=lambda p: (by_id.get(p[0], {}).get("provider_index", 10**12), p)
    ):
        a, b = by_id.get(pid), by_id.get(sid)
        valid = bool(
            a
            and b
            and a["event_type"] == "Pass"
            and b["event_type"] == "Shot"
            and a["period"] == b["period"]
            and a["period"] in (1, 2, 3, 4)
            and a["team_id"] == b["team_id"]
            and a["provider_index"] < b["provider_index"]
            and source[pid]["pass"].get("assisted_shot_id") == sid
            and source[sid]["shot"].get("key_pass_id") == pid
        )
        if valid and (
            b["shot_xg"] is None or not math.isfinite(b["shot_xg"]) or not 0 <= b["shot_xg"] <= 1
        ):
            raise ValueError("Invalid linked source shot xG")
        result.append(
            {
                "pass_event_id": pid,
                "shot_event_id": sid,
                "status": "verified" if valid else "unverified",
                "reason": "reciprocal_native_keys"
                if valid
                else "missing_or_inconsistent_native_link",
                "shot_xg": b["shot_xg"] if valid else None,
            }
        )
    return pa.Table.from_pylist(result, schema=LINK_SCHEMA)


def player_facts(
    events: pa.Table, selected: pa.Table, possessions, tactical, roster: list[dict]
) -> PlayerFacts:
    """Count selected actor records; shot context is complete native evidence, not credit."""
    sources = set(events["source"].to_pylist())
    matches = set(events["match_id"].to_pylist())
    if len(matches) != 1 or len(sources) != 1:
        raise ValueError("Expected one source and match")
    if len(set(events["event_id"].to_pylist())) != events.num_rows:
        raise ValueError("Duplicate IDs")
    source = next(iter(sources))
    match_id = next(iter(matches))
    ids = set(selected["event_id"].to_pylist())
    if not ids <= set(events["event_id"].to_pylist()):
        raise ValueError("Foreign selection ID")
    # Embedded source identity was checked by possession reconstruction; retain originals.
    fields = [
        "event_id",
        "team_id",
        "player_id",
        "player_name",
        "provider_index",
        "period",
        "possession_id",
        "event_type",
    ]
    records = events.select(fields).to_pylist()
    actors = {}
    for r in records:
        if r["player_id"] is not None and r["team_id"] is not None:
            actors.setdefault(
                (r["team_id"], r["player_id"]), {"player_name": r["player_name"], "positions": None}
            )
    roster_seen = set()
    for r in roster:
        key = (r["team_id"], r["player_id"])
        if key in roster_seen:
            raise ValueError("Duplicate roster team/player ID")
        roster_seen.add(key)
        actors[key] = r
    actions = {r["event_id"]: r for r in possessions.actions.to_pylist()}
    if set(actions) != set(events["event_id"].to_pylist()):
        raise ValueError("Possession lineage mismatch")
    tacts = {r["event_id"]: r for r in tactical.actions.to_pylist()}
    linked = native_shot_links(events)
    links = linked.to_pylist()
    output = []
    chains = possessions.possessions.to_pylist()
    by_record = {r["event_id"]: r for r in records}
    for (team, player), meta in sorted(actors.items()):
        rows = [
            r
            for r in records
            if (r["team_id"], r["player_id"]) == (team, player) and r["event_id"] in ids
        ]
        evidence = [r["event_id"] for r in rows]
        own = [actions[i] for i in evidence if actions[i]["is_owner_action"]]
        passes = [tacts[i] for i in evidence if i in tacts and tacts[i]["event_type"] == "Pass"]
        complete = [r["event_id"] for r in passes if r["status"] == "completed"]
        failed = sum(r["status"] == "failed" for r in passes)
        progressive = [tacts[i] for i in evidence if i in tacts and tacts[i]["progressive"] is True]
        own_progress = sum(r["progressive"] is True for r in own)
        preshot = []
        context = []
        sequence_ids = []
        for chain in chains:
            before = set()
            for sid in chain["shot_event_ids"]:
                shot = by_record[sid]
                contributing = [
                    r["event_id"]
                    for r in own
                    if r["event_id"] in chain["owner_action_ids"]
                    and r["period"] == shot["period"]
                    and r["provider_index"] < shot["provider_index"]
                ]
                if contributing:
                    before.update(contributing)
                    context.append(sid)
            if before:
                preshot.extend(sorted(before, key=lambda i: by_record[i]["provider_index"]))
                sequence_ids.append(chain["possession_id"])
        direct = [
            link
            for link in links
            if link["status"] == "verified" and link["pass_event_id"] in evidence
        ]
        positions = meta.get("positions")
        output.append(
            {
                "source": source,
                "match_id": match_id,
                "team_id": team,
                "player_id": player,
                "player_name": meta.get("player_name"),
                "position_metadata": json.dumps(positions, sort_keys=True) if positions else None,
                "metadata_status": "native_positions" if positions else "position_unknown",
                "metadata_source_locator": meta.get("source_pointer"),
                "source_manifest_sha256": events["source_manifest_sha256"][0].as_py(),
                "selected_events": len(rows),
                "owner_actions": len(own),
                "owner_possessions": len({r["possession_id"] for r in own}),
                "passes": len(passes),
                "completed_passes": len(complete),
                "failed_passes": failed,
                "unknown_passes": len(passes) - len(complete) - failed,
                "known_pass_completion_fraction": len(complete) / (len(complete) + failed)
                if len(complete) + failed
                else None,
                "progressive_passes": sum(r["event_type"] == "Pass" for r in progressive),
                "progressive_carries": sum(r["event_type"] == "Carry" for r in progressive),
                "owner_progressive_actions": own_progress,
                "owner_progressions_per100_actions": 100 * own_progress / len(own) if own else None,
                "pre_shot_possessions": len(sequence_ids),
                "native_shot_links": len(direct),
                "native_linked_shot_xg": math.fsum(link["shot_xg"] for link in direct),
                "minutes_played": None,
                "event_ids": evidence,
                "owner_action_ids": [r["event_id"] for r in own],
                "completed_pass_ids": complete,
                "progression_ids": [r["event_id"] for r in progressive],
                "possession_ids": sorted({r["possession_id"] for r in own}),
                "pre_shot_action_ids": preshot,
                "context_shot_ids": list(dict.fromkeys(context)),
                "linked_pass_ids": [link["pass_event_id"] for link in direct],
                "linked_shot_ids": [link["shot_event_id"] for link in direct],
                "metric_version": VERSION,
            }
        )
    return PlayerFacts(
        pa.Table.from_pylist(output, schema=SCHEMA),
        linked,
        {
            "version": VERSION,
            "source_events": events.num_rows,
            "selected_events": selected.num_rows,
            "selected_unattributed_actor_events": sum(
                r["player_id"] is None for r in selected.to_pylist()
            ),
            "verified_native_shot_links": sum(link["status"] == "verified" for link in links),
            "unverified_native_shot_links": sum(link["status"] != "verified" for link in links),
            "minutes": "not certified; no per90",
            "limits": "single-match observed participation; not causal contribution",
        },
    )


def combine_matches(tables: list[pa.Table]) -> pa.Table:
    """Stable per-source/match/team/player grain; never imply cross-match validation."""
    if not tables:
        return pa.Table.from_pylist([], schema=SCHEMA)
    if any(not t.schema.equals(SCHEMA, check_metadata=True) for t in tables):
        raise ValueError("Metric version/schema mismatch")
    result = pa.concat_tables(tables)
    keys = [
        tuple(r[k] for k in ("source", "match_id", "team_id", "player_id"))
        for r in result.to_pylist()
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate match/player key")
    return result
