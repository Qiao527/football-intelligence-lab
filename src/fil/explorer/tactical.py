"""Interactive tactical view; all football calculations live in metrics/ingestion."""

import hashlib
import html
import json
import math
from dataclasses import replace

import plotly.graph_objects as go
import streamlit as st

from fil.ingestion.statsbomb_tactics import extract_tactics
from fil.metrics.shots import clock_view
from fil.metrics.tactics import compare, completed_passes, passing_network, select_actions
from fil.time.clock import PeriodRange, partition_period


@st.cache_resource(show_spinner="Auditing original pass/carry semantics…")
def facts(_events, home: int, away: int, content_key: str):
    return extract_tactics(_events, home, away)


def network_figure(edges, nodes, team: int, name: str, color: str, figure):
    fig = figure(f"{name} · directed completed passes", 400)
    by_id = {r["player_id"]: r for r in nodes.to_pylist() if r["team_id"] == team}
    bands = {1: ([], []), 2: ([], []), 3: ([], [])}
    points = []
    for e in edges.to_pylist():
        if e["team_id"] != team:
            continue
        a, b = by_id[e["passer_id"]], by_id[e["recipient_id"]]
        if a["x"] is None or b["x"] is None:
            continue
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
        distance = math.hypot(dx, dy)
        if distance == 0:
            continue  # Retained in table, never invent a new node position.
        # Parallel display offset separates reciprocal arrows, not source locations.
        ox, oy = -dy / distance * 0.7, dx / distance * 0.7
        x0, y0, x1, y1 = a["x"] + ox, a["y"] + oy, b["x"] + ox, b["y"] + oy
        band = 1 if e["weight"] == 1 else 2 if e["weight"] < 5 else 3
        bands[band][0].extend([x0, x1, None])
        bands[band][1].extend([y0, y1, None])
        key = f"edge:{team}:{e['passer_id']}:{e['recipient_id']}"
        points.append(
            (
                (x0 + x1) / 2,
                (y0 + y1) / 2,
                key,
                e["weight"],
                f"{a['player_name']} → {b['player_name']}",
            )
        )
        fig.add_annotation(
            x=x0 + 0.8 * dx,
            y=y0 + 0.8 * dy,
            ax=x0 + 0.6 * dx,
            ay=y0 + 0.6 * dy,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=0.8,
            arrowwidth=1,
            arrowcolor=color,
        )
    for band, (xs, ys) in bands.items():
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(width=band, color=color),
                opacity=0.35,
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[p[0] for p in points],
            y=[p[1] for p in points],
            mode="markers",
            marker=dict(size=[5 + math.sqrt(p[3]) for p in points], symbol="diamond", color=color),
            customdata=[[p[2], p[3], html.escape(p[4])] for p in points],
            hovertemplate="%{customdata[2]}<br>%{customdata[1]} distinct passes<extra></extra>",
            name="Pass links · click diamond",
        )
    )
    located = [n for n in by_id.values() if n["x"] is not None]
    fig.add_trace(
        go.Scatter(
            x=[n["x"] for n in located],
            y=[n["y"] for n in located],
            mode="markers+text",
            text=[
                html.escape((n["player_name"] or str(n["player_id"])).split()[-1]) for n in located
            ],
            textposition="top center",
            textfont=dict(size=10),
            marker=dict(
                size=[10 + math.sqrt(n["sent"] + n["received"]) for n in located], color=color
            ),
            customdata=[
                [
                    f"player:{team}:{n['player_id']}",
                    html.escape(n["player_name"] or "Unknown"),
                    n["sample_count"],
                    n["sent"],
                    n["received"],
                ]
                for n in located
            ],
            hovertemplate=(
                "%{customdata[1]}<br>%{customdata[2]} pass-origin samples"
                "<br>Sent %{customdata[3]} / received %{customdata[4]}<extra></extra>"
            ),
            name="Event-average pass origins",
        )
    )
    fig.add_shape(type="rect", x0=0, x1=120, y0=0, y1=80, line=dict(color="#647a8c"))
    fig.update_xaxes(range=[-3, 123], title="Native x", constrain="domain")
    fig.update_yaxes(
        range=[83, -3],
        title="Native y (down)",
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
    )
    # The common legend wraps above the plot on narrow screens and collides
    # with the title. The nearby caption already explains these two symbols.
    fig.update_layout(showlegend=False)
    return fig


def render(events, selected, meta: dict, state, width: int, content_key: str, figure) -> None:
    home, away = meta["home_team_id"], meta["away_team_id"]
    names = {home: meta["home_team_name"], away: meta["away_team_name"]}
    bundle = facts(events, home, away, content_key)
    actions = select_actions(bundle.actions, selected)
    passes = completed_passes(actions)
    edges, nodes = passing_network(actions)
    rows = actions.to_pylist()
    action_by_id = {r["event_id"]: r for r in rows}
    token = hashlib.sha256(
        (
            str(st.session_state.get("selection_epoch", 0))
            + "|"
            + "|".join(selected["event_id"].to_pylist())
        ).encode()
    ).hexdigest()[:12]
    st.header("Tactical Dashboard")
    st.caption(
        "FIL-012 · descriptive event evidence, not player importance or causal tactics. "
        "All foreground views use the shared filters, including pre-event score state."
    )
    cols = st.columns(4)
    cols[0].metric("Completed passes", passes.num_rows)
    cols[1].metric("Directed pass pairs", edges.num_rows)
    cols[2].metric(
        "Progressive passes v1",
        sum(r["event_type"] == "Pass" and r["progressive"] is True for r in rows),
    )
    cols[3].metric(
        "Progressive carries v1",
        sum(r["event_type"] == "Carry" and r["progressive"] is True for r in rows),
    )
    st.caption(
        "Positions are means of observed completed-pass origins in this selection. "
        "They are not tracking, physical formations or complete player involvement. "
        "Arrows connect event averages, not actual individual pass trajectories. "
        "Coordinates remain native 120×80, y down; physical attacking ends are unknown."
    )
    entities = {"all": "All selected pass/carry evidence"}
    entity_ids = {}
    node_rows = nodes.to_pylist()
    labels = {
        (r["team_id"], r["player_id"]): r["player_name"] or str(r["player_id"]) for r in node_rows
    }
    for e in edges.to_pylist():
        key = f"edge:{e['team_id']}:{e['passer_id']}:{e['recipient_id']}"
        entities[key] = (
            f"{names[e['team_id']]}: {labels[e['team_id'], e['passer_id']]} → "
            f"{labels[e['team_id'], e['recipient_id']]} ({e['weight']})"
        )
        entity_ids[key] = e["event_ids"]
    for n in node_rows:
        key = f"player:{n['team_id']}:{n['player_id']}"
        entities[key] = f"Player involvement: {n['player_name']} ({len(n['event_ids'])} pass IDs)"
        entity_ids[key] = n["event_ids"]

    def accept(selection, kind):
        points = selection.selection.points if selection else []
        if not points:
            return
        candidate = points[-1].get("customdata", [None])[0]
        click = (kind, candidate, token)
        if st.session_state.get(f"last_tactical_{kind}") == click:
            return
        st.session_state[f"last_tactical_{kind}"] = click
        if kind == "network" and candidate in entities:
            st.session_state["tactical_entity"] = candidate
            st.session_state.pop("tactical_event", None)
        if kind == "action" and candidate in action_by_id:
            st.session_state["tactical_entity"] = "all"
            st.session_state["tactical_event"] = candidate

    teams = [t for t in (home, away) if state.team_id in (None, t)]
    for column, team in zip(st.columns(len(teams)), teams, strict=True):
        with column:
            chart = network_figure(
                edges,
                nodes,
                team,
                html.escape(names[team]),
                "#66c9ed" if team == home else "#f8a56c",
                figure,
            )
            accept(
                st.plotly_chart(
                    chart,
                    key=f"tactical_network_{team}_{token}",
                    on_select="rerun",
                    selection_mode="points",
                ),
                "network",
            )
    unmapped = sum(n["x"] is None for n in node_rows)
    st.caption(
        f"{unmapped} nodes without pass-origin positions stay in the tables. "
        "Links with unplaced/coincident endpoints stay in counts and evidence. "
        "Diamond = directed pair; circle = player. Line-width bands: 1, 2–4, ≥5 passes."
    )
    st.subheader("Progression v1 · native-frame convention")
    st.caption(
        "Completed passes or observed carries: positive Δx AND ≥10 provider units closer "
        "to the conventional (120,40) goal. This declared +x convention does not certify "
        "physical directions. No xT, VAEP or retained-possession claim. Missing/invalid "
        "endpoints remain unresolved; dots mark endpoints, not player tracking."
    )
    plot = figure("Progressive passes / carries", 400)
    plot.update_layout(legend=dict(y=-0.22, yanchor="top"), margin=dict(b=90))
    for kind, color in (("Pass", "#66c9ed"), ("Carry", "#f8a56c")):
        items = [r for r in rows if r["event_type"] == kind and r["progressive"] is True]
        xs, ys = [], []
        for r in items:
            xs.extend([r["x"], r["end_x"], None])
            ys.extend([r["y"], r["end_y"], None])
        plot.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color=color, width=1),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        plot.add_trace(
            go.Scatter(
                x=[r["end_x"] for r in items],
                y=[r["end_y"] for r in items],
                mode="markers",
                marker=dict(color=color, size=8, symbol="diamond"),
                name=kind,
                customdata=[[r["event_id"], r["display_clock"], r["distance_gain"]] for r in items],
                hovertemplate=(
                    "%{customdata[1]} · gain %{customdata[2]:.2f} provider units<extra></extra>"
                ),
            )
        )
    plot.update_xaxes(range=[0, 120], title="Native x", constrain="domain")
    plot.update_yaxes(
        range=[80, 0], title="Native y", scaleanchor="x", scaleratio=1, constrain="domain"
    )
    accept(
        st.plotly_chart(
            plot, key=f"tactical_progression_{token}", on_select="rerun", selection_mode="points"
        ),
        "action",
    )
    if st.session_state.get("tactical_entity") not in entities:
        st.session_state["tactical_entity"] = "all"
    entity = st.selectbox(
        "Passing entity / evidence focus",
        list(entities),
        format_func=entities.__getitem__,
        key="tactical_entity",
    )
    detail_ids = entity_ids.get(entity, list(action_by_id))
    detail_ids = sorted(detail_ids, key=lambda i: action_by_id[i]["provider_index"])
    if st.session_state.get("tactical_event") not in detail_ids:
        st.session_state.pop("tactical_event", None)
    st.subheader("Exact tactical source evidence")
    if not detail_ids:
        st.info("No pass/carry evidence in this selection. No positions or progression inferred.")
    else:
        chosen = st.selectbox(
            "Tactical original event",
            detail_ids,
            key="tactical_event",
            format_func=lambda i: (
                f"{action_by_id[i]['display_clock']} · {action_by_id[i]['event_type']} · {i}"
            ),
        )
        row = events.slice(events["event_id"].to_pylist().index(chosen), 1).to_pylist()[0]
        st.code(chosen, language=None)
        st.caption(
            f"Provider index {row['provider_index']} · timestamp {row['period_timestamp']} · "
            f"pre-event score {row['score_home_before']}–{row['score_away_before']}"
        )
        left, right = st.columns(2)
        with left:
            st.json(action_by_id[chosen], expanded=False)
        with right:
            st.json(json.loads(row["source_record_json"]), expanded=False)
        st.caption(
            f"Source manifest {row['source_manifest_sha256']} · "
            f"clock manifest {row['clock_manifest_sha256']}"
        )
    with st.expander("Network tables and action QA"):
        st.dataframe(edges, hide_index=True)
        st.dataframe(nodes, hide_index=True)
        st.dataframe(actions, hide_index=True)
        st.json(bundle.quality, expanded=False)
    st.subheader("Phase and game-state comparisons")
    mode = st.selectbox(
        "Comparison",
        ["First half / second half", "Two explicit windows", "Score states"],
        key="tactical_comparison",
    )
    if mode == "Score states":
        choices = [
            (f"Acting team {v}", replace(state, score_state=v))
            for v in ("level", "leading", "trailing")
        ]
        st.caption(
            "Shared time/team/player/type/outcome retained; each row replaces only score state."
        )
    else:
        cv = clock_view(events)
        periods = sorted(set(events["period"].to_pylist()) - {5})
        options = (
            [
                PeriodRange(
                    p,
                    0,
                    max(
                        r["period_end_ms"]
                        for r in events.select(["period", "period_end_ms"]).to_pylist()
                        if r["period"] == p
                    ),
                    True,
                )
                for p in periods
            ]
            if mode == "First half / second half"
            else [b for p in periods for b in partition_period(cv, p, width * 60000)]
        )

        def label(i: int) -> str:
            s = options[i]
            return f"P{s.period} [{s.start_ms / 60000:g}, {s.end_ms / 60000:g}] elapsed min" + (
                " terminal included" if s.include_terminal else " end excluded"
            )

        a = st.selectbox(
            "Comparison A", range(len(options)), format_func=label, key=f"compare_a_{mode}_{width}"
        )
        b = st.selectbox(
            "Comparison B",
            range(len(options)),
            index=min(1, len(options) - 1),
            format_func=label,
            key=f"compare_b_{mode}_{width}",
        )
        choices = [
            (f"A: {label(a)}", replace(state, segments=(options[a],))),
            (f"B: {label(b)}", replace(state, segments=(options[b],))),
        ]
        st.caption(
            "Comparison windows replace only shared time; "
            "team/player/type/outcome/score filters remain."
        )
    st.dataframe(compare(events, bundle.actions, tuple(teams), choices), hide_index=True)
    st.caption(
        "Counts have unequal time/player exposure. No per-90, causal contribution "
        "or stable formation inference. "
        "Existing v0.3 cold-start and interaction budgets remain unmet; see the engineering report."
    )
