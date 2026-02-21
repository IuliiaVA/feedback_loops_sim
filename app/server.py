"""
Pure-stdlib HTTP server.

Routes:
  GET  /              → serves index.html
  GET  /static/*      → serves JS / CSS
  POST /api/run       → runs simulation, returns JSON
"""

from __future__ import annotations

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

from .simulation import SimParams, run_simulation

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_TEMPLATES = os.path.join(_APP_DIR, "templates")
_STATIC = os.path.join(_APP_DIR, "static")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    """Single-class request handler for all routes."""

    # Suppress per-request log lines in console (comment out to debug)
    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # silent

    # ── GET ───────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self._serve_file(os.path.join(_TEMPLATES, "index.html"), ".html")
        elif self.path.startswith("/static/"):
            filename = self.path[len("/static/"):]
            filepath = os.path.join(_STATIC, filename)
            ext = os.path.splitext(filename)[1]
            self._serve_file(filepath, ext)
        else:
            self._send_error(404, "Not found")

    # ── POST ──────────────────────────────────────────────────────────────

    def do_POST(self) -> None:
        if self.path == "/api/run":
            self._handle_run()
        else:
            self._send_error(404, "Not found")

    # ── Internal helpers ──────────────────────────────────────────────────

    def _handle_run(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body) if body else {}

            params = SimParams(
                n_agents=int(data.get("n_agents", 200)),
                group_imbalance=float(data.get("group_imbalance", 0.5)),
                seed=int(data.get("seed", 42)),
                t_user=float(data.get("t_user", 0.7)),
                a_user=float(data.get("a_user", 0.3)),
                r_user=float(data.get("r_user", 0.2)),
                t_hr=float(data.get("t_hr", 0.6)),
                b_hr=float(data.get("b_hr", 0.15)),
                hiring_threshold=float(data.get("hiring_threshold", 0.45)),
                hiring_capacity=float(data.get("hiring_capacity", 0.3)),
                lr=float(data.get("lr", 0.25)),
                diversity_reg=float(data.get("diversity_reg", 0.1)),
                feedback_weight=float(data.get("feedback_weight", 0.6)),
                iterations=int(data.get("iterations", 20)),
            )

            result = run_simulation(params)
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def _serve_file(self, filepath: str, ext: str) -> None:
        if not os.path.isfile(filepath):
            self._send_error(404, "File not found")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, code: int, obj: Any) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", MIME[".json"])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, code: int, msg: str) -> None:
        body = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Start the HTTP server."""
    server = HTTPServer((host, port), Handler)
    print(f"Server running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
