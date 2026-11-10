"""Real Chromium player evidence and native-context checks against original JSON."""

import argparse
import json
import re
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8510")
    parser.add_argument("--output", type=Path, default=Path("data/interim/player-review"))
    args = parser.parse_args()
    assert args.url.startswith("http://127.0.0.1:")
    args.output.mkdir(parents=True, exist_ok=True)
    config = json.loads(args.config.read_bytes())
    raw = json.loads((Path(config["raw"]) / "data/events/8658.json").read_bytes())
    by_id = {e["id"]: e for e in raw}
    linked = next(
        e
        for e in raw
        if e["type"]["name"] == "Pass" and e["pass"].get("assisted_shot_id") and e["period"] == 2
    )
    errors, blocked, timings, checks = [], [], {}, []
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

        def box(label):
            return (
                page.get_by_test_id("stSelectbox")
                .filter(has=page.get_by_text(label, exact=True))
                .get_by_role("combobox")
            )

        def select(label, value, regex=False):
            b = box(label)
            b.scroll_into_view_if_needed()
            b.click()
            b.fill(value)
            page.get_by_role(
                "option", name=re.compile(value) if regex else value, exact=not regex
            ).click()
            page.wait_for_timeout(350)
            idle()

        def idle():
            expect(page.get_by_test_id("stApp")).to_have_attribute(
                "data-test-script-state", "notRunning", timeout=30000
            )
            expect(page.get_by_test_id("stException")).to_have_count(0)

        def count(n):
            expect(page.get_by_test_id("stMetricValue").nth(0)).to_have_text(str(n), timeout=30000)
            idle()
            expect(page.locator(".score")).to_contain_text("4 : 2")

        page.goto(args.url)
        page.get_by_role("heading", name="Event ledger", exact=True).wait_for(timeout=60000)
        started = time.perf_counter()
        select("View", "Player Evidence")
        page.get_by_role("heading", name="Player Evidence", exact=True).wait_for(timeout=30000)
        count(2978)
        expect(page.get_by_test_id("stMetricValue").nth(4)).to_have_text("27")
        expect(page.get_by_test_id("stMetricValue").nth(5)).to_have_text("16")
        expect(page.get_by_test_id("stMetricValue").nth(6)).to_have_text("650")
        timings["player_open_seconds"] = time.perf_counter() - started
        page.get_by_role("heading", name="Player Evidence", exact=True).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "desktop-players.png"))
        checks.append("2978 events / 27 actors / 16 reciprocal links / 650 completed passes / 4:2")
        select("Period", "Period 2")
        count(sum(e["period"] == 2 for e in raw))
        select("Event type", "Pass")
        count(sum(e["period"] == 2 and e["type"]["name"] == "Pass" for e in raw))
        key = f"{linked['team']['id']}:{linked['player']['id']}"
        select("Player evidence record", key, regex=True)
        select("Player evidence type", "Native linked passes")
        select("Player original event", linked["id"])
        expect(page.get_by_test_id("stCode")).to_have_text(linked["id"])
        select("Player evidence type", "Context shots")
        shot_id = linked["pass"]["assisted_shot_id"]
        assert by_id[shot_id]["shot"]["key_pass_id"] == linked["id"]
        select("Player original event", shot_id)
        expect(page.get_by_test_id("stCode")).to_have_text(shot_id)
        expect(page.get_by_text(re.compile("matches shared filter: False"))).to_be_visible()
        idle()
        page.get_by_role(
            "heading", name="Native position metadata", exact=True
        ).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "source-context.png"))
        checks.append(
            "Period/type filters; reciprocal original pass/shot IDs and outside-filter context"
        )
        page.get_by_role("button", name="Reset filters", exact=True).click()
        count(2978)
        select("Team", "Croatia")
        count(sum(e["team"]["id"] == 785 for e in raw))
        expect(
            page.get_by_test_id("stSelectbox").filter(
                has=page.get_by_text("Player evidence record", exact=True)
            )
        ).to_contain_text("785:")
        page.get_by_role("button", name="Reset filters", exact=True).click()
        count(2978)
        select("Event type", "Camera On")
        count(sum(e["type"]["name"] == "Camera On" for e in raw))
        expect(
            page.get_by_text(
                "No player actor records match this selection. No contribution inferred.",
                exact=True,
            )
        ).to_be_visible()
        checks.append(
            "Team choice resets stale player selection; actorless records remain in shared KPIs"
        )
        page.get_by_role("button", name="Reset filters", exact=True).click()
        count(2978)
        for view, toggle in (
            ("Possession Flow", "Show detailed possession audit"),
            ("Tactical Dashboard", "Show detailed tactical audit"),
        ):
            select("View", view)
            before = page.get_by_test_id("stDataFrame").count()
            page.get_by_text(toggle, exact=True).click()
            expect(page.get_by_test_id("stDataFrame")).to_have_count(
                before + (2 if view == "Possession Flow" else 3)
            )
            idle()
            count(2978)
            page.get_by_text(toggle, exact=True).click()
            expect(page.get_by_test_id("stDataFrame")).to_have_count(before)
            idle()
        names = page.get_by_text("Show all player names", exact=True)
        names.click()
        idle()
        expect(page.get_by_test_id("stPlotlyChart")).to_have_count(3)
        checks.append(
            "Opt-in full audits restore tables without changing source KPIs; network name toggle"
        )
        select("View", "Player Evidence")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(600)  # Complete Streamlit sidebar resize animation.
        page.get_by_role("heading", name="Player Evidence", exact=True).scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.screenshot(path=str(args.output / "mobile-players.png"))
        page.get_by_test_id("stExpandSidebarButton").click()
        select("Team", "France")
        count(sum(e["team"]["id"] == 771 for e in raw))
        checks.append("390px mobile table/filters without horizontal page overflow")
        select("View", "Match Explorer")
        page.get_by_role("heading", name="Event ledger", exact=True).wait_for(timeout=30000)
        expect(page.get_by_test_id("stMetricValue").nth(2)).to_have_text("1.098")
        expect(page.get_by_test_id("stPlotlyChart")).to_have_count(4)
        idle()
        assert not errors
        browser.close()
    report = dict(
        checks=checks, timings=timings, page_errors=errors, blocked_external_requests=blocked
    )
    (args.output / "browser-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
