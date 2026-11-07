"""Check the synthetic Copilot and opt-in local journey in Chromium."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--browser", required=True)
parser.add_argument("--url", default="http://127.0.0.1:8650")
args = parser.parse_args()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser, headless=True)
    for width, height in [(1440, 900), (390, 844)]:
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
        page.goto(args.url, wait_until="networkidle")
        assert page.evaluate("FILAnalytics.snapshot().sessions.length") == 0
        page.get_by_text("Optional local journey measurement").click()
        page.get_by_role("button", name="Start local measurement").click()
        page.get_by_role("button", name="Find candidates").click()
        page.locator(".candidate-card").first.wait_for()
        assert page.locator(".candidate-card").get_by_text("Mara Vale", exact=True).is_visible()
        assert page.get_by_text("RULE-BASED PREVIEW", exact=False).first.is_visible()
        assert page.get_by_text("Contradictory actions:").first.is_visible()
        page.get_by_role("button", name="demo-scout-action-010").click()
        page.locator("#profile").wait_for(state="visible")
        assert page.locator(".pitch svg").is_visible()
        original = json.loads(page.locator("#inspector pre").inner_text())
        assert original["id"] == "demo-scout-action-010"
        assert original["pass"]["outcome"]["name"] == "Incomplete"
        page.get_by_role("button", name="Mark investigation complete").click()
        session = page.evaluate("FILAnalytics.snapshot()")
        assert [x["stage"] for x in session["sessions"][0]["events"]] == [
            "discovery", "candidate", "player_profile", "evidence", "completed_investigation"
        ]
        assert "Mara" not in json.dumps(session) and "query" not in json.dumps(session)
        with page.expect_download() as download_info:
            page.get_by_role("button", name="Download session").click()
        assert json.loads(Path(download_info.value.path()).read_text()) == session
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.get_by_role("button", name="Back to discovery").click()
        page.locator("#scout-need").fill("Rate these players and invent their potential")
        page.get_by_role("button", name="Find candidates").click()
        page.locator(".copilot-abstain").wait_for()
        assert page.locator(".candidate-card").count() == 0
        assert not errors, errors
        page.close()
    page = browser.new_page()
    page.route("**/api/scout-fixture", lambda route: route.abort())
    page.goto(args.url, wait_until="networkidle")
    page.locator("#players tr").first.wait_for()
    assert page.locator("#players tr").count() == 24
    assert page.get_by_text("The scouting fixture is unavailable", exact=False).is_visible()
    page.close()
    browser.close()
print("PASS: Copilot evidence, pitch, abstention and local journey on desktop and mobile")
