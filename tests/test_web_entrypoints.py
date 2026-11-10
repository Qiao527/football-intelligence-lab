"""Verify the deployable serverless entrypoints and their rewritten routes."""

import importlib.util
import json
import runpy
import threading
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "web" / "api"
ENTRYPOINTS = ("analyze", "health", "matches", "scout", "scout-fixture")


def load_entrypoint(name: str):
    module_name = f"fil_entrypoint_{name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, API / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", ENTRYPOINTS)
def test_entrypoint_exposes_a_discoverable_handler(name):
    module = load_entrypoint(name)
    handler = module.handler
    assert issubclass(handler, BaseHTTPRequestHandler)
    assert callable(handler.do_GET) and callable(handler.do_POST)
    assert handler.__module__ == f"fil_entrypoint_{name.replace('-', '_')}"


@pytest.fixture
def server():
    httpd = HTTPServer(("127.0.0.1", 0), load_entrypoint("scout").handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_port
    httpd.shutdown()
    thread.join()
    httpd.server_close()


def request(port, method, path, body=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Content-Type": "application/json"} if body else {}
    conn.request(method, path, body=body, headers=headers)
    result = conn.getresponse()
    data = result.read()
    conn.close()
    return result.status, json.loads(data) if data.startswith(b"{") else None, data


def test_rewritten_function_paths_serve_the_same_scout_result(server):
    payload = json.dumps({"query": "Find build-up passes"})
    status, rewritten, rewritten_raw = request(server, "POST", "/api/scout.py", payload)
    assert status == 200
    status, direct, direct_raw = request(server, "POST", "/api/scout", payload)
    assert status == 200
    assert rewritten_raw == direct_raw
    assert rewritten["candidates"]

    status, fixture, _ = request(server, "GET", "/api/scout-fixture.py")
    assert status == 200 and fixture["provenance"]["mode"] == "synthetic"
    assert request(server, "POST", "/api/other.py", payload)[0] == 405


def test_health_reports_the_deployment_revision(monkeypatch):
    response = runpy.run_path(str(API / "index.py"))["response"]
    monkeypatch.delenv("VERCEL_GIT_COMMIT_SHA", raising=False)
    assert response("/api/health.py")[1]["commit"] is None
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "0" * 40)
    assert response("/api/health")[1]["commit"] == "0" * 40


def test_vercel_config_builds_and_routes_every_api_entrypoint():
    config = json.loads((ROOT / "web" / "vercel.json").read_text())
    builds = {item["src"] for item in config["builds"]}
    rewrites = {item["source"]: item["destination"] for item in config["rewrites"]}
    assert config["framework"] is None
    assert "package.json" in builds
    for name in ENTRYPOINTS:
        assert f"api/{name}.py" in builds
        assert rewrites[f"/api/{name}"] == f"/api/{name}.py"
