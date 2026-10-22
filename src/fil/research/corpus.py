"""Offline corpus contracts; no new provider acquisition or rights grant."""

import hashlib
import json
from dataclasses import dataclass

import pyarrow as pa

from fil.ingestion.statsbomb_possessions import source_records
from fil.research.exposure import chronology

VERSION = "fil-research-corpus-2"
# Exact scope in SOURCE_POLICY.md. Adding another match requires a rights review.
AUTHORISED = frozenset(
    {
        (
            "statsbomb_open_data",
            8658,
            "f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c",
        )
    }
)


@dataclass(frozen=True)
class MatchEvidence:
    events: pa.Table
    metadata: dict
    roster: list[dict]


def assemble(matches: list[MatchEvidence], *, authorisations=AUTHORISED) -> tuple[pa.Table, dict]:
    """Preserve canonical tables and source IDs; identity never uses name matching.

    Low-level authorisations parameter supports offline TEST_ONLY contracts. The
    production CLI uses the reviewed fixed registry, with no allow-unreviewed flag.
    """
    if not matches:
        raise ValueError("Empty corpus")
    seen = set()
    players = {}
    reports = []
    schema = matches[0].events.schema
    for match in matches:
        events, meta, roster = match.events, match.metadata, match.roster
        if not events.schema.equals(schema, check_metadata=True):
            raise ValueError("Mixed canonical schemas/versions")
        sources = set(events["source"].to_pylist())
        mids = set(events["match_id"].to_pylist())
        manifests = set(events["source_manifest_sha256"].to_pylist())
        if len(sources) != 1 or len(mids) != 1 or len(manifests) != 1 or not events.num_rows:
            raise ValueError("Expected one source/match/manifest per input")
        source, mid, manifest = next(iter(sources)), next(iter(mids)), next(iter(manifests))
        if source != "statsbomb_open_data":
            raise ValueError("Unsupported event semantics/provider")
        if (source, mid, manifest) not in authorisations:
            raise ValueError("Match outside reviewed data-use authorisation")
        if meta["match_id"] != mid or meta["source_manifest_sha256"] != manifest:
            raise ValueError("Metadata/source identity mismatch")
        if (source, mid) in seen:
            raise ValueError("Duplicate corpus match; never pseudoreplicate")
        seen.add((source, mid))
        source_records(events)  # Verify canonical/native semantics, IDs and ordering.
        keys = [(source, mid, e) for e in events["event_id"].to_pylist()]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate compound original-event identity")
        roster_keys = {(r["team_id"], r["player_id"]) for r in roster}
        if len(roster_keys) != len(roster):
            raise ValueError("Duplicate roster team/player identity")
        for r in roster:
            key = (source, r["player_id"])
            row = players.setdefault(
                key,
                dict(
                    source=source,
                    provider_player_id=r["player_id"],
                    identity_key=f"{source}:player:{r['player_id']}",
                    aliases=set(),
                    memberships=set(),
                ),
            )
            if r.get("player_name"):
                row["aliases"].add(r["player_name"])
            row["memberships"].add((mid, r["team_id"]))
        for r in events.select(["player_id", "player_name", "team_id"]).to_pylist():
            if r["player_id"] is None:
                continue
            identity = (source, r["player_id"])
            row = players.setdefault(
                identity,
                dict(
                    source=source,
                    provider_player_id=r["player_id"],
                    identity_key=f"{source}:player:{r['player_id']}",
                    aliases=set(),
                    memberships=set(),
                ),
            )
            if r["player_name"]:
                row["aliases"].add(r["player_name"])
            if r["team_id"] is not None:
                row["memberships"].add((mid, r["team_id"]))
        census = chronology(events, roster)
        reports.append(
            dict(
                source=source,
                match_id=mid,
                match_date=meta["match_date"],
                source_manifest_sha256=manifest,
                event_rows=events.num_rows,
                original_ids=events["event_id"].to_pylist(),
                null_counts={k: events[k].null_count for k in events.column_names},
                actorless_events=events["player_id"].null_count,
                unrostered_actors=sorted(
                    {
                        (r["team_id"], r["player_id"])
                        for r in events.to_pylist()
                        if r["player_id"] is not None
                    }
                    - roster_keys
                ),
                unknown_semantic_records=sum(bool(x) for x in events["quality_flags"].to_pylist()),
                exposure=census,
            )
        )
    identities = [
        {
            **p,
            "aliases": sorted(p["aliases"]),
            "memberships": [dict(match_id=m, team_id=t) for m, t in sorted(p["memberships"])],
        }
        for _, p in sorted(players.items())
    ]
    conflicts = []
    for row in identities:
        by_match = {}
        for membership in row["memberships"]:
            by_match.setdefault(membership["match_id"], set()).add(membership["team_id"])
        for mid, teams in by_match.items():
            if len(teams) > 1:
                conflicts.append(
                    dict(identity_key=row["identity_key"], match_id=mid, team_ids=sorted(teams))
                )
    table = pa.concat_tables([m.events for m in matches])
    report = dict(
        version=VERSION,
        matches=reports,
        identities=identities,
        identity_conflicts=conflicts,
        match_count=len(matches),
        event_rows=table.num_rows,
        generalisation_status="insufficient_evidence",
        identity_limits=(
            "Provider IDs only; aliases retained, never used for merges; "
            "cross-provider linkage unsupported"
        ),
    )
    report["definition_sha256"] = hashlib.sha256(
        json.dumps(
            dict(
                version=VERSION,
                identity="source/provider_player_id",
                event="source/match_id/original_event_id",
            ),
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return table, report
