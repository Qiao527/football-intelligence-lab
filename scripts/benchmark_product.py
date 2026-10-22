"""Interleaved fresh-server/browser pairs with CDP CPU, websocket and rendering traces.

All traces remain local: they can contain provider-derived interface content.
Cold means a new process/browser, without OS page-cache eviction. No warm-up sample
is discarded. Parent/candidate order alternates AB/BA across pairs.
"""

import argparse
import base64
import hashlib
import json
import os
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

from playwright.sync_api import expect, sync_playwright

VIEWS = {
    "Match Explorer": ("Event ledger", 4),
    "Tactical Dashboard": ("Phase and game-state comparisons", 3),
    "Possession Flow": ("Ordered native action sequence", 2),
    "Player Evidence": ("Evidence and limits", 0),
}


def digest(source):
    h = hashlib.sha256()
    for p in sorted(source.rglob("*.py")):
        h.update(str(p.relative_to(source)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def summarize(results):
    report = {}
    for stage in results[0]["stages"]:
        report[stage] = {}
        for label in ("parent", "candidate"):
            values = [r["stages"][stage]["seconds"] for r in results if r["label"] == label]
            if not values:
                continue
            report[stage][label] = dict(
                n=len(values),
                median=statistics.median(values),
                mean=statistics.mean(values),
                stdev=statistics.stdev(values) if len(values) > 1 else 0,
                minimum=min(values),
                maximum=max(values),
                p90=sorted(values)[max(0, (9 * len(values) + 9) // 10 - 1)],
                samples=values,
            )
        if all(k in report[stage] for k in ("parent", "candidate")):
            pairs = {}
            for r in results:
                pairs.setdefault(r["pair"], {})[r["label"]] = r["stages"][stage]["seconds"]
            delta = [p["candidate"] - p["parent"] for p in pairs.values() if len(p) == 2]
            report[stage]["paired_delta"] = dict(
                samples=delta,
                median=statistics.median(delta),
                candidate_faster=sum(d < 0 for d in delta),
            )
    return report


def run(p, args, source, label, pair, raw):
    stem = args.output / f"{pair:02d}-{label}"
    profile = stem.with_suffix(".profile.json").resolve()
    url = f"http://127.0.0.1:{args.port}"
    env = {**os.environ, "PYTHONPATH": str(source.resolve()), "FIL_EXPLORER_PROFILE": str(profile)}
    opener = build_opener(ProxyHandler({}))
    browser = None
    with stem.with_suffix(".server.log").open("w") as log:
        start = time.perf_counter()
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "fil.explorer",
                "--config",
                str(args.config.resolve()),
                "--port",
                str(args.port),
            ],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            while True:
                try:
                    with opener.open(url + "/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
                if process.poll() is not None or time.perf_counter() - start > 30:
                    raise RuntimeError("Server readiness failed")
                time.sleep(0.05)
            server = time.perf_counter() - start
            start = time.perf_counter()
            browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 1150})
            browser_seconds = time.perf_counter() - start
            errors, blocked, frames = [], [], []
            page.on("pageerror", lambda e: errors.append(str(e)))

            def route(r):
                if r.request.url.startswith((url + "/", f"ws://127.0.0.1:{args.port}/")):
                    r.continue_()
                else:
                    blocked.append(r.request.url.split("?")[0])
                    r.abort()

            page.route("**/*", route)
            cdp = page.context.new_cdp_session(page)
            cdp.send("Network.enable")
            cdp.send("Performance.enable")

            def frame(e):
                r = e["response"]
                body = r["payloadData"]
                size = len(base64.b64decode(body)) if r["opcode"] == 2 else len(body.encode())
                frames.append({"timestamp": e["timestamp"], "bytes": size})

            cdp.on("Network.webSocketFrameReceived", frame)
            cdp.send(
                "Tracing.start",
                {
                    "categories": "devtools.timeline,blink.user_timing,v8.execute",
                    "transferMode": "ReturnAsStream",
                },
            )
            stages = {}

            def choose(label, value):
                box = (
                    page.get_by_test_id("stSelectbox")
                    .filter(has=page.get_by_text(label, exact=True))
                    .get_by_role("combobox")
                )
                box.click()
                page.get_by_role("option", name=value, exact=True).click()

            def ready(view, subset):
                heading, charts = VIEWS[view]
                page.get_by_role("heading", name=heading, exact=True).wait_for(timeout=60000)
                expect(page.get_by_test_id("stMetricValue").nth(0)).to_have_text(
                    str(len(subset)), timeout=60000
                )
                expect(page.get_by_test_id("stPlotlyChart")).to_have_count(charts)
                if view != "Match Explorer":
                    expected = sum(
                        e["type"]["name"] == "Pass"
                        and "outcome" not in e["pass"]
                        and bool(e["pass"].get("recipient"))
                        for e in subset
                    )
                    if view == "Possession Flow":
                        expected = len({e["possession"] for e in subset})
                    if view == "Player Evidence":
                        expected = len(
                            {
                                (e["team"]["id"], e["player"]["id"])
                                for e in subset
                                if e.get("player")
                            }
                        )
                    expect(page.get_by_test_id("stMetricValue").nth(4)).to_have_text(
                        str(expected), timeout=60000
                    )
                expect(page.get_by_test_id("stApp")).to_have_attribute(
                    "data-test-script-state", "notRunning", timeout=60000
                )
                expect(page.get_by_test_id("stException")).to_have_count(0)
                expect(page.get_by_test_id("stCode")).to_have_count(1)
                expect(page.locator(".score")).to_contain_text("4 : 2")
                for chart in page.get_by_test_id("stPlotlyChart").all():
                    expect(chart.locator(".js-plotly-plot")).to_have_count(1)
                    assert chart.locator(".js-plotly-plot").evaluate("e=>!!e._fullLayout")
                page.evaluate(
                    "()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))"
                )
                assert not errors, errors

            def measure(name, action, view, subset):
                before = {
                    x["name"]: x["value"] for x in cdp.send("Performance.getMetrics")["metrics"]
                }
                first = len(frames)
                start = time.perf_counter()
                action()
                ready(view, subset)
                duration = time.perf_counter() - start
                after = {
                    x["name"]: x["value"] for x in cdp.send("Performance.getMetrics")["metrics"]
                }
                stages[name] = dict(
                    seconds=duration,
                    websocket_messages=len(frames) - first,
                    websocket_payload_bytes=sum(f["bytes"] for f in frames[first:]),
                    browser_cpu={
                        k: after[k] - before.get(k, 0)
                        for k in (
                            "TaskDuration",
                            "ScriptDuration",
                            "LayoutDuration",
                            "RecalcStyleDuration",
                        )
                    },
                    server_profile=json.loads(profile.read_bytes()),
                )
                print(
                    json.dumps(
                        dict(pair=pair, label=label, stage=name, seconds=round(duration, 3))
                    ),
                    flush=True,
                )

            ledger_elapsed = []

            def navigate():
                started = time.perf_counter()
                page.goto(url, wait_until="domcontentloaded")
                page.get_by_role("heading", name="Event ledger", exact=True).wait_for(timeout=60000)
                ledger_elapsed.append(time.perf_counter() - started)

            measure("explorer_cold", navigate, "Match Explorer", raw)
            stages["explorer_cold"]["ledger_seconds"] = ledger_elapsed[0]
            for view in VIEWS:
                key = view.split()[0].lower()
                if view != "Match Explorer":
                    measure(key + "_open", lambda v=view: choose("View", v), view, raw)
                second = [e for e in raw if e["period"] == 2]
                measure(key + "_period2", lambda: choose("Period", "Period 2"), view, second)
                measure(key + "_full", lambda: choose("Period", "Full match"), view, raw)
            done = []
            cdp.on("Tracing.tracingComplete", lambda e: done.append(e))
            cdp.send("Tracing.end")
            while not done:
                page.wait_for_timeout(50)
            handle = done[0]["stream"]
            with stem.with_suffix(".trace.json").open("w") as out:
                while True:
                    chunk = cdp.send("IO.read", {"handle": handle})
                    out.write(chunk["data"])
                    if chunk.get("eof"):
                        break
            cdp.send("IO.close", {"handle": handle})
            trace = json.loads(stem.with_suffix(".trace.json").read_bytes())
            costs = {}
            for e in trace["traceEvents"]:
                if e.get("ph") == "X" and e["name"] in (
                    "Layout",
                    "UpdateLayoutTree",
                    "FunctionCall",
                    "EvaluateScript",
                    "Paint",
                ):
                    costs[e["name"]] = costs.get(e["name"], 0) + e.get("dur", 0) / 1e6
            return dict(
                pair=pair,
                label=label,
                source_digest=digest(source),
                stages=stages,
                server_ready_seconds=server,
                browser_launch_seconds=browser_seconds,
                trace_inclusive_seconds=costs,
                page_errors=errors,
                blocked_external_requests=blocked,
            )
        finally:
            if browser:
                browser.close()
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=10)
    parser.add_argument("--port", type=int, default=8512)
    args = parser.parse_args()
    if not 1 <= args.pairs <= 30 or not 1024 <= args.port <= 65535:
        parser.error("Expected 1..30 pairs and unprivileged port; acceptance requires >=10 pairs")
    args.output.mkdir(parents=True, exist_ok=True)
    config = json.loads(args.config.read_bytes())
    raw = json.loads((Path(config["raw"]) / "data/events/8658.json").read_bytes())
    sources = {"parent": args.parent, "candidate": args.candidate}
    hashes = {k: digest(v) for k, v in sources.items()}
    results = []
    with sync_playwright() as p:
        for pair in range(args.pairs):
            for label in ("parent", "candidate") if pair % 2 == 0 else ("candidate", "parent"):
                assert hashes == {k: digest(v) for k, v in sources.items()}, (
                    "Code changed during benchmark"
                )
                results.append(run(p, args, sources[label], label, pair, raw))
                report = dict(
                    method=(
                        "Alternating AB/BA, fresh processes/browser, no OS cache eviction; "
                        "trace enabled equally"
                    ),
                    source_digests=hashes,
                    results=results,
                    summary=summarize(results),
                )
                (args.output / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    assert hashes == {k: digest(v) for k, v in sources.items()}


if __name__ == "__main__":
    main()
