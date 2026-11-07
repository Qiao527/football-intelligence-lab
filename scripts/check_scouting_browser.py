"""Exercise the synthetic discovery journey against a running local web server."""

import argparse
import json

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--browser", required=True, help="Path to a Chromium executable")
parser.add_argument("--url", default="http://127.0.0.1:8650")
args = parser.parse_args()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser, headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(args.url, wait_until="networkidle")
    page.get_by_text("PLAYER MATCH RECORDS").first.wait_for()
    initial = page.locator("#players tr").count()
    assert initial > 0
    page.locator("#query").fill("no such player")
    assert page.get_by_text("No players match these filters.", exact=False).is_visible()
    page.locator("#query").fill("Fictional player 1")
    assert 0 < page.locator("#players tr").count() < initial
    page.locator("#match-filter").select_option("demo-1")
    assert all(
        "Northbridge FC vs Harbour Athletic" in t
        for t in page.locator("#players tr").all_inner_texts()
    )
    page.locator("#team-filter").select_option(label="Northbridge FC")
    assert all(
        t == "Northbridge FC" for t in page.locator("#players .person small").all_inner_texts()
    )
    page.get_by_role("button", name="View Fictional player 1", exact=False).first.click()
    assert page.locator("#profile").is_visible()
    assert int(page.locator("#stats strong").first.inner_text()) == page.locator(".action").count()
    page.locator(".action").first.click()
    record = json.loads(page.locator("#inspector pre").inner_text())
    assert record["player"]["name"] == "Fictional player 1"
    assert record["id"].startswith("demo-1-action-")
    page.get_by_role("button", name="Back to discovery").click()
    assert page.locator("#query").input_value() == "Fictional player 1"
    page.get_by_role("link", name="Match intelligence").click()
    page.locator("#run").wait_for(state="visible")
    page.locator("#run").click()
    page.locator("#result").wait_for(state="visible")
    assert "Northbridge FC" in page.locator("#fixture").inner_text()
    page.get_by_role("button", name="Inspect original actions").first.click()
    match_record = json.loads(page.locator("#raw").inner_text())
    assert match_record["id"].startswith("demo-1-action-")
    page.get_by_role("button", name="Baseline & limits").click()
    assert page.locator("#totals tr").count() == 2
    page.get_by_role("link", name="SCOUTING DISCOVERY").click()
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator("#players tr").first.wait_for()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.locator("#players button").first.click()
    page.locator(".action").first.click()
    assert page.locator("#inspector pre").is_visible()
    assert not errors, errors
    print(
        f"PASS: {initial} player-match records; search, match filter, profile, "
        "source action, return, match report and mobile"
    )
    browser.close()
