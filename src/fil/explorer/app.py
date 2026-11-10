"""Local Streamlit Match Explorer. Only trusted, verified bundles enter this UI."""

import html
import json
import math
import os
from pathlib import Path
from time import perf_counter

import plotly.graph_objects as go
import streamlit as st

from fil.explorer.data import fingerprint, load_match
from fil.metrics.shots import (
    MatchFilter,
    apply_filter,
    build_shots,
    clock_view,
    cumulative,
    totals,
    window_threat,
)
from fil.metrics.spatial import spatial_report
from fil.time.clock import PeriodRange, partition_period

_TIMINGS = {}
_LAST_STAGE = perf_counter()
ALL_VALUES = "__fil_all_values__"


def mark(stage: str) -> None:
    """Optional local profiling only; never includes provider records."""
    global _LAST_STAGE
    now = perf_counter()
    _TIMINGS[stage] = now - _LAST_STAGE
    _LAST_STAGE = now


st.set_page_config(page_title="FIL · Match Explorer", page_icon="⚽", layout="wide")
st.markdown(
    """<style>
.stApp{background:#0c1420;
color:#e8edf3} .block-container{padding-top:2rem;
max-width:1500px}
h1,h2,h3{font-family:Inter,system-ui,sans-serif;
letter-spacing:-.035em}
[data-testid="stMetric"]{background:#152131;
border:1px solid #29374b;
border-radius:12px;
padding:18px}
[data-testid="stMetricLabel"]{color:#a9b7ca}
[data-testid="stMetricLabel"] p{white-space:normal;overflow:visible}
[data-testid="stMetricValue"]{color:#f3f6fa}
.match-head{padding:26px 32px;
border:1px solid #334259;
border-radius:16px;
background:linear-gradient(110deg,#172d46,#151e2e)}
.eyebrow{font:600 11px system-ui;
letter-spacing:.18em;
color:#83b9c7;
text-transform:uppercase}
.score{font:700 40px system-ui;
letter-spacing:-.04em;
margin:12px 0}.subtle{color:#a9b7ca;
font-size:13px}
[data-testid="stAppDeployButton"]{display:none}
[data-testid="stSidebar"]{background:#101c2a} button{border-radius:8px!important}
@media(max-width:600px){
  .match-head{padding:20px}.score{font-size:28px}
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]){
    display:grid;grid-template-columns:repeat(2,minmax(0,1fr));align-items:stretch}
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) >
    [data-testid="stColumn"]{width:100%!important;min-width:0!important}
  [data-testid="stMetric"]{padding:12px}
  [data-testid="stMetricValue"]{font-size:26px}
}
</style>""",
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Verifying source, clock and score lineage…")
def verified(config_body: str, content_hash: str):
    return load_match(json.loads(config_body))


@st.cache_resource(show_spinner=False, max_entries=8)
def prepared(_events, content_key: str):
    """Read-only display context, reused only after the per-rerun content hash check."""
    from types import MappingProxyType

    rows = _events.select(
        [
            "event_id",
            "period",
            "provider_index",
            "period_end_ms",
            "chronological_ms",
            "player_id",
            "player_name",
            "team_id",
            "outcome",
            "event_type",
            "display_clock",
            "score_home_before",
            "score_home_after",
            "score_away_before",
            "score_away_after",
        ]
    ).to_pylist()
    full_shots = build_shots(_events)
    cv = clock_view(_events)
    periods = sorted(set(_events["period"].to_pylist()) - {5})
    return tuple(MappingProxyType(r) for r in rows), full_shots, cv, periods


def figure(title: str, height: int = 320) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=title, font=dict(color="#e3edf7", size=15)),
        height=height,
        clickmode="event+select",
        paper_bgcolor="#0c1420",
        plot_bgcolor="#111e2d",
        font=dict(color="#bac8d9", family="system-ui"),
        margin=dict(l=24, r=24, t=70, b=35),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
    )
    fig.update_xaxes(gridcolor="#283647", zeroline=False)
    fig.update_yaxes(gridcolor="#283647", zeroline=False)
    return fig


def main() -> None:
    config_path = os.environ.get("FIL_EXPLORER_CONFIG")
    if not config_path:
        st.title("Match Explorer")
        st.info("Prepare a verified local match bundle, then launch with --config. See README.")
        st.stop()
    try:
        config_body = Path(config_path).read_text()
        config = json.loads(config_body)
        mark("page_setup_seconds")
        content_hash = fingerprint(config)
        events, meta = verified(config_body, content_hash)
        mark("verification_seconds")
    except Exception as exc:
        st.error(f"Source verification failed. No analytics displayed: {exc}")
        st.stop()
    team_ids = (meta["home_team_id"], meta["away_team_id"])
    names = dict(zip(team_ids, (meta["home_team_name"], meta["away_team_name"]), strict=True))
    colors = {team_ids[0]: "#66c9ed", team_ids[1]: "#f8a56c"}
    rows, full_shots, cv, periods = prepared(events, config_body + content_hash)
    spatial = meta.get("spatial") or spatial_report(events)
    mark("view_preparation_seconds")
    st.html(
        f"""<div class="match-head">
    <div class="eyebrow">Football Intelligence Lab</div>

    <div class="score">{html.escape(names[team_ids[0]])}
    &nbsp; {meta["home_score"]} : {meta["away_score"]}
    &nbsp; {html.escape(names[team_ids[1]])}</div><div class="subtle">
    {html.escape(meta["competition_name"])} · {html.escape(meta["season_name"])}
    · {html.escape(meta["match_date"])}
    · Official full-match score · StatsBomb Open Data</div></div>""",
    )
    st.caption(f"LOCAL RESEARCH / SOURCE-VERIFIED / HISTORICAL MATCH {meta['match_id']}")
    with st.sidebar:
        st.markdown("### Explore the match")
        st.caption("One selection drives every foreground panel.")

        def reset():
            st.session_state.update(
                {
                    "window_selection": ALL_VALUES,
                    "width_choice": 15,
                    "period_choice": "Full match",
                    "team_choice": ALL_VALUES,
                    "player_choice": ALL_VALUES,
                    "type_choice": ALL_VALUES,
                    "outcome_choice": ALL_VALUES,
                    "score_choice": ALL_VALUES,
                    "event_choice": rows[0]["event_id"],
                    "network_min_weight": 1,
                    "player_roster_rows": False,
                    "selection_epoch": st.session_state.get("selection_epoch", 0) + 1,
                }
            )
            st.session_state.pop("last_map_click", None)
            for key in (
                "tactical_entity",
                "tactical_event",
                "last_tactical_network",
                "last_tactical_action",
                "possession_choice",
                "possession_event",
                "possession_ending",
                "possession_last_click",
                "possession_path_click",
                "player_evidence_choice",
                "player_evidence_type",
                "player_original_event",
            ):
                st.session_state.pop(key, None)

        st.button("Reset filters", on_click=reset, width="stretch")
        view = st.selectbox(
            "View",
            ["Match Explorer", "Tactical Dashboard", "Possession Flow", "Player Evidence"],
            key="view_choice",
        )

        def clear_window():
            st.session_state["window_selection"] = ALL_VALUES
            st.session_state["selection_epoch"] = st.session_state.get("selection_epoch", 0) + 1
            st.session_state.pop("last_map_click", None)

        options = ["Full match"] + [f"Period {p}" for p in periods]
        period_choice = st.selectbox("Period", options, key="period_choice", on_change=clear_window)
        selected_periods = (
            periods if period_choice == "Full match" else [int(period_choice.split()[-1])]
        )
        width = st.selectbox(
            "Threat window",
            [5, 10, 15],
            index=2,
            format_func=lambda v: f"{v} minutes",
            key="width_choice",
            on_change=clear_window,
        )
        bins = tuple(b for p in selected_periods for b in partition_period(cv, p, width * 60000))
        # Changing period/width clears the range; returning cannot resurrect an old bin.
        window_choice = st.selectbox(
            "Time window",
            [ALL_VALUES, *range(len(bins))],
            format_func=lambda i: "Entire selected period(s)"
            if i == ALL_VALUES
            else (
                f"P{bins[i].period} · {bins[i].start_ms / 60000:g}–"
                f"{bins[i].end_ms / 60000:.2f} elapsed min"
            ),
            key="window_selection",
        )
        window = None if window_choice == ALL_VALUES else window_choice
        segments = (
            tuple(
                PeriodRange(p, 0, next(r["period_end_ms"] for r in rows if r["period"] == p), True)
                for p in selected_periods
            )
            if window is None
            else (bins[window],)
        )
        team_choice = st.selectbox(
            "Team",
            [ALL_VALUES, *team_ids],
            format_func=lambda t: "Both teams" if t == ALL_VALUES else names[t],
            key="team_choice",
        )
        team = None if team_choice == ALL_VALUES else team_choice
        players = {
            r["player_id"]: r["player_name"]
            for r in rows
            if r["player_id"] is not None and (team is None or r["team_id"] == team)
        }
        if st.session_state.get("player_choice") not in [ALL_VALUES, *players]:
            st.session_state["player_choice"] = ALL_VALUES
        player_choice = st.selectbox(
            "Player",
            [ALL_VALUES, *sorted(players)],
            format_func=lambda i: "All players" if i == ALL_VALUES else players[i],
            key="player_choice",
        )
        player = None if player_choice == ALL_VALUES else player_choice
        kind_choice = st.selectbox(
            "Event type",
            [ALL_VALUES, *sorted(set(events["event_type"].to_pylist()))],
            format_func=lambda v: "All event types" if v == ALL_VALUES else v,
            key="type_choice",
        )
        kind = None if kind_choice == ALL_VALUES else kind_choice
        outcome_choice = st.selectbox(
            "Outcome",
            [ALL_VALUES, *sorted({r["outcome"] for r in rows if r["outcome"]})],
            format_func=lambda v: "All outcomes" if v == ALL_VALUES else v,
            key="outcome_choice",
        )
        outcome = None if outcome_choice == ALL_VALUES else outcome_choice
        score_choice = st.selectbox(
            "Pre-event score state",
            [ALL_VALUES, "level", "leading", "trailing"],
            format_func=lambda v: "All score states" if v == ALL_VALUES else v.title(),
            key="score_choice",
        )
        st.divider()
        st.caption(
            "Coordinates: provider 120 × 80, y increases downward. "
            "Physical attacking ends are unknown; no team/period flips."
        )
        st.caption(
            "Noncommercial local research. Provider data is not covered by "
            "FIL’s MIT license. No redistribution."
        )
    state = MatchFilter(
        segments,
        team,
        player,
        kind,
        outcome,
        None if score_choice == ALL_VALUES else score_choice,
        meta["home_team_id"],
        meta["away_team_id"],
    )
    st.session_state["match_filter"] = state
    selected = apply_filter(events, state)
    shots = build_shots(selected)
    shot_rows = shots.to_pylist()
    selected_ids = set(selected["event_id"].to_pylist())
    mark("filter_seconds")
    scope = [period_choice, names.get(team, "Both teams")]
    if player is not None:
        scope.append(players[player])
    if window is not None:
        scope.append(
            f"P{bins[window].period} {bins[window].start_ms / 60000:g}–"
            f"{bins[window].end_ms / 60000:g} elapsed min"
        )
    if kind:
        scope.append(kind)
    if outcome:
        scope.append(outcome)
    if score_choice != ALL_VALUES:
        scope.append(f"Pre-event state: {score_choice}")
    st.caption("Shared selection · " + " · ".join(scope))

    cols = st.columns(4)
    cols[0].metric("Selected events", str(selected.num_rows))
    cols[1].metric("Selected shots", str(shots.num_rows))
    cols[2].metric("Selected source xG", f"{sum(totals(shots, t)['xg'] for t in team_ids):.3f}")
    cols[3].metric(
        "Selected non-penalty xG",
        f"{sum(totals(shots, t)['non_penalty_xg'] for t in team_ids):.3f}",
    )
    st.caption(
        "Selected metrics use the shared filter. Full-match score above remains fixed. "
        + ("Cumulative background below remains fixed. " if view == "Match Explorer" else "")
        + "Own goals add to score, not shot xG."
    )
    st.caption(
        " · ".join(
            f"{names[t]}: {totals(shots, t)['shot_count']} selected shots / "
            f"{totals(shots, t)['xg']:.3f} xG / {totals(shots, t)['non_penalty_xg']:.3f} NPxG"
            for t in team_ids
        )
    )
    if view == "Player Evidence":
        from fil.explorer.players import render

        render(events, selected, meta, state, config_body + content_hash, config["raw"])
        mark("player_view_seconds")
        return
    if view == "Possession Flow":
        from fil.explorer.possession import render

        render(events, selected, meta, config_body + content_hash, figure)
        mark("possession_view_seconds")
        return
    if view == "Tactical Dashboard":
        from fil.explorer.tactical import render

        render(events, selected, meta, state, width, config_body + content_hash, figure)
        mark("tactical_view_seconds")
        return
    left, right = st.columns([1.18, 1])
    with left:
        curve = figure("Source xG progression · full-match context")
        points = cumulative(full_shots)
        end = max(r["chronological_ms"] for r in rows if r["chronological_ms"] is not None) / 60000
        for t in team_ids:
            line = [r for r in points if r["team_id"] == t]
            curve.add_trace(
                go.Scatter(
                    x=[0] + [r["chronological_ms"] / 60000 for r in line] + [end],
                    y=[0]
                    + [r["cumulative_xg"] for r in line]
                    + [line[-1]["cumulative_xg"] if line else 0],
                    mode="lines",
                    line=dict(color=colors[t], shape="hv", width=3),
                    name=names[t],
                )
            )
            chosen = [r for r in line if r["event_id"] in selected_ids]
            curve.add_trace(
                go.Scatter(
                    x=[r["chronological_ms"] / 60000 for r in chosen],
                    y=[r["cumulative_xg"] for r in chosen],
                    mode="markers",
                    marker=dict(color=colors[t], size=8),
                    customdata=[[r["event_id"], r["display_clock"]] for r in chosen],
                    hovertemplate="%{customdata[1]} · %{y:.3f} xG<extra></extra>",
                    showlegend=False,
                )
            )
        curve.update_xaxes(title="Event clock (minutes)")
        curve.update_yaxes(title="Cumulative source xG")
        st.plotly_chart(curve, use_container_width=True, key="xg_curve")
    with right:
        pitch = figure("Shot map · provider coordinates", 320)
        pitch.add_shape(type="rect", x0=0, x1=120, y0=0, y1=80, line=dict(color="#647a8c"))
        for x0, x1 in [(0, 18), (102, 120)]:
            pitch.add_shape(type="rect", x0=x0, x1=x1, y0=18, y1=62, line=dict(color="#647a8c"))
        pitch.add_shape(type="line", x0=60, x1=60, y0=0, y1=80, line=dict(color="#647a8c"))
        pitch.add_shape(type="circle", x0=50, x1=70, y0=30, y1=50, line=dict(color="#647a8c"))
        for t in team_ids:
            located = [
                r
                for r in shot_rows
                if r["team_id"] == t and r["x"] is not None and r["y"] is not None
            ]
            pitch.add_trace(
                go.Scatter(
                    x=[r["x"] for r in located],
                    y=[r["y"] for r in located],
                    mode="markers",
                    name=names[t],
                    marker=dict(
                        size=[8 + 22 * math.sqrt(r["shot_xg"]) for r in located],
                        color=colors[t],
                        symbol=[
                            "star" if r["shot_outcome"] == "Goal" else "circle" for r in located
                        ],
                        line=dict(color="#e4edf7", width=1),
                    ),
                    customdata=[
                        [
                            r["event_id"],
                            r["player_name"] or "Player unavailable",
                            r["display_clock"],
                            r["shot_outcome"],
                            r["shot_xg"],
                        ]
                        for r in located
                    ],
                    hovertemplate=(
                        "%{customdata[1]} · %{customdata[2]}<br>"
                        "%{customdata[3]} · %{customdata[4]:.3f} xG<extra></extra>"
                    ),
                )
            )
        pitch.update_xaxes(range=[-3, 123], visible=False)
        pitch.update_yaxes(range=[83, -3], visible=False, scaleanchor="x", scaleratio=1)
        selection = st.plotly_chart(
            pitch,
            use_container_width=True,
            key=f"shot_map_{st.session_state.get('selection_epoch', 0)}",
            on_select="rerun",
            selection_mode="points",
        )
        st.caption(
            "★ Shot goal · ● Other outcome · marker size = 8 + 22√xG px (range "
            "8–30). Missing locations remain in the table."
        )
        st.caption(
            "Provider frame · 120 × 80 · y down · coordinates unchanged. "
            + (
                "Observed team/period goals corroborate a +x shot frame. "
                if spatial["shot_positive_x_corroborated"]
                else "Shot attacking direction remains uncertified. "
            )
            + "Physical pitch ends are unknown."
        )
        with st.expander("Coordinate frame and limits"):
            st.json(spatial, expanded=False)
    threat = figure(f"Window threat · source xG sum / {width}-minute period bins", 230)
    # Reuse exactly the selected event IDs; bin assignment never reintroduces excluded events.
    full_windows = window_threat(events, team_ids, width * 60000)
    for t in team_ids:
        bins_t = [r for r in full_windows if r["team_id"] == t and r["period"] in selected_periods]
        values = []
        for b in bins_t:
            values.append(sum(r["shot_xg"] for r in shot_rows if r["event_id"] in b["event_ids"]))
        threat.add_trace(
            go.Bar(
                x=[
                    f"P{b['period']} {b['start_ms'] / 60000:g}–{b['end_ms'] / 60000:.1f}"
                    for b in bins_t
                ],
                y=values,
                name=names[t],
                marker_color=colors[t],
                customdata=[[b["period"], b["start_ms"], b["end_ms"]] for b in bins_t],
            )
        )
    threat.update_layout(barmode="group")

    threat_key = f"threat_selection_{st.session_state.get('selection_epoch', 0)}"

    def select_threat_window():
        points = st.session_state[threat_key].selection.points
        if points:
            values = points[-1].get("customdata", [])
            for i, b in enumerate(bins):
                if values == [b.period, b.start_ms, b.end_ms]:
                    st.session_state["window_selection"] = i

    st.plotly_chart(
        threat,
        use_container_width=True,
        key=threat_key,
        on_select=select_threat_window,
        selection_mode="points",
    )
    st.caption(
        "Threat = sum of recorded shot xG in each selected period/window; not "
        "possession, control, or a black-box momentum model. Partial terminal "
        "bins have shorter exposure."
    )
    score_fig = figure("Match state · full-match score, selected goal markers", 220)
    awarded = [
        r
        for r in rows
        if r["period"] < 5
        and (
            r["score_home_after"] != r["score_home_before"]
            or r["score_away_after"] != r["score_away_before"]
        )
    ]
    for t, side in zip(team_ids, ("home", "away"), strict=True):
        score_fig.add_trace(
            go.Scatter(
                x=[0] + [r["chronological_ms"] / 60000 for r in awarded] + [end],
                y=[0] + [r[f"score_{side}_after"] for r in awarded] + [meta[f"{side}_score"]],
                mode="lines",
                name=names[t],
                line=dict(color=colors[t], shape="hv", width=2),
            )
        )
        chosen = [
            r
            for r in awarded
            if r["event_id"] in selected_ids
            and r[f"score_{side}_after"] != r[f"score_{side}_before"]
        ]
        score_fig.add_trace(
            go.Scatter(
                x=[r["chronological_ms"] / 60000 for r in chosen],
                y=[r[f"score_{side}_after"] for r in chosen],
                mode="markers",
                marker=dict(size=11, color=colors[t], symbol="star"),
                showlegend=False,
                text=[f"{r['display_clock']} · {r['event_type']}" for r in chosen],
                hovertemplate="%{text}<extra></extra>",
            )
        )
    score_fig.update_yaxes(dtick=1, title="Goals (shootout excluded)")
    score_fig.update_xaxes(title="Chronological event minutes")
    st.plotly_chart(score_fig, use_container_width=True, key="score_state")
    mark("charts_seconds")
    table_col, evidence_col = st.columns([1.2, 1])
    with table_col:
        st.subheader("Event ledger")
        table_rows = selected.select(
            [
                "display_clock",
                "period",
                "provider_index",
                "event_type",
                "team_name",
                "player_name",
                "outcome",
                "shot_xg",
                "score_home_after",
                "score_away_after",
                "event_id",
            ]
        )
        st.dataframe(table_rows, width="stretch", hide_index=True, height=350)
        st.caption(
            f"{selected.num_rows} original records · every row retains its provider event ID"
        )
    with evidence_col:
        st.subheader("Source evidence")
        ids = selected["event_id"].to_pylist()
        clicked = selection.selection.points if selection else []
        if clicked:
            candidate = clicked[-1].get("customdata", [None])[0]
            token = (candidate, tuple(ids))
            if candidate in ids and st.session_state.get("last_map_click") != token:
                st.session_state["event_choice"] = candidate
                st.session_state["last_map_click"] = token
        if st.session_state.get("event_choice") not in ids:
            st.session_state.pop("event_choice", None)
        if not ids:
            st.info("No events in this selection. Reset filters to explore the full match.")
        else:
            by_id = {
                r["event_id"]: r
                for r in selected.select(
                    ["event_id", "period", "display_clock", "event_type"]
                ).to_pylist()
            }
            chosen = st.selectbox(
                "Original event",
                ids,
                key="event_choice",
                format_func=lambda i: (
                    f"P{by_id[i]['period']} · {by_id[i]['display_clock']} · "
                    f"{by_id[i]['event_type']} · {i[:8]}"
                ),
            )
            r = selected.slice(ids.index(chosen), 1).to_pylist()[0]
            st.code(chosen, language=None)
            st.caption(
                f"Provider timestamp {r['period_timestamp']} · index {r['provider_index']} · "
                f"raw array offset {r['raw_event_row']}"
            )
            st.caption(
                f"Score state {r['score_home_before']}–{r['score_away_before']} → "
                f"{r['score_home_after']}–{r['score_away_after']}"
            )
            st.link_button(
                "View pinned source file",
                f"https://github.com/hudl/open-data/blob/{meta['source_revision']}/{r['raw_event_path']}",
            )
            with st.expander("Original provider JSON", expanded=True):
                st.json(json.loads(r["source_record_json"]), expanded=False)
            with st.expander("Provenance and metric definitions"):
                st.json(
                    {
                        k: r[k]
                        for k in (
                            "source_revision",
                            "source_manifest_sha256",
                            "canonical_manifest_sha256",
                            "clock_manifest_sha256",
                            "score_pipeline_git_sha",
                        )
                    }
                )
                st.write(
                    "Source xG: provided shot probability, match-play penalties "
                    "included; period 5 excluded. Model internals unavailable. "
                    "Display clock is period-aware; chronological time omits "
                    "real breaks."
                )
    st.divider()
    st.caption(
        "StatsBomb Open Data · Hudl official repository · 2018 historical match "
        "· Local noncommercial research only. No tracking, ratings, xT or AI "
        "claims."
    )
    mark("ledger_evidence_seconds")


if __name__ == "__main__":
    try:
        main()
    finally:
        if path := os.environ.get("FIL_EXPLORER_PROFILE"):
            Path(path).write_text(json.dumps(_TIMINGS, indent=2) + "\n")
