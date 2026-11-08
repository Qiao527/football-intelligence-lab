"""Local-only exploratory replay of the source-audited SkillCorner match."""

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from fil.research.pass_lane import (
    passing_line_observation,
    position_screen,
    summarize_lane_timeline,
)
from fil.research.review_annotations import save_review
from fil.research.tracking_replay import (
    detected_trail,
    frame_distances,
    movement_candidate,
    tracking_window,
)

ROOT = Path(__file__).resolve().parents[1]
REV = "4340d274572876239c154c90bc507a9b3250a656"
RAW_ROOT = ROOT / "data" / "raw" / "skillcorner" / REV
INTERIM_ROOT = ROOT / "data" / "interim" / "skillcorner" / REV

st.set_page_config(page_title="FIL · Space Replay", layout="wide")
st.title("Space Replay")
st.caption("LOCAL RESEARCH · SkillCorner open data")
review_packets = sorted(INTERIM_ROOT.glob("*/blind-review-queue.json"))
position_packets = sorted(INTERIM_ROOT.glob("*/position-candidates.json"))
views = ["Exploration"]
if review_packets:
    views.append("Unlabelled review")
if position_packets:
    views.append("Low-movement positions")
mode = st.radio(
    "View",
    views,
    horizontal=True,
)
blind = mode == "Unlabelled review"
position_mode = mode == "Low-movement positions"
packets = review_packets if blind else position_packets
match_id = (
    st.selectbox("Review match", [p.parent.name for p in packets])
    if (blind or position_mode)
    else "1874553"
)
RAW = RAW_ROOT / match_id
INTERIM = INTERIM_ROOT / match_id
st.warning(
    "Exploratory tracking visualization, not match video or a verified tactical finding. "
    "Some player and ball positions are model-extrapolated; identities can be wrong."
)
try:
    meta = json.loads((RAW / f"{match_id}_match.json").read_text())
    queue_name = (
        "blind-review-queue.json"
        if blind
        else "position-candidates.json"
        if position_mode
        else "video-review-queue.json"
    )
    queue = json.loads((INTERIM / queue_name).read_text())
    qc = json.loads((INTERIM / "source-quality.json").read_text())
    if (
        qc["status"] != "WARN"
        or queue["status"] != "NOT_REVIEWED"
        or str(qc["match_id"]) != match_id
        or str(meta["id"]) != match_id
        or str(queue["match_id"]) != match_id
        or queue["source_revision"] != REV
        or qc["source_revision"] != REV
    ):
        raise ValueError("Source or review status is not eligible for this exploratory replay")
    for name in (
        f"{match_id}_match.json",
        f"{match_id}_tracking_extrapolated.jsonl",
        f"{match_id}_phases_of_play.csv",
    ):
        with (RAW / name).open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != queue["source_file_sha256"][name]:
            raise ValueError(f"Source hash mismatch: {name}")
    with (RAW / f"{match_id}_phases_of_play.csv").open(encoding="utf-8", newline="") as source:
        phases = list(csv.DictReader(source))
except (OSError, ValueError, KeyError) as exc:
    st.error(f"Local reviewed-source files are unavailable: {exc}")
    st.stop()

items = queue["items"]
st.caption(f"{meta['home_team']['name']} · {meta['away_team']['name']}")
selected = st.selectbox(
    "Review frame (unreviewed)" if blind else "Candidate frame (unreviewed)",
    range(len(items)),
    format_func=lambda i: f"Period {items[i]['period']} · {items[i]['match_timestamp']} "
    f"· frame {items[i]['frame_id']}",
)
candidate = items[selected]
frames = tracking_window(
    RAW / f"{match_id}_tracking_extrapolated.jsonl", candidate["frame_id"], candidate["period"]
)
if not frames:
    st.error("No source tracking frames found for this candidate.")
    st.stop()
players = {p["id"]: p for p in meta["players"]}
home = meta["home_team"]["id"]
away = meta["away_team"]["id"]
candidate_ids = [pid for pid in candidate["candidate_player_ids"] if pid in players]
if not candidate_ids:
    st.error("Candidate player identity is unavailable in source metadata.")
    st.stop()
focus = st.selectbox(
    "Review player" if blind else "Focus player (candidate at the selected frame)",
    candidate_ids,
    format_func=lambda pid: players[pid].get("short_name") or str(pid),
)
show_extrapolated = st.checkbox("Show extrapolated positions (hollow markers)", value=True)
observed = sum(
    any(
        p.get("player_id") == focus
        and p.get("is_detected") is True
        and p.get("x") is not None
        and p.get("y") is not None
        for p in f["player_data"]
    )
    for f in frames
)
st.caption(
    f"Focus player detected in {observed} of {len(frames)} sampled frames. "
    "The trail breaks where detection is missing; no positions are invented."
)
teams = {pid: p["team_id"] for pid, p in players.items()}
focus_team = teams[focus]
group = "home team" if focus_team == home else "away team"
if position_mode:
    source_window = [
        f for f in frames if candidate["frame_id"] - 20 <= f["frame"] <= candidate["frame_id"]
    ]
    position_result = position_screen(
        summarize_lane_timeline(
            [passing_line_observation(f, teams, home, away, focus) for f in source_window], phases
        )
    )
    if position_result["status"] != "candidate":
        st.error("Position hypothesis no longer passes the source checks; it cannot be displayed.")
        st.stop()
    st.info(
        "Low-movement geometry hypothesis: detected positions satisfy the illustrative rule "
        f"in {len(position_result['qualifying_frames'])} of five samples. This is not a "
        "confirmed passing option; unseen opponents may exist."
    )
if not blind:
    movement = movement_candidate(
        frames, focus, focus_team, group, teams, phases, candidate["frame_id"], candidate["period"]
    )
    if position_mode and (
        movement["status"] != "not_candidate" or movement["displacement_m"] is None
    ):
        st.error("Low-movement condition no longer passes the source checks.")
        st.stop()
    st.subheader("Two-second movement screen")
    if movement["status"] == "candidate":
        st.info(
            f"Exploratory candidate · {movement['displacement_m']:.1f} m displacement "
            f"across frames {movement['frame_ids'][0]}–{movement['frame_ids'][-1]}."
        )
    elif movement["status"] == "not_candidate":
        st.info(f"Does not meet this exploratory screen. {movement['reason']}")
    else:
        st.info(f"Insufficient evidence for this screen. {movement['reason']}")
    if movement["displacement_m"] is not None:
        start_x, start_y = movement["start"]
        end_x, end_y = movement["end"]
        st.caption(
            f"Source frames {movement['frame_ids'][0]}–{movement['frame_ids'][-1]} · "
            f"start ({start_x:.1f}, {start_y:.1f}) m · end ({end_x:.1f}, {end_y:.1f}) m."
        )
    st.caption(
        "Five detected samples at 0.5-second intervals, same provider in-play phase and "
        "teammate possession, consistent source timestamps, ≥3 m straight-line displacement. "
        "Provider possession is an estimate; "
        "movement between samples is unknown. This threshold is unvalidated: not a support action, "
        f"pass, player rating or contribution claim. Method: {movement['version']}."
    )


def traces(frame):
    result = []
    for team, colour in ((home, "#8dc8ff"), (away, "#ffba70")):
        for detected in (True, False):
            points = [
                p
                for p in frame["player_data"]
                if p.get("player_id") in players
                and players[p["player_id"]]["team_id"] == team
                and p.get("is_detected") is detected
                and p.get("x") is not None
                and p.get("y") is not None
                and (detected or show_extrapolated)
            ]
            result.append(
                go.Scatter(
                    x=[p["x"] for p in points],
                    y=[p["y"] for p in points],
                    mode="markers",
                    marker={
                        "size": 12,
                        "color": colour,
                        "symbol": "circle" if detected else "circle-open",
                        "line": {"width": 2},
                    },
                    text=[
                        players[p["player_id"]].get("short_name", str(p["player_id"]))
                        for p in points
                    ],
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=False,
                )
            )
    ball = frame.get("ball_data") or {}
    visible = (
        ball.get("x") is not None
        and ball.get("y") is not None
        and (
            ball.get("is_detected") is True
            or (show_extrapolated and ball.get("is_detected") is False)
        )
    )
    result.append(
        go.Scatter(
            x=[ball["x"]] if visible else [],
            y=[ball["y"]] if visible else [],
            mode="markers",
            marker={
                "size": 8,
                "color": "white",
                "symbol": "diamond" if ball.get("is_detected") is True else "diamond-open",
                "line": {"width": 2},
            },
            hovertemplate="Ball<extra></extra>",
            showlegend=False,
        )
    )
    trail_x, trail_y = detected_trail(frames, focus, frame["frame"])
    result.append(
        go.Scatter(
            x=trail_x,
            y=trail_y,
            mode="lines",
            line={"color": "#fff080", "width": 3},
            connectgaps=False,
            hoverinfo="skip",
            showlegend=False,
        )
    )
    focused = [
        p
        for p in frame["player_data"]
        if p.get("player_id") == focus
        and p.get("x") is not None
        and p.get("y") is not None
        and (p.get("is_detected") is True or (show_extrapolated and p.get("is_detected") is False))
    ]
    result.append(
        go.Scatter(
            x=[p["x"] for p in focused],
            y=[p["y"] for p in focused],
            mode="markers",
            marker={"size": 20, "symbol": "circle-open", "color": "#fff080", "line": {"width": 3}},
            hovertemplate="Focus player<extra></extra>",
            showlegend=False,
        )
    )
    # The geometric screen was calculated at the selected frame only.
    line = (
        not blind
        and not position_mode
        and frame["frame"] == candidate["frame_id"]
        and len(focused) == 1
        and focused[0].get("is_detected") is True
        and ball.get("is_detected") is True
        and ball.get("x") is not None
        and ball.get("y") is not None
    )
    result.append(
        go.Scatter(
            x=[ball["x"], focused[0]["x"]] if line else [],
            y=[ball["y"], focused[0]["y"]] if line else [],
            mode="lines",
            line={"color": "#fff080", "width": 2, "dash": "dot"},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    return result


length, width = meta["pitch_length"], meta["pitch_width"]


def evidence(frame):
    ball_distance, opponent_distance = frame_distances(frame, focus, teams)
    ball_text = f"{ball_distance:.1f} m" if ball_distance is not None else "unavailable"
    opponent_text = f"{opponent_distance:.1f} m" if opponent_distance is not None else "unavailable"
    return [
        {
            "text": f"Detected ball: {ball_text} · nearest detected opponent: {opponent_text}",
            "xref": "paper",
            "yref": "paper",
            "x": 0,
            "y": 1.1,
            "xanchor": "left",
            "showarrow": False,
            "font": {"color": "#ffffff", "size": 12},
        }
    ]


fig = go.Figure(data=traces(frames[0]))
fig.frames = [
    go.Frame(name=str(f["frame"]), data=traces(f), layout=go.Layout(annotations=evidence(f)))
    for f in frames
]
fig.add_shape(
    type="rect", x0=-length / 2, x1=length / 2, y0=-width / 2, y1=width / 2, line_color="#a7c2a9"
)
fig.add_shape(type="line", x0=0, x1=0, y0=-width / 2, y1=width / 2, line_color="#a7c2a9")
fig.add_shape(type="circle", x0=-9.15, x1=9.15, y0=-9.15, y1=9.15, line_color="#a7c2a9")
steps = [
    {
        "label": f["timestamp"],
        "method": "animate",
        "args": [
            [str(f["frame"])],
            {"mode": "immediate", "frame": {"duration": 0}, "transition": {"duration": 0}},
        ],
    }
    for f in frames
]
fig.update_layout(
    height=550,
    paper_bgcolor="#101b18",
    plot_bgcolor="#193b2a",
    margin=dict(l=15, r=15, t=42, b=20),
    annotations=evidence(frames[0]),
    xaxis={"range": [-length / 2 - 2, length / 2 + 2], "visible": False},
    yaxis={
        "range": [-width / 2 - 2, width / 2 + 2],
        "visible": False,
        "scaleanchor": "x",
        "scaleratio": 1,
    },
    sliders=[{"steps": steps, "currentvalue": {"prefix": "Match clock: "}}],
    updatemenus=[
        {
            "type": "buttons",
            "buttons": [
                {
                    "label": "Play",
                    "method": "animate",
                    "args": [
                        None,
                        {
                            "frame": {"duration": 500, "redraw": True},
                            "transition": {"duration": 0},
                            "fromcurrent": True,
                        },
                    ],
                },
                {
                    "label": "Pause",
                    "method": "animate",
                    "args": [
                        [None],
                        {
                            "mode": "immediate",
                            "frame": {"duration": 0},
                            "transition": {"duration": 0},
                        },
                    ],
                },
            ],
        }
    ],
)
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Blue: home · orange: away · diamond: ball · solid: detected · hollow: "
    "extrapolated · yellow ring: focus player · yellow trail: last 4 seconds of detected samples. "
    + (
        ""
        if blind or position_mode
        else "Dotted line: ball to candidate at selected frame, not a pass prediction. "
    )
    + "Nearest detected opponent is not necessarily the nearest actual opponent. "
    "Frames sampled at 2 Hz; no interpolation. Pitch is in provider metres; "
    "attack direction is not inferred. Hover for source player names."
)
st.caption("Source: SkillCorner Open Data, MIT. Match timestamps are not synchronized to video.")

if blind:
    st.subheader("Local review")
    st.caption(
        "Judge only what the tracking replay shows. Model and provider labels are hidden; "
        "this is not independent video validation."
    )
    review_key = f"{match_id}:{candidate['period']}:{candidate['frame_id']}:{focus}"
    answer = st.selectbox(
        "Does the player appear to offer a usable passing option?",
        ["Not reviewed", "Yes", "No", "Not observable"],
        key=f"answer:{review_key}",
    )
    notes = st.text_area("What supports or contradicts that judgment?", key=f"notes:{review_key}")
    reviewer = st.text_input("Reviewer pseudonym", key="local_reviewer")
    if st.button("Save local review"):
        if answer == "Not reviewed":
            st.error("Choose Yes, No or Not observable before saving.")
        elif not reviewer.strip():
            st.error("Enter a reviewer pseudonym before saving.")
        else:
            path = INTERIM / "review-annotations.json"
            record = {
                "match_id": match_id,
                "period": candidate["period"],
                "frame_id": candidate["frame_id"],
                "player_id": focus,
                "answer": answer,
                "notes": notes,
                "reviewer": reviewer.strip(),
                "reviewed_at_utc": datetime.now(UTC).isoformat(),
                "source_file_sha256": queue["source_file_sha256"],
            }
            try:
                save_review(path, record)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                st.error(f"Review could not be saved: {exc}")
            else:
                st.success("Review saved locally.")
