"""Real Chromium MVP checks. Synthetic images are reusable; local data stays ignored."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8520")
    parser.add_argument("--output", type=Path, default=Path("data/interim/intelligence/browser"))
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    parser.add_argument(
        "--local-library",
        type=Path,
        help="Optional existing local catalog; real-data checks take no screenshots",
    )
    args = parser.parse_args()
    if not args.url.startswith("http://127.0.0.1:"):
        parser.error("Only loopback verification is supported")
    args.output.mkdir(parents=True, exist_ok=True)
    errors, blocked, checks, timing = [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        def route(r):
            if r.request.url.startswith((args.url, args.url.replace("http:", "ws:"))):
                r.continue_()
            else:
                blocked.append(r.request.url)
                r.abort()

        page.route("**/*", route)

        def idle():
            expect(page.get_by_test_id("stApp")).to_have_attribute(
                "data-test-script-state", "notRunning", timeout=30000
            )
            expect(page.get_by_test_id("stException")).to_have_count(0)

        def charts_ready():
            expect(page.locator(".js-plotly-plot")).to_have_count(2)
            page.wait_for_function(
                "[...document.querySelectorAll('.js-plotly-plot')].every(e => !!e._fullLayout)"
            )

        def top():
            page.get_by_test_id("stMain").evaluate("e => e.scrollTo(0,0)")

        def select(label, value):
            box = (
                page.get_by_test_id("stSelectbox")
                .filter(has=page.get_by_text(label, exact=True))
                .get_by_role("combobox")
            )
            box.scroll_into_view_if_needed()
            box.click()
            box.fill(value)
            page.get_by_role("option", name=value, exact=True).click()

        page.goto(args.url)
        page.get_by_role("heading", name="See the match. Follow the evidence.").wait_for()
        idle()
        assert "Fictional demo" in page.get_by_test_id("stSidebar").inner_text()
        # This script intentionally refuses to capture a real-data workspace.
        assert "PRIVATE LOCAL RESEARCH" not in page.locator("body").inner_text()
        page.screenshot(path=str(args.output / "landing-desktop.png"), full_page=True)
        start = perf_counter()
        page.get_by_role("button", name="Analyze selected match", exact=True).click()
        page.get_by_role("heading", name="Match Intelligence Report", exact=True).wait_for()
        expect(page.get_by_test_id("stMetricValue").nth(1)).to_have_text("14")
        idle()
        charts_ready()
        timing.append({"action": "first_demo_analysis", "seconds": perf_counter() - start})
        expect(page.get_by_text("Usefulness unmeasured", exact=True)).to_have_count(3)
        page.screenshot(path=str(args.output / "report-desktop.png"), full_page=True)
        page.get_by_role("heading", name="Match Intelligence Report", exact=True).evaluate(
            "e => e.scrollIntoView({block:'start'})"
        )
        page.get_by_test_id("stMain").evaluate("e => e.scrollTop -= 80")
        page.screenshot(path=str(args.output / "report-detail-desktop.png"))
        page.get_by_role("button", name="Inspect original actions", exact=False).first.click()
        page.get_by_role("heading", name="Evidence explorer", exact=True).wait_for()
        idle()
        source_id = page.get_by_test_id("stCode").inner_text().strip()
        assert source_id.startswith("demo-1-action-")
        expect(page.get_by_text("View untouched source JSON", exact=True)).to_be_visible()
        page.screenshot(path=str(args.output / "evidence-desktop.png"), full_page=True)
        checks.append("Dynamic report opens original fictional action and complete membership")
        select("Report period", "Period 2")
        select("Report team", "Northbridge FC")
        expect(page.get_by_test_id("stMetricValue").nth(1)).to_have_text("3")
        page.get_by_role("button", name="Reset filters", exact=True).click()
        expect(page.get_by_test_id("stMetricValue").nth(0)).to_have_text("66")
        page.get_by_text("Baseline & limits", exact=True).click()
        page.get_by_role("heading", name="Four claims, four evidence standards").wait_for()
        idle()
        page.screenshot(path=str(args.output / "baseline-desktop.png"), full_page=True)
        checks.append("Team/period filters, reset, full baseline and four distinct claim standards")
        select("Select match", "Beacon City vs Westhaven Town")
        expect(page.get_by_test_id("stMetricValue")).to_have_count(0)
        page.get_by_role("button", name="Run match analysis", exact=True).click()
        page.get_by_role("heading", name="Match Intelligence Report", exact=True).wait_for()
        select("Report period", "Period 2")
        expect(page.get_by_test_id("stMetricValue").nth(1)).to_have_text("0")
        expect(page.get_by_text("No recorded Shots in this selection.", exact=True)).to_be_visible()
        checks.append("Changing match removes stale report; no-Shot selection abstains")
        select("Select match", "Atlas United vs Riverside FC")
        page.get_by_role("button", name="Run match analysis", exact=True).click()
        page.get_by_role("heading", name="Match Intelligence Report", exact=True).wait_for()
        expect(page.get_by_test_id("stMetricValue").nth(1)).to_have_text("14")
        checks.append("All three fictional matches compute successfully")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)  # Responsive auto-collapse starts asynchronously.
        sidebar = page.get_by_test_id("stSidebar")
        if sidebar.get_attribute("aria-expanded") == "true":
            sidebar.get_by_role("button").first.click()
        idle()
        charts_ready()
        page.wait_for_timeout(400)  # Let the framework's responsive sidebar transition finish.
        top()
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        box = page.locator(".fil-hero").bounding_box()
        assert box and box["x"] >= 0 and box["x"] + box["width"] <= 391
        logo = page.locator(".fil-logo").bounding_box()
        assert logo and logo["y"] >= 64
        page.screenshot(path=str(args.output / "report-mobile.png"), full_page=True)
        page.locator(".fil-card").first.scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "report-mobile-detail.png"))
        page.get_by_role("button", name="Inspect original actions", exact=False).first.click()
        page.get_by_role("heading", name="Evidence explorer", exact=True).wait_for()
        idle()
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.get_by_role("heading", name="Original record", exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "evidence-mobile.png"), full_page=True)
        page.get_by_role("textbox", name="Search original actions", exact=True).fill("NO_SUCH_ID")
        page.get_by_role("textbox", name="Search original actions", exact=True).press("Enter")
        expect(
            page.get_by_text("No original actions match these filters.", exact=False)
        ).to_be_visible()
        checks.append(
            "390px report/evidence, original ID inspection, empty search and no page overflow"
        )
        if args.local_library:
            from fil.intelligence.sources import load

            library = json.loads(args.local_library.read_bytes())
            page.set_viewport_size({"width": 1440, "height": 1100})
            page.wait_for_timeout(400)
            if sidebar.get_attribute("aria-expanded") != "true":
                page.get_by_test_id("stExpandSidebarButton").click()
            page.get_by_text("Local research", exact=True).click()
            for mid in ("8658", "7570"):
                raw, meta, _ = load(mid, library)
                name = (
                    meta["home_team"]["home_team_name"]
                    + " vs "
                    + meta["away_team"]["away_team_name"]
                )
                select("Select match", name)
                page.get_by_role("button", name="Run match analysis", exact=True).click()
                page.get_by_role("heading", name="Match Intelligence Report", exact=True).wait_for()
                shots = [e for e in raw if e["type"]["name"] == "Shot" and e["period"] < 5]
                expect(page.get_by_test_id("stMetricValue").nth(0)).to_have_text(f"{len(raw):,}")
                expect(page.get_by_test_id("stMetricValue").nth(1)).to_have_text(str(len(shots)))
                expect(
                    page.get_by_role("button", name="Download fictional report JSON")
                ).to_have_count(0)
                charts_ready()
                page.get_by_role(
                    "button", name="Inspect original actions", exact=False
                ).first.click()
                page.get_by_role("heading", name="Evidence explorer", exact=True).wait_for()
                idle()
                event_id = page.get_by_test_id("stCode").inner_text().strip()
                assert event_id in {e["id"] for e in raw}
                checks.append(f"Local match {mid}: source counts, original ID and no report export")
        browser.close()
    assert not errors and not blocked, {"page_errors": errors, "external_requests": blocked}
    result = {
        "checks": checks,
        "page_errors": errors,
        "external_requests": blocked,
        "timing_samples": timing,
        "synthetic_only_screenshots": True,
    }
    (args.output / "browser-report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
