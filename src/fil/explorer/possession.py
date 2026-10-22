"""Possession Flow: full native context behind shared event-filter matches."""

import hashlib
import json
from collections import Counter

import plotly.graph_objects as go
import pyarrow as pa
import streamlit as st

from fil.possessions.extract import process_summary, reconstruct, select_possessions


@st.cache_resource(show_spinner="Auditing native possession memberships…")
def facts(_events, home: int, away: int, content_key: str):
    return reconstruct(_events, home, away)


def render(events, selected, meta: dict, content_key: str, figure) -> None:
    bundle = facts(events, meta["home_team_id"], meta["away_team_id"], content_key)
    cohort = select_possessions(bundle, selected)
    rows = cohort.to_pylist()
    selected_ids = set(selected["event_id"].to_pylist())
    token = hashlib.sha256(
        (
            str(st.session_state.get("selection_epoch", 0))
            + "|"
            + "|".join(selected["event_id"].to_pylist())
        ).encode()
    ).hexdigest()[:12]
    st.header("Possession Flow")
    st.caption(
        "Provider-ID sequences retain every owner, opponent and context event. "
        "Shared filters select matching events; the cohort includes each touched possession "
        "in full. Context actions outside the filter are explicitly marked. "
        "Team filters refer to acting team, not possession owner."
    )
    cols = st.columns(4)
    cols[0].metric("Touched native possessions", len(rows))
    cols[1].metric("Possessions containing shots", sum(r["shot_count"] > 0 for r in rows))
    cols[2].metric("Supported turnover endings", sum(r["turnover"] for r in rows))
    cols[3].metric("Native final-third reached", sum(r["reached_final_third"] for r in rows))
    st.caption(
        "Native 120×80, y down; +x zones/progression are declared conventions. "
        "Physical attacking directions remain unknown. No off-ball movement or intent inferred. "
        "Time spans include event gaps/stoppages; they are not live-ball possession time."
    )
    if not rows:
        st.info("No native possession matches this event selection. No sequence inferred.")
        return
    summary = process_summary(cohort)
    st.subheader("Same-possession co-occurrence · whole touched possessions")
    rates = st.columns(3)
    denominator = summary["observed_final_third_denominator"]
    rates[0].metric(
        "Shot / final-third possessions",
        f"{summary['shot_and_final_third_numerator']} / {denominator}",
    )
    rates[1].metric(
        "Box / final-third possessions",
        f"{summary['box_and_final_third_numerator']} / {denominator}",
    )
    value = summary["xg_per_possession"]
    rates[2].metric("Source xG / eligible possession", "NA" if value is None else f"{value:.4f}")
    st.caption(
        "Co-occurrence does not establish event order. Denominators count eligible "
        "possessions with observed "
        "native final-third evidence, including ones starting there. Not pass counts. "
        "Time-to-shot includes only shot-producing same-period possessions. "
        "The fixed official score and selected-event xG above retain their original scope."
    )
    endings = Counter(r["end_reason"] for r in rows)
    chart = figure("Observed terminal states", 300)
    chart.add_trace(
        go.Bar(
            x=list(endings),
            y=list(endings.values()),
            customdata=[[k] for k in endings],
            marker_color="#66c9ed",
        )
    )
    chart.update_layout(showlegend=False)
    click = st.plotly_chart(chart, key=f"possession_endings_{token}", on_select="rerun")
    options = ["All endings", *sorted(endings)]
    points = click.selection.points
    if points:
        candidate = points[-1].get("customdata", [None])[0]
        last_click = (candidate, token)
        if candidate in endings and st.session_state.get("possession_last_click") != last_click:
            st.session_state["possession_last_click"] = last_click
            st.session_state["possession_ending"] = candidate
    if st.session_state.get("possession_ending") not in options:
        st.session_state["possession_ending"] = "All endings"
    ending = st.selectbox("Possession ending", options, key="possession_ending")
    visible = [r for r in rows if ending == "All endings" or r["end_reason"] == ending]
    names = {
        meta["home_team_id"]: meta["home_team_name"],
        meta["away_team_id"]: meta["away_team_name"],
    }
    by_pid = {r["possession_id"]: r for r in visible}
    if st.session_state.get("possession_choice") not in by_pid:
        st.session_state["possession_choice"] = next(
            (r["possession_id"] for r in visible if r["owner_actions"] > 0),
            visible[0]["possession_id"],
        )
    pid = st.selectbox(
        "Native possession",
        list(by_pid),
        key="possession_choice",
        format_func=lambda i: (
            f"#{i} · {names.get(by_pid[i]['possession_team_id'], 'Unknown owner')} · "
            f"P{by_pid[i]['start_period']} · {by_pid[i]['event_count']} records · "
            f"{by_pid[i]['end_reason']}"
        ),
    )
    row = by_pid[pid]
    qualifications = [
        v for v in row["quality_flags"] if v != "physical_attacking_direction_unknown"
    ]
    if qualifications:
        st.warning("Source qualifications: " + "; ".join(qualifications))
    st.subheader("Ordered native action sequence")
    st.caption(" → ".join(row["zone_path"]) or "No located owner action states.")
    st.json(
        {
            k: v
            for k, v in row.items()
            if k not in ("event_ids", "owner_action_ids", "path_event_ids")
        },
        expanded=False,
    )
    chain = bundle.actions.filter(
        pa.array(
            [i in set(row["event_ids"]) for i in bundle.actions["event_id"].to_pylist()],
            type=pa.bool_(),
        )
    )
    display = chain.append_column(
        "matches_shared_filter",
        pa.array([i in selected_ids for i in chain["event_id"].to_pylist()], type=pa.bool_()),
    )
    foreground = [
        "sequence",
        "display_clock",
        "event_type",
        "team_id",
        "player_id",
        "role",
        "event_id",
        "matches_shared_filter",
        "zone",
        "end_zone",
    ]
    st.dataframe(display.select(foreground), hide_index=True)
    st.subheader("Recorded progression segments")
    path = figure("Observed pass / carry segments", 360)
    path.update_layout(showlegend=False)
    for kind, color in (("Pass", "#66c9ed"), ("Carry", "#f8a56c")):
        movements = [
            r
            for r in chain.to_pylist()
            if r["is_owner_action"]
            and r["event_type"] == kind
            and r["action_status"] in ("completed", "observed_carry")
            and r["progressive"] is not None
        ]
        xs, ys = [], []
        for a in movements:
            xs.extend([a["x"], a["end_x"], None])
            ys.extend([a["y"], a["end_y"], None])
        path.add_trace(
            go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color), hoverinfo="skip")
        )
        path.add_trace(
            go.Scatter(
                x=[a["end_x"] for a in movements],
                y=[a["end_y"] for a in movements],
                mode="markers",
                marker=dict(color=color, size=9),
                customdata=[[a["event_id"], a["display_clock"]] for a in movements],
                hovertemplate="%{customdata[1]} · %{customdata[0]}<extra></extra>",
            )
        )
    path.update_xaxes(range=[0, 120], constrain="domain", title="Native x")
    path.update_yaxes(range=[80, 0], constrain="domain", scaleanchor="x", title="Native y")
    path_click = st.plotly_chart(
        path, key=f"possession_path_{pid}_{token}", on_select="rerun", selection_mode="points"
    )
    if path_click.selection.points:
        candidate = path_click.selection.points[-1].get("customdata", [None])[0]
        last_click = (candidate, pid, token)
        if (
            candidate in row["event_ids"]
            and st.session_state.get("possession_path_click") != last_click
        ):
            st.session_state["possession_path_click"] = last_click
            st.session_state["possession_event"] = candidate
    st.caption(
        "Each line is one source-recorded completed pass or observed carry. "
        "There are no connectors between events or periods, and no continuous player paths. "
        "Cross-period possessions retain their native ID and carry an explicit quality flag."
    )
    ids = row["event_ids"]
    if st.session_state.get("possession_event") not in ids:
        st.session_state["possession_event"] = ids[0]
    event_id = st.selectbox("Possession original event", ids, key="possession_event")
    source = events.slice(events["event_id"].to_pylist().index(event_id), 1).to_pylist()[0]
    st.subheader("Original possession action evidence")
    st.code(event_id, language=None)
    st.caption(
        f"Provider index {source['provider_index']} · P{source['period']} · "
        f"{source['display_clock']} · "
        f"matches shared filter: {event_id in selected_ids} · "
        f"acting team {source['team_id']} / possession team {source['possession_team_id']}"
    )
    st.json(json.loads(source["source_record_json"]), expanded=False)
    st.caption(
        f"Source manifest {source['source_manifest_sha256']} · "
        f"clock manifest {source['clock_manifest_sha256']}"
    )
    if st.toggle("Show detailed possession audit", key="possession_audit"):
        st.dataframe(display, hide_index=True)
        st.json(summary)
        st.dataframe(cohort, hide_index=True)
        st.json(bundle.quality)
