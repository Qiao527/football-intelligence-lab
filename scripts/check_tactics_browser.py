"""Real Chromium tactical interactions against original local source events."""

import argparse
import json
import math
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8504")
    parser.add_argument("--output", type=Path, default=Path("data/interim/tactical-review"))
    args = parser.parse_args()
    if not args.url.startswith("http://127.0.0.1:"):
        raise ValueError("Loopback only")
    args.output.mkdir(parents=True, exist_ok=True)
    config = json.loads(args.config.read_bytes())
    raw = json.loads((Path(config["raw"]) / "data/events/8658.json").read_bytes())
    by_id = {e["id"]: e for e in raw}
    complete = [
        e
        for e in raw
        if e["type"]["name"] == "Pass" and "outcome" not in e["pass"] and e["pass"].get("recipient")
    ]
    scores = {771: 0, 785: 0}
    contexts = {}
    counted = set()
    for e in raw:
        team = e["team"]["id"]
        diff = scores[team] - scores[785 if team == 771 else 771]
        contexts[e["id"]] = "Level" if diff == 0 else "Leading" if diff > 0 else "Trailing"
        if e["type"]["name"] == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            scores[team] += 1
        if e["type"]["name"] in ("Own Goal For", "Own Goal Against") and e["id"] not in counted:
            pair = [e] + [
                by_id[i]
                for i in e.get("related_events", [])
                if by_id[i]["type"]["name"] in ("Own Goal For", "Own Goal Against")
            ]
            credit = next(p["team"]["id"] for p in pair if p["type"]["name"] == "Own Goal For")
            scores[credit] += 1
            counted.update(p["id"] for p in pair)
    timings = []
    checks = []
    errors = []
    blocked = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1150})

        def route(r):
            if r.request.url.startswith(("http://127.0.0.1:", "ws://127.0.0.1:")):
                r.continue_()
            else:
                blocked.append(r.request.url)
                r.abort()

        page.route("**/*", route)
        page.on("pageerror", lambda e: errors.append(str(e)))
        started = time.perf_counter()
        page.goto(args.url, wait_until="domcontentloaded")
        page.get_by_role("heading", name="Event ledger", exact=True).wait_for(timeout=60000)
        startup = time.perf_counter() - started

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

        def idle():
            expect(page.get_by_test_id("stApp")).to_have_attribute(
                "data-test-script-state", "notRunning", timeout=30000
            )
            expect(page.get_by_test_id("stException")).to_have_count(0)
            assert not errors, errors

        def metrics(subset):
            ids = {e["id"] for e in subset}
            passes = [e for e in complete if e["id"] in ids]
            pairs = {
                (e["team"]["id"], e["player"]["id"], e["pass"]["recipient"]["id"]) for e in passes
            }
            progressive = {"Pass": 0, "Carry": 0}
            for e in subset:
                kind = e["type"]["name"]
                if (
                    kind not in progressive
                    or kind == "Pass"
                    and e["id"] not in {p["id"] for p in passes}
                ):
                    continue
                start = e.get("location")
                end = e[kind.lower()].get("end_location")
                if (
                    start
                    and end
                    and end[0] > start[0]
                    and math.hypot(120 - start[0], 40 - start[1])
                    - math.hypot(120 - end[0], 40 - end[1])
                    >= 10
                ):
                    progressive[kind] += 1
            values = page.get_by_test_id("stMetricValue")
            for i, value in (
                (0, len(subset)),
                (4, len(passes)),
                (5, len(pairs)),
                (6, progressive["Pass"]),
                (7, progressive["Carry"]),
            ):
                expect(values.nth(i)).to_have_text(str(value), timeout=30000)
            idle()
            expect(page.locator(".score")).to_contain_text("4 : 2")
            return passes

        def change(label, value, subset):
            began = time.perf_counter()
            select(label, value)
            metrics(subset)
            timings.append({"action": label + ": " + value, "seconds": time.perf_counter() - began})

        began = time.perf_counter()
        select("View", "Tactical Dashboard")
        page.get_by_role("heading", name="Phase and game-state comparisons", exact=True).wait_for(
            timeout=60000
        )
        metrics(raw)
        open_seconds = time.perf_counter() - began
        page.get_by_role(
            "heading", name="Tactical Dashboard", exact=True
        ).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "desktop-network.png"))
        checks.append("full source pass/progression totals and score context")
        # Actual diamond marker click, not synthetic Streamlit state.
        network = page.get_by_test_id("stPlotlyChart").nth(0)
        expected_key = network.locator(".js-plotly-plot").evaluate("e=>e.data[3].customdata[3][0]")
        _, team, actor, receiver = expected_key.split(":")
        edge_ids = [
            e["id"]
            for e in complete
            if (e["team"]["id"], e["player"]["id"], e["pass"]["recipient"]["id"])
            == (int(team), int(actor), int(receiver))
        ]
        point = network.locator(".scatterlayer .trace").nth(3).locator(".point").nth(3)
        point.scroll_into_view_if_needed()
        box = point.bounding_box()
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        expect(page.get_by_test_id("stCode")).to_have_text(edge_ids[0], timeout=30000)
        idle()
        checks.append(
            "actual directed-edge click resolves first exact contributing original pass ID"
        )
        network = page.get_by_test_id("stPlotlyChart").nth(0)
        expected_key = network.locator(".js-plotly-plot").evaluate("e=>e.data[4].customdata[1][0]")
        _, team, player = expected_key.split(":")
        involved = [
            e["id"]
            for e in complete
            if e["team"]["id"] == int(team)
            and int(player) in (e["player"]["id"], e["pass"]["recipient"]["id"])
        ]
        point = network.locator(".scatterlayer .trace").nth(4).locator(".point").nth(1)
        point.scroll_into_view_if_needed()
        box = point.bounding_box()
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        expect(page.get_by_test_id("stCode")).to_have_text(involved[0], timeout=30000)
        idle()
        checks.append("actual player-node click resolves incoming/outgoing pass evidence")
        prog = page.get_by_test_id("stPlotlyChart").nth(2)
        choice = prog.locator(".js-plotly-plot").evaluate("""e=>{
          const all=e.data.filter(t=>t.mode==='markers').flatMap(t=>t.x.map((x,i)=>[x,t.y[i]]));
          for(const trace of [1,3]) for(let i=0;i<e.data[trace].x.length;i++){
            const x=e.data[trace].x[i],y=e.data[trace].y[i];
            if(all.filter(p=>Math.hypot(p[0]-x,p[1]-y)<3).length===1)
              return [trace,i,e.data[trace].customdata[i][0]];
          } throw Error('No isolated progression endpoint');
        }""")
        point = prog.locator(".scatterlayer .trace").nth(choice[0]).locator(".point").nth(choice[1])
        point.scroll_into_view_if_needed()
        box = point.bounding_box()
        page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        expect(page.get_by_test_id("stCode")).to_have_text(choice[2], timeout=30000)
        idle()
        page.get_by_role(
            "heading", name="Exact tactical source evidence", exact=True
        ).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "event-evidence.png"))
        checks.append("actual progression endpoint click resolves original source event")
        half = [e for e in raw if e["period"] == 2]
        change("Period", "Period 2", half)
        france = [e for e in half if e["team"]["id"] == 771]
        change("Team", "France", france)
        leading = [e for e in france if contexts[e["id"]] == "Leading"]
        change("Pre-event score state", "Leading", leading)
        change("Event type", "Shot", [e for e in leading if e["type"]["name"] == "Shot"])
        expect(
            page.get_by_text("No pass/carry evidence in this selection.", exact=False)
        ).to_be_visible()
        checks.append("period/team/pre-event score/type and no-pass state synchronize")
        page.get_by_role("button", name="Reset filters", exact=True).click()
        metrics(raw)
        select("Comparison", "Two explicit windows")
        expect(
            page.get_by_test_id("stSelectbox").filter(
                has=page.get_by_text("Comparison A", exact=True)
            )
        ).to_contain_text("P1 [0, 15]", timeout=30000)
        select("Comparison A", "P1 [30, 45] elapsed min end excluded")
        idle()
        page.get_by_role(
            "heading", name="Phase and game-state comparisons", exact=True
        ).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "comparison.png"))
        select("Comparison", "Score states")
        idle()
        checks.append(
            "two explicit windows and score-state comparison controls render without exceptions"
        )
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role(
            "heading", name="Tactical Dashboard", exact=True
        ).scroll_into_view_if_needed()
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.screenshot(path=str(args.output / "mobile-overview.png"))
        page.get_by_test_id("stPlotlyChart").nth(0).scroll_into_view_if_needed()
        page.screenshot(path=str(args.output / "mobile-network.png"))
        page.get_by_test_id("stExpandSidebarButton").click()
        croatia = [e for e in raw if e["team"]["id"] == 785]
        change("Team", "Croatia", croatia)
        page.screenshot(path=str(args.output / "mobile-filters.png"))
        checks.append(
            "390px mobile controls update tactical metrics without horizontal page overflow"
        )
        select("View", "Match Explorer")
        page.get_by_role("heading", name="Event ledger", exact=True).wait_for(timeout=30000)
        expect(page.get_by_test_id("stPlotlyChart")).to_have_count(4)
        idle()
        values = page.get_by_test_id("stMetricValue")
        expect(values.nth(1)).to_have_text("15")
        expect(values.nth(2)).to_have_text("1.480")
        checks.append(
            "return to Explorer preserves shared Croatia filter, source xG and four original charts"
        )
        browser.close()
    result = {
        "checks": checks,
        "v03_startup_seconds": startup,
        "tactical_open_seconds": open_seconds,
        "interaction_seconds": timings,
        "page_errors": errors,
        "blocked_external_requests": blocked,
    }
    (args.output / "browser-report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
