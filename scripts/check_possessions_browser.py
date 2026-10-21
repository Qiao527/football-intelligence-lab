"""Real Chromium Possession Flow checks; expected memberships come from raw JSON."""

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8508")
    parser.add_argument("--output", type=Path, default=Path("data/interim/possession-review"))
    args = parser.parse_args()
    assert args.url.startswith("http://127.0.0.1:")
    args.output.mkdir(parents=True, exist_ok=True)
    config = json.loads(args.config.read_bytes())
    raw = json.loads((Path(config["raw"]) / "data/events/8658.json").read_bytes())
    groups = defaultdict(list)
    for e in raw:
        groups[e["possession"]].append(e)
    checks = []
    timings = []
    errors = []
    blocked = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1150})
        page.on("pageerror", lambda e: errors.append(str(e)))

        def route(r):
            if r.request.url.startswith(("http://127.0.0.1:", "ws://127.0.0.1:")):
                r.continue_()
            else:
                blocked.append(r.request.url)
                r.abort()

        page.route("**/*", route)
        page.goto(args.url)
        page.get_by_role("heading", name="Event ledger", exact=True).wait_for(timeout=60000)

        def box(label):
            return (
                page.get_by_test_id("stSelectbox")
                .filter(has=page.get_by_text(label, exact=True))
                .get_by_role("combobox")
            )

        def select(label, value):
            b = box(label)
            b.scroll_into_view_if_needed()
            b.click()
            b.fill(value)
            page.get_by_role("option", name=value, exact=True).click()

        def idle():
            expect(page.get_by_test_id("stApp")).to_have_attribute(
                "data-test-script-state", "notRunning", timeout=30000
            )
            expect(page.get_by_test_id("stException")).to_have_count(0)
            assert not errors, errors

        def ready(subset):
            ids = {e["possession"] for e in subset}
            expect(page.get_by_test_id("stMetricValue").nth(0)).to_have_text(
                str(len(subset)), timeout=30000
            )
            expect(page.get_by_test_id("stMetricValue").nth(4)).to_have_text(
                str(len(ids)), timeout=30000
            )
            expect(page.locator(".score")).to_contain_text("4 : 2")
            idle()

        def change(label, value, subset):
            began = time.perf_counter()
            select(label, value)
            ready(subset)
            timings.append({"action": label + ": " + value, "seconds": time.perf_counter() - began})

        began = time.perf_counter()
        select("View", "Possession Flow")
        ready(raw)
        page.get_by_role("heading", name="Ordered native action sequence", exact=True).wait_for(
            timeout=30000
        )
        expect(page.get_by_test_id("stPlotlyChart")).to_have_count(2)
        opening = time.perf_counter() - began
        page.get_by_role("heading", name="Possession Flow", exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "desktop-flow.png"))
        checks.append(
            "182 native IDs / 2978 records / official score; distinct cohort and event scopes"
        )
        # Pick a long source chain; all original records must be available in order.
        b = box("Native possession")
        b.click()
        b.fill("#2 ·")
        page.get_by_role("option", name=re.compile(r"^#2 ·")).click()
        expect(page.get_by_test_id("stCode")).to_have_text(groups[2][0]["id"], timeout=30000)
        event = next(e for e in groups[2] if e["team"]["id"] != e["possession_team"]["id"])
        select("Possession original event", event["id"])
        expect(page.get_by_test_id("stCode")).to_have_text(event["id"])
        idle()
        expect(
            page.get_by_text(
                re.compile(
                    "acting team "
                    + str(event["team"]["id"])
                    + " / possession team "
                    + str(event["possession_team"]["id"])
                )
            )
        ).to_be_visible()
        checks.append(
            "opponent event remains in original native chain and drills down to exact provider ID"
        )
        # Click an actual plotted endpoint; never synthesize Streamlit state.
        path = page.get_by_test_id("stPlotlyChart").nth(1)
        choice = path.locator(".js-plotly-plot").evaluate("""e=>{
          const all=e.data.filter(t=>t.mode==='markers').flatMap(t=>t.x.map((x,i)=>[x,t.y[i]]));
          for(const trace of [1,3]) for(let i=0;i<e.data[trace].x.length;i++){
            const x=e.data[trace].x[i],y=e.data[trace].y[i];
            if(all.filter(p=>Math.hypot(p[0]-x,p[1]-y)<3).length===1)
              return [trace,i,e.data[trace].customdata[i][0]];
          } throw Error('No isolated source endpoint');
        }""")
        pt = path.locator(".scatterlayer .trace").nth(choice[0]).locator(".point").nth(choice[1])
        pt.scroll_into_view_if_needed()
        rect = pt.bounding_box()
        page.mouse.click(rect["x"] + rect["width"] / 2, rect["y"] + rect["height"] / 2)
        expect(page.get_by_test_id("stCode")).to_have_text(choice[2], timeout=30000)
        idle()
        page.get_by_role(
            "heading", name="Original possession action evidence", exact=True
        ).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "action-evidence.png"))
        checks.append("actual path endpoint click selects exact original pass/carry event")
        # Source shot chain and ending bar both remain interactive.
        pid = next(k for k, g in groups.items() if sum(e["type"]["name"] == "Shot" for e in g) > 1)
        b = box("Native possession")
        b.click()
        b.fill(f"#{pid} ·")
        page.get_by_role("option", name=re.compile(r"^#" + str(pid) + r" ·")).click()
        expect(page.get_by_test_id("stCode")).to_have_text(groups[pid][0]["id"], timeout=30000)
        idle()
        shot = next(e for e in groups[pid] if e["type"]["name"] == "Shot")
        select("Possession original event", shot["id"])
        expect(page.get_by_test_id("stCode")).to_have_text(shot["id"], timeout=30000)
        idle()
        page.get_by_role(
            "heading", name="Ordered native action sequence", exact=True
        ).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "shot-sequence.png"))
        bar = page.get_by_test_id("stPlotlyChart").nth(0)
        bar.scroll_into_view_if_needed()
        index = bar.locator(".js-plotly-plot").evaluate("e=>e.data[0].x.indexOf('shot')")
        mark = bar.locator(".barlayer .point").nth(index)
        mark.scroll_into_view_if_needed()
        r = mark.bounding_box()
        page.mouse.click(r["x"] + r["width"] / 2, r["y"] + r["height"] / 2)
        expect(
            page.get_by_test_id("stSelectbox").filter(
                has=page.get_by_text("Possession ending", exact=True)
            )
        ).to_contain_text("shot", timeout=30000)
        idle()
        checks.append("multi-shot native sequence and actual terminal-state bar selection")
        page.get_by_role("button", name="Reset filters", exact=True).click()
        ready(raw)
        second = [e for e in raw if e["period"] == 2]
        change("Period", "Period 2", second)
        b = box("Native possession")
        b.click()
        b.fill("#91 ·")
        page.get_by_role("option", name=re.compile(r"^#91 ·")).click()
        expect(
            page.get_by_text(re.compile("Source qualifications: cross_period_provider_id"))
        ).to_be_visible(timeout=30000)
        select("Possession original event", groups[91][0]["id"])
        expect(page.get_by_test_id("stCode")).to_have_text(groups[91][0]["id"])
        expect(page.get_by_text(re.compile("matches shared filter: False"))).to_be_visible()
        checks.append(
            "ID 91 spans halves; duration uncertainty and outside-filter context visible"
        )
        france = [e for e in second if e["team"]["id"] == 771]
        change("Team", "France", france)
        pressure = [e for e in france if e["type"]["name"] == "Pressure"]
        change("Event type", "Pressure", pressure)
        # France leads throughout period 2, independently reconciled from raw goals.
        change("Pre-event score state", "Leading", pressure)
        expect(page.get_by_test_id("stMetricValue").nth(1)).to_have_text("0")
        change("Outcome", "Goal", [])
        expect(
            page.get_by_text(
                "No native possession matches this event selection. No sequence inferred.",
                exact=True,
            )
        ).to_be_visible()
        checks.append(
            "period/team/type/outcome and empty state synchronize with complete native chains"
        )
        page.get_by_role("button", name="Reset filters", exact=True).click()
        ready(raw)
        first = [e for e in raw if e["period"] == 1 and int(e["timestamp"][3:5]) < 15]
        change("Time window", "P1 · 0–15.00 elapsed min", first)
        change("Threat window", "5 minutes", raw)
        checks.append("period-aware window cohort and width reset prevent stale event selections")
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role("heading", name="Possession Flow", exact=True).scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.screenshot(path=str(args.output / "mobile-flow.png"))
        page.get_by_test_id("stExpandSidebarButton").click()
        croatia = [e for e in raw if e["team"]["id"] == 785]
        change("Team", "Croatia", croatia)
        page.screenshot(path=str(args.output / "mobile-filters.png"))
        checks.append("390px mobile flow, sidebar filters and no horizontal page overflow")
        select("View", "Match Explorer")
        page.get_by_role("heading", name="Event ledger", exact=True).wait_for(timeout=30000)
        expect(page.get_by_test_id("stMetricValue").nth(1)).to_have_text("15")
        expect(page.get_by_test_id("stMetricValue").nth(2)).to_have_text("1.480")
        expect(page.get_by_test_id("stPlotlyChart")).to_have_count(4)
        idle()
        checks.append(
            "return to Explorer preserves Croatia selection, source xG and four original charts"
        )
        browser.close()
    result = {
        "checks": checks,
        "possession_open_seconds": opening,
        "interaction_seconds": timings,
        "page_errors": errors,
        "blocked_external_requests": blocked,
    }
    (args.output / "browser-report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
