"""Retain every sample of the local MVP browser benchmark; no speedup claim.

Each repetition launches a fresh Python server and Chromium process. This measures
process-cold startup with a warm OS/package cache, not machine-cold installation.
Opening includes server and browser startup, navigation, analysis and rendering.
Interaction uses a verified expected metric plus idle state and two animation
frames. The legacy four-view timings are a different workload and not a comparator.
"""

import argparse
import hashlib
import http.client
import json
import os
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def summary(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "n": len(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0,
        "min": min(values),
        "max": max(values),
        "p90_nearest_rank": ordered[max(0, (9 * len(values) + 9) // 10 - 1)],
    }


def local_route(origin: str, external: list[str]):
    """One positional callback: Playwright supplies Request as an optional second arg."""

    def handle(route):
        if route.request.url.startswith((origin, origin.replace("http:", "ws:"))):
            route.continue_()
        else:
            external.append(route.request.url)
            route.abort()

    return handle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--base-port", type=int, default=8530)
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    parser.add_argument("--library", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("data/interim/intelligence/benchmark.json")
    )
    args = parser.parse_args()
    if args.repetitions < 1 or not 1024 <= args.base_port <= 65535 - args.repetitions:
        parser.error("Positive repetitions and valid local port range required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    samples = []
    external = []
    with sync_playwright() as p:
        for n in range(args.repetitions):
            port = args.base_port + n
            url = f"http://127.0.0.1:{port}"
            cmd = [sys.executable, "-m", "fil.intelligence", "run", "--port", str(port)]
            if args.library:
                cmd += ["--local-library", str(args.library)]
            started = time.perf_counter()
            log = args.output.parent / f"{args.output.stem}-server-{n:02d}.log"
            with log.open("w") as handle:
                server = subprocess.Popen(
                    cmd, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True
                )
                browser = None
                try:
                    while True:
                        if server.poll() is not None or time.perf_counter() - started > 30:
                            raise RuntimeError(f"Local server failed; see {log}")
                        try:
                            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
                            connection.request("GET", "/_stcore/health")
                            ready = connection.getresponse().status == 200
                            connection.close()
                            if ready:
                                break
                        except OSError:
                            pass
                        time.sleep(0.03)
                    server_ready = time.perf_counter() - started
                    browser = p.chromium.launch(executable_path=args.chromium, headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 1100})

                    page.route("**/*", local_route(url, external))
                    page.goto(url)
                    page.get_by_role(
                        "heading", name="See the match. Follow the evidence."
                    ).wait_for()
                    landing = time.perf_counter() - started

                    def select(label, value, page=page):
                        box = (
                            page.get_by_test_id("stSelectbox")
                            .filter(has=page.get_by_text(label, exact=True))
                            .get_by_role("combobox")
                        )
                        box.click()
                        box.fill(value)
                        page.get_by_role("option", name=value, exact=True).click()

                    if args.library:
                        page.get_by_text("Local research", exact=True).click()
                        select("Select match", "France vs Croatia")
                    clicked = time.perf_counter()
                    page.get_by_role("button", name="Run match analysis", exact=True).click()
                    page.get_by_role(
                        "heading", name="Match Intelligence Report", exact=True
                    ).wait_for()

                    def idle(page=page):
                        expect(page.get_by_test_id("stApp")).to_have_attribute(
                            "data-test-script-state", "notRunning", timeout=30000
                        )
                        expect(page.get_by_test_id("stException")).to_have_count(0)
                        expect(page.get_by_test_id("stPlotlyChart")).to_have_count(2)
                        expect(page.locator(".js-plotly-plot")).to_have_count(2)
                        page.wait_for_function(
                            "[...document.querySelectorAll('.js-plotly-plot')]"
                            ".every(e => !!e._fullLayout)"
                        )
                        page.evaluate(
                            "() => new Promise(r => requestAnimationFrame("
                            "() => requestAnimationFrame(r)))"
                        )

                    idle()
                    finished = time.perf_counter()
                    interactions = []
                    for name, metric in (
                        ("Period 2", "15" if args.library else "7"),
                        ("Full match", "23" if args.library else "14"),
                    ):
                        t = time.perf_counter()
                        select("Report period", name)
                        expect(page.get_by_test_id("stMetricValue").nth(1)).to_have_text(metric)
                        idle()
                        interactions.append({"filter": name, "seconds": time.perf_counter() - t})
                    samples.append(
                        {
                            "repetition": n + 1,
                            "server_ready_seconds": server_ready,
                            "landing_including_server_browser_seconds": landing,
                            "analysis_click_to_render_seconds": finished - clicked,
                            "opening_including_server_browser_seconds": finished - started,
                            "interactions": interactions,
                        }
                    )
                finally:
                    try:
                        if browser:
                            browser.close()
                    finally:
                        try:
                            os.killpg(server.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        server.wait(timeout=10)
            args.output.write_text(
                json.dumps({"status": "IN_PROGRESS", "samples": samples}, indent=2) + "\n"
            )
    assert not external, external
    report = {
        "status": "PASS",
        "mode": "local" if args.library else "synthetic",
        "method": __doc__,
        "repetitions": args.repetitions,
        "samples": samples,
        "opening": summary([s["opening_including_server_browser_seconds"] for s in samples]),
        "analysis_click": summary([s["analysis_click_to_render_seconds"] for s in samples]),
        "interaction": summary([i["seconds"] for s in samples for i in s["interactions"]]),
        "external_requests": external,
        "legacy_speedup_measured": False,
        "code_sha256": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [*Path("src/fil/intelligence").glob("*.py"), Path(__file__)]
        },
        "python": sys.version,
        "browser": "System Chromium at " + args.chromium,
        "comparison_with_pre_fix_is_valid": False,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("samples", "method")}, indent=2))


if __name__ == "__main__":
    main()
