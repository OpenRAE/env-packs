#!/usr/bin/env python3
"""Expose only the GCE identity metadata needed by the model client."""

from __future__ import annotations

import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


_METADATA = "http://169.254.169.254"
_ALLOWED = frozenset(
    {
        "/computeMetadata/v1/",
        "/computeMetadata/v1/instance/service-accounts/default/",
        "/computeMetadata/v1/instance/service-accounts/default/token",
        "/computeMetadata/v1/instance/service-accounts/default/email",
        "/computeMetadata/v1/instance/service-accounts/default/scopes",
        "/computeMetadata/v1/project/project-id",
        "/computeMetadata/v1/project/numeric-project-id",
    }
)


def allowed_path(path: str) -> bool:
    """Accept only exact metadata resources; query expansion is not permitted."""

    return "?" not in path and path in _ALLOWED


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _reply(self, status: int, body: bytes = b"", content_type: str = "text/plain") -> None:
        self.send_response(status)
        self.send_header("Metadata-Flavor", "Google")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.headers.get("Metadata-Flavor") != "Google":
            self._reply(403)
            return
        if not allowed_path(self.path):
            self._reply(404)
            return
        request = urllib.request.Request(
            _METADATA + self.path,
            headers={"Metadata-Flavor": "Google"},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
                body = response.read(65537)
                if len(body) > 65536:
                    raise ValueError
                self._reply(response.status, body, response.headers.get("Content-Type", "text/plain"))
        except Exception:
            self._reply(502)

    def log_message(self, _format: str, *args: object) -> None:
        return


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    ThreadingHTTPServer((sys.argv[1], int(sys.argv[2])), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
