"""Exercise the local synthetic scouting HTTP boundary."""

import json
import runpy
import threading
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path

import pytest

handler = runpy.run_path(str(Path(__file__).resolve().parents[1] / "web/api/index.py"))["handler"]


@pytest.fixture
def server():
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_port
    httpd.shutdown()
    thread.join()
    httpd.server_close()


def request(port, method, path, body=None, headers=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=body, headers=headers or {})
    result = conn.getresponse()
    data = result.read()
    conn.close()
    return result.status, json.loads(data) if data.startswith(b"{") else None


def test_scout_api_uses_only_authored_fixture_and_abstains(server):
    status, fixture = request(server, "GET", "/api/scout-fixture")
    assert status == 200 and fixture["provenance"]["mode"] == "synthetic"
    status, result = request(
        server, "POST", "/api/scout", json.dumps({"query": "Find build-up passes"}),
        {"Content-Type": "application/json"},
    )
    ids = {event["id"] for event in fixture["events"]}
    assert status == 200 and result["source_mode"] == "synthetic"
    assert result["candidates"]
    assert all(set(c["supporting_event_ids"]) <= ids for c in result["candidates"])
    status, result = request(
        server, "POST", "/api/scout", json.dumps({"query": "Invent a player rating"}),
        {"Content-Type": "application/json"},
    )
    assert status == 200 and result["abstention"] and not result["candidates"]


def test_scout_api_rejects_malformed_and_unbounded_input(server):
    for body, headers in (
        ("not json", {"Content-Type": "application/json"}),
        ('{"query": "hello", "extra": true}', {"Content-Type": "application/json"}),
        (json.dumps({"query": "a" * 1001}), {"Content-Type": "application/json"}),
        (json.dumps({"query": "hello"}), {"Content-Type": "text/plain"}),
        (" " * 4097, {"Content-Type": "application/json"}),
    ):
        assert request(server, "POST", "/api/scout", body, headers)[0] == 400
    assert request(server, "POST", "/api/other", "{}")[0] == 405
