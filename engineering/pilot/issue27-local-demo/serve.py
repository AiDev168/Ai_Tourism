"""Loopback HTTPS static PWA server and same-origin API reverse proxy."""
from __future__ import annotations

from http.client import HTTPConnection
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import ssl
import sys


DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
API_HOST = "127.0.0.1"
API_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8801
WEB_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 443
if not 1024 <= API_PORT <= 65535 or not 1024 <= WEB_PORT <= 65535:
    raise SystemExit("Local demo ports must be in the unprivileged TCP range")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def log_message(self, fmt, *args):
        # Do not log request paths, which may contain identifiers or user data.
        return

    def _send_security(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Cache-Control", "no-store")

    def _proxy(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 2_000_000:
            self.send_error(413)
            return
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in {"host", "connection", "content-length", "forwarded",
                                        "x-forwarded-host", "x-forwarded-proto"}}
        headers.update({"Host": "localhost", "X-Forwarded-Proto": "https", "Connection": "close"})
        connection = HTTPConnection(API_HOST, API_PORT, timeout=90)
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read(2_000_001)
            if len(payload) > 2_000_000:
                self.send_error(502)
                return
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in {"connection", "transfer-encoding", "content-length", "server", "date"}:
                    self.send_header(key, value)
            self._send_security()
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
        except Exception:
            self.send_error(502)
        finally:
            connection.close()

    def do_GET(self):
        if self.path.startswith(("/api/", "/health/")):
            self._proxy()
            return
        path = self.translate_path(self.path)
        if not Path(path).is_file() and not self.path.startswith("/assets/"):
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self): self._proxy()
    def do_PUT(self): self._proxy()
    def do_PATCH(self): self._proxy()
    def do_DELETE(self): self._proxy()
    def do_OPTIONS(self): self._proxy()
    def do_HEAD(self): self._proxy()

    def end_headers(self):
        self._send_security()
        if self.path in {"/", "/index.html", "/sw.js", "/manifest.webmanifest"}:
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        elif self.path.startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        super().end_headers()


if not DIST.is_dir() or not (DIST / "index.html").is_file():
    raise SystemExit("Frontend production build is missing")
root = Path(os.environ["RAHGARD_DEMO_ROOT"])
server = ThreadingHTTPServer(("127.0.0.1", WEB_PORT), Handler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.load_cert_chain(root / "tls" / "localhost.crt", root / "tls" / "localhost.key")
server.socket = context.wrap_socket(server.socket, server_side=True)
server.serve_forever()
