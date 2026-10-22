"""Descriptive player evidence, shared filters and complete native context links."""

import json
from pathlib import Path

import streamlit as st

from fil.explorer.possession import facts as possession_facts
from fil.explorer.tactical import facts as tactical_facts
from fil.ingestion.player_roster import load_roster
from fil.metrics.players import player_facts


@st.cache_resource(show_spinner="Verifying native lineup metadata…")
def roster(raw: str, match_id: int, source_manifest: str, content_key: str):
    return load_roster(Path(raw), match_id, source_manifest)


@st.cache_resource(show_spinner="Preparing source-linked player evidence…", max_entries=32)
def filtered_facts(
    _events,
    _selected,
    _possessions,
    _tactics,
    _native,
    content_key: str,
    selected_ids: tuple[str, ...],
):
    return player_facts(_events, _selected, _possessions, _tactics, _native)


def render(events, selected, meta: dict, state, content_key: str, raw: str) -> None:
    home, away = meta["home_team_id"], meta["away_team_id"]
    native = roster(raw, meta["match_id"], meta["source_manifest_sha256"], content_key)
    possessions = possession_facts(events, home, away, content_key)
    tactics = tactical_facts(events, home, away, content_key)
    facts = filtered_facts(
        events,
        selected,
        possessions,
        tactics,
        native,
        content_key,
        tuple(selected["event_id"].to_pylist()),
    )
    rows = facts.players.to_pylist()
    st.header("Player Evidence")
    st.caption(
        "Observed event involvement in this match. Shared filters select actor records. "
        "Full native shot/possession context remains traceable outside the window; "
        "participation is not causal chance creation or a player rating."
    )
    metrics = st.columns(3)
    metrics[0].metric("Observed actors", sum(r["selected_events"] > 0 for r in rows))
    metrics[1].metric("Pass-to-shot links", sum(r["native_shot_links"] for r in rows))
    metrics[2].metric("Completed passes", sum(r["completed_passes"] for r in rows))
    st.caption(
        "Per-100 values use each player’s selected owner-action records, including receipts; "
        "they are not touches, minutes or equal opportunity. Minutes/per-90 and inferred roles "
        "are unavailable. Geometry uses native +x; physical ends remain unknown."
    )
    include = st.toggle("Include roster records without selected events", key="player_roster_rows")
    visible = [
        r
        for r in rows
        if (r["selected_events"] > 0 or include)
        and state.team_id in (None, r["team_id"])
        and state.player_id in (None, r["player_id"])
    ]
    if not visible:
        st.info("No player actor records match this selection. No contribution inferred.")
        return
    keyed = {f"{r['team_id']}:{r['player_id']}": r for r in visible}
    if st.session_state.get("player_evidence_choice") not in keyed:
        st.session_state["player_evidence_choice"] = next(iter(keyed))
    choice = st.selectbox(
        "Player evidence record",
        list(keyed),
        key="player_evidence_choice",
        format_func=lambda k: f"{keyed[k]['player_name']} · {k}",
    )
    row = keyed[choice]
    groups = {
        "Involvement": {
            "player_name": "Player",
            "selected_events": "Records",
            "owner_actions": "Owner actions",
            "owner_possessions": "Possessions",
        },
        "Passing": {
            "player_name": "Player",
            "completed_passes": "Completed",
            "failed_passes": "Failed",
            "unknown_passes": "Unknown",
        },
        "Progression": {
            "player_name": "Player",
            "progressive_passes": "Passes",
            "progressive_carries": "Carries",
            "owner_progressions_per100_actions": "Per 100 owner actions",
        },
        "Shot context": {
            "player_name": "Player",
            "pre_shot_possessions": "Pre-shot sequences",
            "native_shot_links": "Native shot links",
            "native_linked_shot_xg": "Linked source xG",
        },
    }
    group = st.selectbox("Player table measures", list(groups), key="player_table_group")
    columns = groups[group]
    with st.container(border=True):
        st.markdown(f"**Selected player · {row['player_name']}**")
        for field, label in columns.items():
            if field == "player_name":
                continue
            value = row[field]
            display = (
                "Unavailable"
                if value is None
                else (f"{value:.3f}" if isinstance(value, float) else str(value))
            )
            st.markdown(f"- {label}: **{display}**")
    st.caption(
        "Compare players in the table below; swipe horizontally on a narrow screen. "
        "The selected player's measures above do not require table scrolling."
    )
    import pyarrow as pa

    st.dataframe(
        pa.Table.from_pylist(visible, schema=facts.players.schema).select(list(columns)),
        hide_index=True,
        height=250,
        column_config={
            k: st.column_config.Column(v, width="large" if k == "player_name" else "small")
            for k, v in columns.items()
        },
    )
    st.caption(
        f"{len(visible)} player records · table follows shared filters. "
        f"Evidence below: {row['player_name']} · {choice}. "
        "Counts describe recorded involvement, not a ranking."
    )
    evidence = {
        "Selected actor records": row["event_ids"],
        "Owner-action participation": row["owner_action_ids"],
        "Progressive passes/carries": row["progression_ids"],
        "Recorded actions preceding a shot": row["pre_shot_action_ids"],
        "Native linked passes": row["linked_pass_ids"],
        "Context shots": list(dict.fromkeys(row["context_shot_ids"] + row["linked_shot_ids"])),
    }
    kind = st.selectbox("Player evidence type", list(evidence), key="player_evidence_type")
    ids = evidence[kind]
    if not ids:
        st.info("No original events for this evidence type in the selection.")
    else:
        if st.session_state.get("player_original_event") not in ids:
            st.session_state["player_original_event"] = ids[0]
        eid = st.selectbox("Player original event", ids, key="player_original_event")
        original = events.slice(events["event_id"].to_pylist().index(eid), 1).to_pylist()[0]
        st.code(eid, language=None)
        st.caption(
            f"P{original['period']} · {original['display_clock']} · matches shared filter: "
            f"{eid in set(selected['event_id'].to_pylist())} · "
            f"native possession {original['possession_id']}"
        )
        st.json(json.loads(original["source_record_json"]), expanded=False)
        st.caption(f"Source manifest {original['source_manifest_sha256']}")
    st.subheader("Native position metadata")
    if row["position_metadata"]:
        st.json(json.loads(row["position_metadata"]), expanded=False)
    else:
        st.info("No certified position metadata for this record.")
    st.caption(
        f"Metadata source: {row['metadata_source_locator']} · "
        f"manifest {row['source_manifest_sha256']}"
    )
    st.caption("Native lineup intervals are metadata, not tracking or certified minute exposure.")
    st.subheader("Evidence and limits")
    st.json(
        {k: v for k, v in row.items() if k not in ("position_metadata", "event_ids")},
        expanded=False,
    )
    st.caption(
        "Pre-shot actions can belong to multiple participants and are not additive credit. "
        "Only reciprocal source pass/shot keys certify a direct link; linked xG is a descriptive "
        "context sum, not an inferred xA model. Same-match records only; no peer ranking."
    )
    if st.toggle("Show native link audit", key="player_link_audit"):
        st.dataframe(facts.links, hide_index=True)
        st.json(facts.quality)
