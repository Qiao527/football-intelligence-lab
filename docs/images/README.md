# Match Intelligence screenshots

The four match-review PNGs below are actual Chromium captures of the running application using FIL's
self-authored fictional fixtures. They contain no real provider records or real player names.
They are not static app content; the application generates reports from actions at runtime.

- `match-intelligence-selection.png`: desktop match-selection entry point.
- `match-intelligence-desktop.png`: rendered charts, scoped observations and evidence controls.
- `match-intelligence-mobile.png`: 390px review cards.
- `match-intelligence-evidence-mobile.png`: original fictional ID and JSON drilldown.

Reproduce with `scripts/check_intelligence_browser.py` against the local app in its default
fictional mode. Explicit screenshots are taken before the script's optional real-data checks.
Provider-derived screenshots remain under ignored `data/` and must not be added here.

## Synthetic Scout Copilot (deployed alpha)

These PNGs are Chromium captures of the deployed synthetic app at
`https://fil-public-alpha.vercel.app`, made on 2026-11-10. They contain fictional players and
actions only; no provider records, credentials or model output are shown.

- `scout-candidates.png`: Scout Copilot returning two candidates with supporting and
  contradictory event IDs.
- `scout-player.png`: player evidence view with pitch markers, action list and original JSON
  inspector.
- `scout-mobile.png`: 390px candidate view from the same deployment.

Reproduce with a Playwright session against the deployed URL, or locally with
`scripts/serve_public_web.py` plus `scripts/check_scout_copilot_browser.py`.

## Demo and social preview

- `demo.gif` (960px, 11 fps, 23 s) and `demo.mp4` (1280x720, H.264): recorded with Playwright
  against the deployed synthetic app on 2026-11-10. The cursor overlay is injected for
  legibility. Flow: Find candidates -> contradictory action -> original JSON -> Match
  Intelligence report.
- `social-preview.png` (1280x640): GitHub social preview card. Upload it in repository
  Settings -> General -> Social preview; the API cannot set it.

Re-record with a Playwright context using `record_video_dir` and `record_video_size`
(1280x720), then encode `demo.mp4` with H.264 and `demo.gif` with a 128-colour palette.
