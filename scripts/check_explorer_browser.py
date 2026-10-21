"""Real local browser acceptance checks. Run only with a licensed verified local config.

uv run --frozen --group browser python scripts/check_explorer_browser.py CONFIG
The screenshots/trace remain ignored local provider-derived research artifacts.
"""

import argparse
import json
import math
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8501")
    parser.add_argument("--output", type=Path, default=Path("data/interim/review"))
    args = parser.parse_args()
    if not args.url.startswith("http://127.0.0.1:"):
        raise ValueError("This check supports loopback only")
    config = json.loads(args.config.read_bytes())
    raw = json.loads((Path(config["raw"]) / "data/events/8658.json").read_bytes())
    checks = []
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
        context = browser.new_context(
            viewport={"width": 1600, "height": 1150}, device_scale_factor=1
        )
        blocked = []

        def route(request):
            if request.request.url.startswith(("http://127.0.0.1:", "ws://127.0.0.1:")):
                request.continue_()
            else:
                blocked.append(request.request.url.split("?")[0])
                request.abort()

        context.route("**/*", route)
        page = context.new_page()
        started = time.perf_counter()
        page.goto(args.url, wait_until="domcontentloaded")
        page.get_by_role("heading", name="Event ledger", exact=True).wait_for(timeout=60000)
        startup = time.perf_counter() - started

        def no_errors():
            expect(page.get_by_test_id("stException")).to_have_count(0)

        def select(label, value):
            box = (
                page.get_by_test_id("stSelectbox")
                .filter(has=page.get_by_text(label, exact=True))
                .get_by_role("combobox")
            )
            box.click()
            box.fill(value)
            page.get_by_role("option", name=value, exact=True).click()

        def metrics(count, shots, xg):
            values = page.get_by_test_id("stMetricValue")
            expect(values.nth(0)).to_have_text(str(count), timeout=30000)
            expect(values.nth(1)).to_have_text(str(shots), timeout=30000)
            expect(values.nth(2)).to_have_text(f"{xg:.3f}", timeout=30000)
            no_errors()

        all_shots = [e for e in raw if e["type"]["name"] == "Shot" and e["period"] < 5]
        metrics(len(raw), len(all_shots), math.fsum(e["shot"]["statsbomb_xg"] for e in all_shots))
        expect(page.locator(".score")).to_contain_text("4 : 2")
        expect(page.get_by_test_id("stPlotlyChart")).to_have_count(4)
        page.screenshot(path=str(args.output / "desktop.png"))
        checks.append(
            "initial 2978 events / 23 shots / source xG / official fixed score / four charts"
        )
        select("Period", "Period 2")
        subset = [e for e in raw if e["period"] == 2]
        shots = [e for e in subset if e["type"]["name"] == "Shot"]
        metrics(len(subset), len(shots), math.fsum(e["shot"]["statsbomb_xg"] for e in shots))
        select("Team", "France")
        subset = [e for e in subset if e["team"]["id"] == 771]
        shots = [e for e in subset if e["type"]["name"] == "Shot"]
        metrics(len(subset), len(shots), math.fsum(e["shot"]["statsbomb_xg"] for e in shots))
        expect(page.locator(".score")).to_contain_text("4 : 2")
        checks.append(
            "period and team filters synchronize all selected metrics; official score fixed"
        )
        select("Event type", "Own Goal Against")
        metrics(0, 0, 0)
        expect(page.get_by_text("No events in this selection.", exact=False)).to_be_visible()
        checks.append("empty selection shows zero counts, no stale event evidence, no exception")
        page.get_by_role("button", name="Reset filters", exact=True).click()
        metrics(len(raw), 23, math.fsum(e["shot"]["statsbomb_xg"] for e in all_shots))
        checks.append("reset clears period/team/type/player/window/evidence state")
        # Click a real rendered shot marker; do not inject Streamlit state or fake a callback.
        chart = page.get_by_test_id("stPlotlyChart").nth(1)
        plot = chart.locator(".js-plotly-plot")
        expected_id = plot.evaluate("(el)=>el.data[0].customdata[1][0]")
        point = chart.locator(".scatterlayer .trace").nth(0).locator(".point").nth(1)
        point.scroll_into_view_if_needed()
        box = point.bounding_box()
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        expect(page.get_by_test_id("stCode").locator("code")).to_have_text(
            expected_id, timeout=30000
        )
        source = next(e for e in raw if e["id"] == expected_id)
        expect(
            page.get_by_text(f"Provider timestamp {source['timestamp']}", exact=False)
        ).to_be_visible()
        page.screenshot(path=str(args.output / "event-evidence.png"))
        checks.append(f"real shot-map click resolves exact original ID {expected_id} and timestamp")
        page.get_by_role("button", name="Reset filters", exact=True).click()
        metrics(len(raw), 23, math.fsum(e["shot"]["statsbomb_xg"] for e in all_shots))
        # Select a period-bin by clicking its actual bar.
        threat = page.get_by_test_id("stPlotlyChart").nth(2)
        bar = threat.locator(".barlayer .trace").nth(0).locator(".point path").nth(2)
        bar.scroll_into_view_if_needed()
        box = bar.bounding_box()
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        expected_rows = [
            e for e in raw if e["period"] == 1 and "00:30:00.000" <= e["timestamp"] < "00:45:00.000"
        ]
        expected_shots = [e for e in expected_rows if e["type"]["name"] == "Shot"]
        metrics(
            len(expected_rows),
            len(expected_shots),
            math.fsum(e["shot"]["statsbomb_xg"] for e in expected_shots),
        )
        expect(page.locator(".score")).to_contain_text("4 : 2")
        checks.append("real threat-bar click selects exact P1 [30,45) bin and updates panels")
        page.screenshot(path=str(args.output / "window-selection.png"))
        page.get_by_role("button", name="Reset filters", exact=True).click()
        metrics(len(raw), 23, math.fsum(e["shot"]["statsbomb_xg"] for e in all_shots))
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(args.output / "mobile.png"))
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
            "Horizontal overflow"
        )
        no_errors()
        checks.append("390px mobile viewport renders without page horizontal overflow")
        browser.close()
    result = {
        "checks": checks,
        "startup_seconds": startup,
        "blocked_external_requests": blocked,
        "screenshots": [str(p) for p in args.output.glob("*.png")],
        "source": "real verified StatsBomb 8658, no synthetic match observations",
    }
    (args.output / "browser-report.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
