"""Fresh-process/browser benchmark; ledger milestone matches check_explorer_browser.py.

Server readiness and Chromium startup are measured separately, outside navigation.
No OS page-cache eviction is attempted: cold means a new server and browser context.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--port", type=int, default=8502)
    parser.add_argument("--tactical", action="store_true")
    parser.add_argument("--possession", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.runs <= 10 or not 1024 <= args.port <= 65535:
        parser.error("Expected 1..10 runs and an unprivileged port")
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    url = f"http://127.0.0.1:{args.port}"
    opener = build_opener(ProxyHandler({}))  # Loopback health check only; no remote access.
    with sync_playwright() as p:
        for run in range(args.runs):
            profile = args.output.resolve() / f"app-{run}.json"
            with (args.output / f"server-{run}.log").open("w") as log:
                started = time.perf_counter()
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
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env={**os.environ, "FIL_EXPLORER_PROFILE": str(profile)},
                )
                browser = None
                try:
                    while True:
                        try:
                            with opener.open(url + "/_stcore/health", timeout=1) as response:
                                if response.status == 200:
                                    break
                        except OSError:
                            pass
                        if process.poll() is not None or time.perf_counter() - started > 30:
                            raise RuntimeError(f"Server did not become ready; see {log.name}")
                        time.sleep(0.05)
                    server_seconds = time.perf_counter() - started
                    started = time.perf_counter()
                    browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
                    context = browser.new_context(viewport={"width": 1600, "height": 1150})
                    blocked = []

                    def route(request, blocked=blocked):
                        if request.request.url.startswith(
                            (url + "/", f"ws://127.0.0.1:{args.port}/")
                        ):
                            request.continue_()
                        else:
                            blocked.append(request.request.url.split("?")[0])
                            request.abort()

                    context.route("**/*", route)
                    page = context.new_page()
                    browser_seconds = time.perf_counter() - started
                    started = time.perf_counter()
                    page.goto(url, wait_until="domcontentloaded")
                    page.get_by_role("heading", name="Event ledger", exact=True).wait_for(
                        timeout=60000
                    )
                    ledger_seconds = time.perf_counter() - started
                    expect(page.get_by_test_id("stPlotlyChart")).to_have_count(4)
                    expect(page.get_by_test_id("stCode")).to_have_count(1)
                    expect(page.get_by_test_id("stMetricValue").nth(0)).to_have_text("2978")
                    expect(page.locator(".score")).to_contain_text("4 : 2")
                    expect(page.get_by_test_id("stException")).to_have_count(0)
                    complete_seconds = time.perf_counter() - started
                    result = {
                        "run": run,
                        "server_ready_seconds": server_seconds,
                        "browser_launch_seconds": browser_seconds,
                        "navigation_to_ledger_seconds": ledger_seconds,
                        "navigation_to_evidence_seconds": complete_seconds,
                        "blocked_external_requests": blocked,
                    }
                    if args.tactical:
                        config = json.loads(args.config.read_bytes())
                        raw = json.loads(
                            (Path(config["raw"]) / "data/events/8658.json").read_bytes()
                        )

                        def choose(label, value, page=page):
                            box = (
                                page.get_by_test_id("stSelectbox")
                                .filter(has=page.get_by_text(label, exact=True))
                                .get_by_role("combobox")
                            )
                            box.click()
                            page.get_by_role("option", name=value, exact=True).click()

                        def ready(subset, page=page):
                            passes = sum(
                                e["type"]["name"] == "Pass"
                                and "outcome" not in e["pass"]
                                and bool(e["pass"].get("recipient"))
                                for e in subset
                            )
                            expect(page.get_by_test_id("stMetricValue").nth(4)).to_have_text(
                                str(passes)
                            )
                            expect(page.get_by_test_id("stPlotlyChart")).to_have_count(3)
                            page.get_by_role(
                                "heading", name="Phase and game-state comparisons", exact=True
                            ).wait_for()
                            expect(page.get_by_test_id("stApp")).to_have_attribute(
                                "data-test-script-state", "notRunning"
                            )
                            for chart in page.get_by_test_id("stPlotlyChart").all():
                                assert chart.locator(".js-plotly-plot").evaluate("""e=>{
                                  const x=e._fullLayout.xaxis.range,y=e._fullLayout.yaxis.range;
                                  return Math.min(...x)>=-3 && Math.max(...x)<=123 &&
                                    Math.min(...y)>=-3 && Math.max(...y)<=83;
                                }""")

                        started = time.perf_counter()
                        choose("View", "Tactical Dashboard")
                        ready(raw)
                        result["tactical_open_seconds"] = time.perf_counter() - started
                        started = time.perf_counter()
                        choose("Period", "Period 2")
                        ready([e for e in raw if e["period"] == 2])
                        result["tactical_period_filter_seconds"] = time.perf_counter() - started
                        started = time.perf_counter()
                        choose("Team", "France")
                        ready([e for e in raw if e["period"] == 2 and e["team"]["id"] == 771])
                        result["tactical_team_filter_seconds"] = time.perf_counter() - started
                        expect(page.get_by_test_id("stException")).to_have_count(0)
                    if args.possession:
                        # Return to full-match scope before the separate possession milestone.
                        reset = page.get_by_role("button", name="Reset filters", exact=True)
                        reset.click()
                        expect(page.get_by_test_id("stMetricValue").nth(0)).to_have_text("2978")
                        box = (
                            page.get_by_test_id("stSelectbox")
                            .filter(has=page.get_by_text("View", exact=True))
                            .get_by_role("combobox")
                        )
                        started = time.perf_counter()
                        box.click()
                        page.get_by_role("option", name="Possession Flow", exact=True).click()
                        expect(page.get_by_test_id("stMetricValue").nth(4)).to_have_text("182")
                        page.get_by_role(
                            "heading", name="Ordered native action sequence", exact=True
                        ).wait_for()
                        expect(page.get_by_test_id("stApp")).to_have_attribute(
                            "data-test-script-state", "notRunning"
                        )
                        result["possession_open_seconds"] = time.perf_counter() - started
                    results.append(result)
                    print(json.dumps(result), flush=True)
                finally:
                    if browser is not None:
                        browser.close()
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=10)
    (args.output / "benchmark.json").write_text(
        json.dumps(
            {
                "method": "fresh server/browser; navigation to Event ledger; no OS cache eviction",
                "runs": results,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
