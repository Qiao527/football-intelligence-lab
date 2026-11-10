"""Public synthetic-only HTTP API. No filesystem input, uploads or source acquisition."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fil.intelligence.demo import MATCHES, load_demo  # noqa: E402
from fil.intelligence.public_score import synthetic_score  # noqa: E402
from fil.intelligence.report_core import analyze  # noqa: E402
from fil.intelligence.scout import search  # noqa: E402
from fil.intelligence.scout_fixture import scout_fixture  # noqa: E402


def route(path: str) -> str:
    """Return the API route, accepting the file-suffixed path a rewrite exposes."""
    return urlparse(path).path.removesuffix(".py")


def response(path):
    parsed = urlparse(path)
    endpoint = route(path)
    if endpoint == "/api/health":
        return 200, {
            "status": "ok",
            "mode": "synthetic-only",
            "commit": os.environ.get("VERCEL_GIT_COMMIT_SHA") or None,
        }
    if endpoint == "/api/matches":
        return 200, [{"id": k, "home": v[0], "away": v[1]} for k, v in MATCHES.items()]
    if endpoint == "/api/scout-fixture" and not parsed.query:
        events, metadata, identity = scout_fixture()
        return 200, {"events": events, "match": metadata, "provenance": identity}
    if endpoint != "/api/analyze":
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
        report = analyze(
            raw, meta, identity, period=period, team=team, score_reconciler=synthetic_score
        )
    except ValueError:
        return 400, {"error": "Invalid selection"}
    return 200, {"report": report, "events": raw, "match": meta}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, body = response(self.path)
        payload = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if route(self.path) != "/api/scout":
            self.send_error(405)
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
            if length < 1 or length > 4096:
                raise ValueError("Invalid request length")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Expected JSON")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or set(body) != {"query"}:
                raise ValueError("Expected query")
            result = search(body["query"])
            status = 200
        except (ValueError, UnicodeDecodeError):
            status, result = 400, {"error": "Invalid scouting request"}
        payload = json.dumps(result, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)
