"""Run the synthetic-only public web application locally; no research-library option."""

import argparse
import runpy
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = runpy.run_path(str(ROOT / "web/api/index.py"))["handler"]


class Local(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/"):
            return API.do_GET(self)
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/scout":
            return API.do_POST(self)
        self.send_error(405)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8650)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Expected port between 1024 and 65535")
    print(f"Fictional-only web application: http://127.0.0.1:{args.port}", flush=True)
    HTTPServer(
        ("127.0.0.1", args.port), partial(Local, directory=str(ROOT / "web/public"))
    ).serve_forever()
