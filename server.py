#!/usr/bin/env python3
"""Yuki.exe — NFL Big Data Bowl analytics server.

A zero-dependency web app: standard-library HTTP server exposing a small JSON
API plus a static single-page frontend. Run with:

    python3 server.py

Then open http://127.0.0.1:8000 in a browser.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import analytics
import config

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "YukiExe/1.0"

    # -- helpers ---------------------------------------------------------
    def _send_json(self, payload, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path: str):
        full = os.path.normpath(os.path.join(config.WEB_DIR, path.lstrip("/")))
        if not full.startswith(config.WEB_DIR) or not os.path.isfile(full):
            self._send_json({"error": "not found"}, 404)
            return
        ext = os.path.splitext(full)[1]
        ctype = STATIC_TYPES.get(ext, "application/octet-stream")
        with open(full, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write("[yuki] " + (fmt % args) + "\n")

    # -- routing ---------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        try:
            if path.startswith("/api/"):
                self._route_api(path, qs)
                return
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json({"error": str(exc)}, 500)
            return

        if path == "/" or path == "":
            self._send_static("index.html")
        else:
            self._send_static(path)

    def _route_api(self, path: str, qs: dict):
        if path == "/api/overview":
            self._send_json(analytics.overview())
        elif path == "/api/coverage":
            self._send_json(analytics.coverage_analysis())
        elif path == "/api/pass-rush":
            self._send_json(analytics.pass_rush_leaders())
        elif path == "/api/pass-block":
            self._send_json(analytics.pass_block_leaders())
        elif path == "/api/teams":
            self._send_json(analytics.team_analysis())
        elif path == "/api/games":
            self._send_json(analytics.game_list())
        elif path == "/api/plays":
            game_id = qs.get("gameId", [None])[0]
            self._send_json(analytics.play_list(game_id))
        elif path == "/api/play":
            game_id = qs.get("gameId", [None])[0]
            play_id = qs.get("playId", [None])[0]
            if not game_id or not play_id:
                self._send_json({"error": "gameId and playId required"}, 400)
                return
            self._send_json(analytics.play_detail(game_id, play_id))
        elif path == "/api/player-search":
            q = qs.get("q", [""])[0]
            self._send_json(analytics.player_search(q))
        else:
            self._send_json({"error": "unknown endpoint"}, 404)


def main():
    if not os.path.isdir(config.DATA_DIR):
        sys.stderr.write(
            f"[yuki] WARNING: data directory not found at {config.DATA_DIR}\n"
            f"       Set YUKI_DATA_DIR to point at the Big Data Bowl 'data' folder.\n"
        )
    httpd = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    print(f"Yuki.exe running at http://{config.HOST}:{config.PORT}")
    print(f"Serving data from: {config.DATA_DIR}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
