"""FIL Match Intelligence portfolio application. Local processing, no external AI."""

import hashlib
import html
import json
import os
from pathlib import Path
from time import perf_counter

import streamlit as st

from fil.intelligence import VERSION
from fil.intelligence.engine import CLAIM_STANDARDS, analyze
from fil.intelligence.sources import catalog, fingerprint, load

st.set_page_config(page_title="FIL · Match Intelligence", page_icon="⚽", layout="wide")
st.html("""<style>
.stApp{background:#0a111a;color:#e7eef5}
.block-container{max-width:1360px;padding-top:2.1rem;padding-bottom:4rem}
h1,h2,h3{font-family:Inter,system-ui,sans-serif;letter-spacing:-.04em}
h1{font-size:clamp(2.1rem,4vw,3.7rem)!important;line-height:1.06!important}
p{line-height:1.6} .fil-nav{display:flex;align-items:center;gap:12px;margin-bottom:32px}
.fil-logo{background:#7ee5ba;color:#0a111a;font:850 17px system-ui;padding:10px;
border-radius:10px;letter-spacing:-1px}.fil-wordmark{font:650 15px system-ui}
.fil-kicker{font:650 11px system-ui;letter-spacing:.15em;color:#7ee5ba;text-transform:uppercase}
.fil-muted{color:#a9bacb;font:14px/1.65 system-ui}
.fil-hero{background:linear-gradient(115deg,#162c31,#131f32);border:1px solid #294344;
border-radius:20px;padding:32px;margin:14px 0 22px}
.fil-hero h2{font:650 clamp(1.6rem,3vw,2.6rem) system-ui;letter-spacing:-.04em;margin:8px 0}
.fil-chip{display:inline-block;border:1px solid #3a5361;padding:3px 9px;border-radius:20px;
color:#c3d5e3;font:11px/1.8 system-ui;margin:4px 5px 0 0}
.fil-chip-green{border-color:#446c5a;color:#93e1bd}
.fil-card{padding:20px 22px;background:#111e2b;border:1px solid #2b3e50;border-radius:14px;
margin:10px 0}.fil-card h3{font-size:1.2rem;margin:6px 0 12px}
.fil-card p{color:#d1dfeb;font-size:15px;margin-bottom:8px}
[data-testid="stMetric"]{background:#111e2b;border:1px solid #293c4d;padding:16px;
border-radius:13px}[data-testid="stMetricValue"]{font-size:1.85rem}
[data-testid="stMetricLabel"] p{color:#b6c8d7;white-space:normal}
[data-testid="stSidebar"]{background:#101b27;border-right:1px solid #253747}
button{border-radius:9px!important}[data-testid="stAppDeployButton"]{display:none}
[data-testid="stAlert"]{border-radius:12px}
@media(max-width:650px){.block-container{padding-top:4.5rem;padding-left:1rem;padding-right:1rem}
.fil-hero{padding:21px}.fil-nav{margin-bottom:20px}.fil-card{padding:16px}
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]){display:grid;
grid-template-columns:repeat(2,minmax(0,1fr))}
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"])>[data-testid="stColumn"]{
width:100%!important;min-width:0!important}[data-testid="stMetric"]{padding:12px}
[data-testid="stMetricValue"]{font-size:1.5rem}}
</style>""")


@st.cache_resource(show_spinner=False, max_entries=8)
def verified(match_id: str, library_json: str, content_digest: str):
    """Read-only payload; content_digest is recomputed from bytes before every use."""
    return load(match_id, json.loads(library_json) if library_json else None)


def esc(value) -> str:
    return html.escape(str(value))


def open_evidence(event_id: str, context: list[str]) -> None:
    st.session_state["workspace"] = "Evidence explorer"
    st.session_state["evidence_scope"] = "Selected sequence"
    st.session_state["focus_context"] = context
    st.session_state["original_action"] = event_id
    st.session_state["event_search"] = ""
    st.session_state["event_type"] = "All actions"


def reset_filters() -> None:
    st.session_state["report_period"] = 0
    st.session_state["report_team"] = 0
    st.session_state["evidence_scope"] = "Current selection"
    st.session_state["event_search"] = ""
    st.session_state["event_type"] = "All actions"
    st.session_state.pop("original_action", None)


def render_charts(report: dict, names: dict, label: str) -> None:
    import plotly.graph_objects as go

    colors = ["#7ee5ba", "#b4a0f4"]
    cumulative = go.Figure()
    shot_map = go.Figure()
    for (tid, name), color in zip(names.items(), colors, strict=True):
        shots = [s for s in report["shots"] if s["team_id"] == tid]
        running, ys = 0.0, []
        for s in shots:
            running += float(s["weight"] or 0)
            ys.append(running)
        if not report["missing_shot_weight_ids"]:
            cumulative.add_trace(
                go.Scatter(
                    x=[0] + [s["index"] for s in shots],
                    y=[0] + ys,
                    name=name,
                    mode="lines+markers",
                    line=dict(color=color, shape="hv", width=2),
                    marker=dict(size=6),
                    customdata=[""] + [s["event_id"] for s in shots],
                    hovertemplate="Index %{x}<br>Sum %{y:.3f}<extra>%{fullData.name}</extra>",
                )
            )
        located = [
            s
            for s in shots
            if isinstance(s["location"], list)
            and len(s["location"]) >= 2
            and all(
                type(v) in (int, float) and 0 <= v <= bound
                for v, bound in zip(s["location"][:2], (120, 80), strict=True)
            )
        ]
        shot_map.add_trace(
            go.Scatter(
                x=[s["location"][0] for s in located],
                y=[s["location"][1] for s in located],
                mode="markers",
                name=name,
                marker=dict(
                    color=color, size=11, opacity=0.85, line=dict(color="#d8e6ef", width=1)
                ),
                customdata=[s["event_id"] for s in located],
                text=[f"{s['player']} · {s['outcome']}" for s in located],
                hovertemplate="%{text}<br>Native (%{x}, %{y})<extra></extra>",
            )
        )
    for fig in (cumulative, shot_map):
        fig.update_layout(
            height=285,
            paper_bgcolor="#0a111a",
            plot_bgcolor="#101e29",
            font=dict(color="#bfd0dc", family="system-ui"),
            margin=dict(l=15, r=15, t=15, b=20),
            legend=dict(orientation="h", y=1.16),
            xaxis=dict(gridcolor="#263746"),
            yaxis=dict(gridcolor="#263746"),
        )
    cumulative.update_xaxes(title="Original provider sequence index")
    cumulative.update_yaxes(title=label)
    shot_map.update_xaxes(range=[0, 120], title="Raw native x")
    shot_map.update_yaxes(range=[80, 0], title="Raw native y")
    shot_map.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80, line=dict(color="#486658", width=1))
    left, right = st.columns(2)
    with left:
        st.markdown("#### How chances accumulated")
        if report["missing_shot_weight_ids"]:
            st.info("Cumulative sums unavailable: a Shot has missing weight.")
        else:
            st.plotly_chart(cumulative, use_container_width=True, config={"displayModeBar": False})
        st.caption("Source order, not a physical match clock. Zero anchors are display-only.")
    with right:
        st.markdown("#### Where Shots were recorded")
        st.plotly_chart(shot_map, use_container_width=True, config={"displayModeBar": False})
        st.caption("Unflipped native coordinates. Physical direction and tracking unavailable.")


def render_report(report: dict, names: dict, label: str) -> None:
    st.subheader("Match Intelligence Report")
    st.caption("Descriptive review priorities · no independent usefulness or novelty claim")
    if report["abstention"]:
        st.info(report["abstention"])
    else:
        st.markdown(
            "These memberships have the largest recorded Shot-weight totals in your "
            "selection. Inspect their actions before forming a football explanation."
        )
    render_charts(report, names, label)
    for index, card in enumerate(report["review_cards"], 1):
        unit = card["unit"]
        st.html(
            f'<div class="fil-card"><div class="fil-kicker">Review {index:02d} · '
            f"{esc(names[unit['team_id']])} · Period {unit['period']}</div>"
            f"<h3>{esc(card['title'])}</h3><p>{esc(card['observation'])}</p>"
            '<span class="fil-chip fil-chip-green">Match fact · arithmetic verified</span>'
            '<span class="fil-chip">Usefulness unmeasured</span>'
            '<span class="fil-chip">Baseline-reproducible</span></div>'
        )
        st.button(
            f"Inspect original actions · membership {unit['possession_id']}",
            key=card["id"],
            on_click=open_evidence,
            args=(unit["event_ids"][0], unit["context_event_ids"]),
        )
        with st.expander("Counterevidence & interpretation limits", expanded=False):
            st.write(
                f"**All other Shots in this selection:** {len(unit['complement_event_ids'])}. "
                f"Their home-minus-away weight sum is {unit['complement_difference']}."
            )
            st.caption("Removing records is accounting, not a counterfactual football match.")
            st.write(
                "**Question for review — explanatory hypothesis, untested:** " + card["question"]
            )
            for alternative in card["alternatives"]:
                st.write("• " + alternative)
            st.write("**What would defeat the value claim:** " + card["falsifier"])
            if unit["complement_event_ids"]:
                st.button(
                    "Inspect comparison Shots",
                    key="counter-" + card["id"],
                    on_click=open_evidence,
                    args=(unit["complement_event_ids"][0], unit["complement_event_ids"]),
                )
    st.info(
        "No repeated tactical pattern, causal explanation or general player capability "
        "has been validated. A single event may still be worth an analyst's review."
    )


def render_evidence(raw: list[dict], report: dict, names: dict) -> None:
    st.subheader("Evidence explorer")
    scope = st.selectbox(
        "Evidence scope",
        ["Current selection", "Selected sequence", "Full original match"],
        key="evidence_scope",
    )
    ids = (
        set(report["selected_event_ids"])
        if scope == "Current selection"
        else (
            set(st.session_state.get("focus_context", []))
            if scope == "Selected sequence"
            else {e["id"] for e in raw}
        )
    )
    rows = [e for e in raw if e["id"] in ids]
    if scope == "Selected sequence":
        st.caption(
            "Whole native membership or comparison Shots opened from the report. "
            "Context can include actions outside the foreground team filter."
        )
    a, b = st.columns([2, 1])
    query = (
        a.text_input(
            "Search original actions",
            placeholder="Player, action or original ID",
            key="event_search",
        )
        .casefold()
        .strip()
    )
    types = ["All actions"] + sorted({e["type"]["name"] for e in rows})
    if st.session_state.get("event_type") not in types:
        st.session_state["event_type"] = "All actions"
    kind = b.selectbox("Action type", types, key="event_type")
    rows = [
        e
        for e in rows
        if (kind == "All actions" or e["type"]["name"] == kind)
        and (
            not query
            or query
            in " ".join(
                [
                    e["id"],
                    e["type"]["name"],
                    (e.get("player") or {}).get("name", ""),
                    names[e["team"]["id"]],
                ]
            ).casefold()
        )
    ]
    st.caption(f"{len(rows):,} original actions · source order preserved")
    if not rows:
        st.info("No original actions match these filters. Reset filters or change evidence scope.")
        return
    by_id = {e["id"]: e for e in rows}
    if st.session_state.get("original_action") not in by_id:
        st.session_state["original_action"] = rows[0]["id"]
    event_id = st.selectbox(
        "Original action",
        list(by_id),
        key="original_action",
        format_func=lambda i: f"#{by_id[i]['index']} · "
        f"P{by_id[i]['period']} {by_id[i]['timestamp']} · "
        f"{by_id[i]['type']['name']} · "
        f"{(by_id[i].get('player') or {}).get('name', 'Team record')}",
    )
    selected = by_id[event_id]
    st.markdown("#### Original record")
    st.code(event_id, language=None)
    st.caption(
        f"{names[selected['team']['id']]} · Provider index {selected['index']} · "
        f"Period {selected['period']} · Original timestamp {selected['timestamp']}"
    )
    with st.expander("View untouched source JSON", expanded=True):
        st.json(selected, expanded=1)
    st.markdown("#### Searchable event ledger")
    st.dataframe(
        [
            dict(
                Index=e["index"],
                Period=e["period"],
                Timestamp=e["timestamp"],
                Team=names[e["team"]["id"]],
                Action=e["type"]["name"],
                Player=(e.get("player") or {}).get("name"),
                Original_ID=e["id"],
            )
            for e in rows
        ],
        hide_index=True,
        width="stretch",
        height=350,
    )


def render_baseline(report: dict, names: dict, label: str) -> None:
    st.subheader("Baseline & limits")
    st.markdown(
        "Everything in the report can be reproduced from this conventional baseline "
        "and the original event ledger. The cards make evidence easier to inspect; "
        "incremental analyst value is untested."
    )
    st.markdown("#### Conventional chance totals")
    st.dataframe(
        [
            {"Team": names[r["team_id"]], "Shots": r["shot_count"], label: r["shot_weight"]}
            for r in report["team_totals"]
        ],
        hide_index=True,
        width="stretch",
    )
    st.markdown("#### Complete native-membership comparison")
    st.caption("Includes every eligible Shot-containing membership, not only the three cards.")
    units = [
        {
            "Team": names[u["team_id"]],
            "Period": u["period"],
            "Membership": u["possession_id"],
            "Shots": u["shot_count"],
            label: u["shot_weight"],
            "Complement home−away": u["complement_difference"],
            "Original Shot IDs": ", ".join(u["event_ids"]),
        }
        for u in report["native_units"]
    ]
    if units:
        st.dataframe(units, hide_index=True, width="stretch")
    else:
        st.info("No eligible Shot-containing memberships in this selection.")
    st.markdown("#### Native play-pattern mix")
    if report["phase_totals"]:
        st.dataframe(
            [
                {
                    "Team": names[r["team_id"]],
                    "Native phase": r["phase"],
                    "Shots": r["shot_count"],
                    label: r["shot_weight"],
                }
                for r in report["phase_totals"]
            ],
            hide_index=True,
            width="stretch",
        )
    st.markdown("#### Four claims, four evidence standards")
    for claim, standard in CLAIM_STANDARDS.items():
        st.markdown(f"**{claim}.** {standard}")
    st.markdown("#### What this system cannot conclude")
    for limit in report["limitations"]:
        st.write("• " + limit)
    with st.expander("Definitions, missingness & source provenance"):
        st.json(
            {
                "definitions": report["definitions"],
                "source": report["provenance"],
                "missing_shot_weight_ids": report["missing_shot_weight_ids"],
                "unresolved_membership_shot_ids": report["unresolved_membership_shot_ids"],
                "unknown_pass_outcome_ids": report["unknown_pass_outcome_ids"],
                "excluded_shootout_count": len(report["excluded_shootout_event_ids"]),
                "version": report["version"],
            }
        )


def main() -> None:
    started = perf_counter()
    st.html(
        '<div class="fil-nav"><span class="fil-logo">FIL</span>'
        '<span class="fil-wordmark">Football Intelligence Lab</span></div>'
    )
    library_path = os.environ.get("FIL_INTELLIGENCE_LIBRARY", "")
    try:
        library = json.loads(Path(library_path).read_text()) if library_path else None
        matches = catalog(library)
    except Exception as exc:
        st.error(f"Local library verification failed. No research analytics displayed: {exc}")
        st.stop()
    with st.sidebar:
        st.markdown("### Match workspace")
        mode = st.radio(
            "Data source",
            ["Fictional demo", "Local research"] if library else ["Fictional demo"],
            key="source_mode",
        )
        choices = [
            m
            for m in matches
            if m["mode"] == ("synthetic" if mode == "Fictional demo" else "local")
        ]
        labels = {m["id"]: m["title"] for m in choices}
        if st.session_state.get("match_choice") not in labels:
            st.session_state["match_choice"] = choices[0]["id"]
        mid = st.selectbox("Select match", list(labels), format_func=labels.get, key="match_choice")
        chosen = next(m for m in choices if m["id"] == mid)
        st.caption(chosen["date"])
        run = st.button("Run match analysis", type="primary", width="stretch")
        st.divider()
        st.caption("LOCAL PROCESSING · NO MODEL OR API KEY")
        st.caption("Verified facts. Inspectable evidence. Honest limits.")
        if not library:
            st.caption(
                "64-match local research adapter available to the authorized owner. "
                "No provider data is included in this demo."
            )
    demo = chosen["mode"] == "synthetic"
    if demo:
        st.warning(
            "FICTIONAL DEMO · Self-authored teams and actions. Illustrative shot weights "
            "are not provider xG, calibrated probabilities or research evidence."
        )
    else:
        st.warning(
            "PRIVATE LOCAL RESEARCH · Hudl/StatsBomb data. Do not publish, upload or "
            "redistribute these records, reports or screenshots."
        )
    if run:
        st.session_state["analyzed_match"] = mid
        st.session_state["workspace"] = "Intelligence report"
        reset_filters()
    active = st.session_state.get("analyzed_match") == mid
    if not active:
        st.html('<div class="fil-kicker">Match intelligence / evidence first</div>')
        st.title("See the match. Follow the evidence.")
        st.markdown(
            "Turn recorded football actions into a concise, reproducible match review. "
            "Follow every observation back to its original evidence."
        )
        if st.button("Analyze selected match", type="primary"):
            st.session_state["analyzed_match"] = mid
            st.session_state["workspace"] = "Intelligence report"
            reset_filters()
            st.rerun()
        st.html(
            f'<div class="fil-hero"><div class="fil-kicker">Selected match</div>'
            f'<h2>{esc(chosen["title"])}</h2><p class="fil-muted">'
            f"{esc(chosen['date'])} · {'Fictional demo' if demo else 'Verified local corpus'}"
            '</p><span class="fil-chip">01 / Verify source</span>'
            '<span class="fil-chip">02 / Compute report</span>'
            '<span class="fil-chip">03 / Challenge the interpretation</span></div>'
        )
        st.info("Choose a match in the sidebar, then select Run match analysis.")
        st.caption(
            "Deterministic analysis, not generative AI. Football usefulness and superior "
            "discovery have not been established."
        )
        return
    try:
        with st.spinner("Checking source identity, original records and score…"):
            token = mid if demo else fingerprint(library, int(mid))
            raw, meta, provenance = verified(
                mid, json.dumps(library, sort_keys=True) if not demo else "", token
            )
        verified_seconds = perf_counter() - started
        names = {meta[s][s + "_id"]: meta[s][s + "_name"] for s in ("home_team", "away_team")}
        score = f"{meta['home_score']} – {meta['away_score']}"
        st.html(
            f'<div class="fil-hero"><div class="fil-kicker">'
            f"{'Fictional records validated' if demo else 'Source verified'} / Match play</div>"
            f"<h2>{esc(list(names.values())[0])} &nbsp; {score} &nbsp; "
            f'{esc(list(names.values())[1])}</h2><p class="fil-muted">'
            f"{len(raw):,} original actions · {esc(chosen['date'])} · "
            "Full-match score stays visible under filtering</p></div>"
        )
        left, right, reset = st.columns([2, 2, 1])
        available = {
            0: "Full match",
            **{p: f"Period {p}" for p in sorted({e["period"] for e in raw if e["period"] < 5})},
        }
        period = left.selectbox(
            "Report period", list(available), format_func=available.get, key="report_period"
        )
        team = right.selectbox(
            "Report team",
            [0, *names],
            format_func=lambda x: names.get(x, "Both teams"),
            key="report_team",
        )
        reset.button("Reset filters", on_click=reset_filters, width="stretch")
        report = analyze(raw, meta, provenance, period=period or None, team=team or None)
    except Exception as exc:
        st.error(f"Source verification or analysis failed. No report displayed: {exc}")
        st.stop()
    label = "Demo shot weight" if demo else "Source xG"
    metrics = st.columns(4)
    metrics[0].metric("Selected actions", f"{report['selected_event_count']:,}")
    metrics[1].metric("Recorded Shots", report["shot_count"])
    metrics[2].metric(
        label,
        f"{float(report['shot_weight']):.3f}"
        if report["shot_weight"] is not None
        else "Unavailable",
    )
    metrics[3].metric("Completed passes", report["completed_pass_count"])
    st.caption(f"Shared selection · {available[period]} · {names.get(team, 'Both teams')}")
    workspace = st.radio(
        "Workspace",
        ["Intelligence report", "Evidence explorer", "Baseline & limits"],
        horizontal=True,
        key="workspace",
        label_visibility="collapsed",
    )
    if workspace == "Intelligence report":
        render_report(report, names, label)
    elif workspace == "Evidence explorer":
        render_evidence(raw, report, names)
    else:
        render_baseline(report, names, label)
    st.divider()
    digest = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    elapsed = perf_counter() - started
    st.caption(
        f"{VERSION} · Report {digest[:12]} · Python view execution {elapsed:.3f}s "
        f"(source/cache check {verified_seconds:.3f}s). Browser opening and rendering "
        "are additional; this is not a cold-start benchmark."
    )
    if demo:
        st.download_button(
            "Download fictional report JSON",
            json.dumps(report, indent=2),
            file_name=f"fil-{mid}-report.json",
            mime="application/json",
        )
    else:
        st.caption("Provider-derived export is disabled in this local research interface.")


if __name__ == "__main__":
    main()
