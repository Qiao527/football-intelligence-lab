# Match Intelligence screenshots

These four PNGs are actual Chromium captures of the running application using FIL's
self-authored fictional fixtures. They contain no real provider records or real player names.
They are not static app content; the application generates reports from actions at runtime.

- `match-intelligence-selection.png`: desktop match-selection entry point.
- `match-intelligence-desktop.png`: rendered charts, scoped observations and evidence controls.
- `match-intelligence-mobile.png`: 390px review cards.
- `match-intelligence-evidence-mobile.png`: original fictional ID and JSON drilldown.

Reproduce with `scripts/check_intelligence_browser.py` against the local app in its default
fictional mode. Explicit screenshots are taken before the script's optional real-data checks.
Provider-derived screenshots remain under ignored `data/` and must not be added here.
