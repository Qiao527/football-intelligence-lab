"""Connected four-view desktop/mobile acceptance evidence; local use only."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

VIEWS = ["Match Explorer", "Tactical Dashboard", "Possession Flow", "Player Evidence"]
HEADINGS = ["Event ledger", "Tactical Dashboard", "Possession Flow", "Player Evidence"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8514")
    parser.add_argument("--output", type=Path, default=Path("data/interim/stabilization-review"))
    args = parser.parse_args()
    assert args.url.startswith("http://127.0.0.1:")
    args.output.mkdir(parents=True, exist_ok=True)
    config = json.loads(args.config.read_bytes())
    raw = json.loads((Path(config["raw"]) / "data/events/8658.json").read_bytes())
    by_id = {e["id"]: e for e in raw}
    checks, errors, blocked = [], [], []
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

        def idle():
            expect(page.get_by_test_id("stApp")).to_have_attribute(
                "data-test-script-state", "notRunning", timeout=30000
            )
            expect(page.get_by_test_id("stException")).to_have_count(0)

        def select(label, value):
            b = (
                page.get_by_test_id("stSelectbox")
                .filter(has=page.get_by_text(label, exact=True))
                .get_by_role("combobox")
            )
            b.scroll_into_view_if_needed()
            b.click()
            b.fill(value)
            page.get_by_role("option", name=value, exact=True).click()
            page.wait_for_timeout(350)
            idle()

        def ready(view, n):
            page.get_by_role("heading", name=HEADINGS[VIEWS.index(view)], exact=True).wait_for(
                timeout=30000
            )
            expect(page.get_by_test_id("stMetricValue").nth(0)).to_have_text(str(n), timeout=30000)
            expect(page.locator(".score")).to_contain_text("4 : 2")
            idle()

        second = [e for e in raw if e["period"] == 2 and e["team"]["id"] == 785]
        select("Period", "Period 2")
        select("Team", "Croatia")
        for view in VIEWS:
            select("View", view)
            ready(view, len(second))
            expect(
                page.get_by_text("Shared selection · Period 2 · Croatia", exact=True)
            ).to_be_visible()
            if view == "Possession Flow":
                expect(
                    page.get_by_role(
                        "heading", name="Same-possession co-occurrence · whole touched possessions"
                    )
                ).to_be_visible()
                expect(
                    page.get_by_text("Co-occurrence does not establish event order.", exact=False)
                ).to_be_visible()
            eid = page.get_by_test_id("stCode").inner_text()
            assert eid in by_id
            if view == "Match Explorer":
                assert by_id[eid] in second
        checks.append("Four views retain Period 2 / Croatia, original IDs and official score")
        page.get_by_role("button", name="Reset filters", exact=True).click()
        ready("Player Evidence", 2978)
        for group in ("Passing", "Progression", "Shot context", "Involvement"):
            select("Player table measures", group)
            expect(page.get_by_test_id("stDataFrame")).to_have_count(1)
            expect(page.get_by_text("Selected player ·", exact=False)).to_be_visible()
            expect(page.get_by_test_id("stMetricValue").nth(6)).to_have_text("650")
        checks.append("Four concise tables and selected-player measures; totals invariant")
        select("View", "Tactical Dashboard")
        ready("Tactical Dashboard", 2978)
        select("Minimum passes per displayed link", "3")
        for network in page.get_by_test_id("stPlotlyChart").all()[:2]:
            links = network.locator(".js-plotly-plot").evaluate(
                "e=>e.data.find(t=>t.name==='Pass links · click diamond').customdata"
            )
            assert links and all(x[1] >= 3 for x in links)
            assert network.locator(".annotation").count() == 0
            assert network.locator(".js-plotly-plot").evaluate(
                "e=>e.data.find(t=>t.name==='Directed arrowheads').x.length"
            ) == len(links)
        expect(page.get_by_test_id("stMetricValue").nth(4)).to_have_text("650")
        expect(page.get_by_test_id("stMetricValue").nth(5)).to_have_text("194")
        page.get_by_role("button", name="Reset filters", exact=True).click()
        ready("Tactical Dashboard", 2978)
        expect(
            page.get_by_test_id("stSelectbox").filter(
                has=page.get_by_text("Minimum passes per displayed link", exact=True)
            )
        ).to_contain_text("1")
        checks.append(
            "Batched arrows / display threshold preserve all 194 pairs; reset clears threshold"
        )
        for view in VIEWS:
            select("View", view)
            ready(view, 2978)
            page.evaluate("window.scrollTo(0,0)")
            page.screenshot(
                path=str(args.output / (view.split()[0].lower() + "-desktop.png")), full_page=True
            )
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(600)
        for view in VIEWS:
            button = page.get_by_test_id("stExpandSidebarButton")
            if button.is_visible():
                button.click()
            select("View", view)
            ready(view, 2978)
            close = page.get_by_test_id("stSidebarCollapseButton")
            if close.is_visible():
                close.click()
            else:
                # Streamlit 1.50 uses this test ID for the collapse control.
                close = page.get_by_test_id("stSidebar").get_by_role("button").first
                close.click()
            page.wait_for_timeout(600)
            page.get_by_role(
                "heading", name=HEADINGS[VIEWS.index(view)], exact=True
            ).scroll_into_view_if_needed()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            page.screenshot(
                path=str(args.output / (view.split()[0].lower() + "-mobile.png")), full_page=True
            )
            if view == "Player Evidence":
                page.get_by_text("Selected player ·", exact=False).scroll_into_view_if_needed()
            else:
                page.get_by_test_id("stPlotlyChart").first.scroll_into_view_if_needed()
            page.screenshot(
                path=str(args.output / (view.split()[0].lower() + "-mobile-detail.png"))
            )
        checks.append("390px all views, sidebar navigation, player details and no page overflow")
        browser.close()
    assert not errors and not blocked
    result = dict(checks=checks, page_errors=errors, blocked_external_requests=blocked)
    (args.output / "product-browser-report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
