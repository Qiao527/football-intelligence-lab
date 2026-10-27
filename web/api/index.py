"""Public synthetic-only HTTP API. No filesystem input, uploads or source acquisition."""

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fil.intelligence.demo import MATCHES, load_demo  # noqa: E402
from fil.intelligence.engine import analyze  # noqa: E402


def response(path):
    parsed = urlparse(path)
    if parsed.path == "/api/health":
        return 200, {"status": "ok", "mode": "synthetic-only"}
    if parsed.path == "/api/matches":
        return 200, [{"id": k, "home": v[0], "away": v[1]} for k, v in MATCHES.items()]
    if parsed.path != "/api/analyze":
        return 404, {"error": "Endpoint not found"}
    q = parse_qs(parsed.query, keep_blank_values=True)
    if set(q) - {"match", "period", "team"} or any(len(v) != 1 for v in q.values()):
        return 400, {"error": "Unsupported or repeated parameter"}
    mid = q.get("match", [""])[0]
    if mid not in MATCHES:
        return 400, {"error": "Choose a supported fictional match"}
    try:
        period = int(q["period"][0]) if q.get("period") else None
        team = int(q["team"][0]) if q.get("team") else None
        raw, meta, identity = load_demo(mid)
        report = analyze(raw, meta, identity, period=period, team=team)
    except ValueError:
        return 400, {"error": "Invalid selection"}
    return 200, {"report": report, "events": raw, "match": meta}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, body = response(self.path)
        payload = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        self.send_error(405)
