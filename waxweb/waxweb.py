#!/usr/bin/env python3
"""waxweb -- a web front end for WAX & TAPE that screen-scrapes the VMS program.

    python3 waxweb.py            # configuration comes from environment variables

  VAX_HOST / VAX_PORT   where the VAX's telnet is reachable (default 127.0.0.1:2323,
                        i.e. the end of the ssh tunnel)
  VAX_USER / VAX_PASS   the dedicated VMS account (never logged)
  VAX_WAXDIR            directory holding RUN_WAXR.COM   (default DUA1:[SYSTEM.WAXR])
  WAXWEB_BIND / _PORT   where to serve the web UI        (default 0.0.0.0:8088)
  WAXWEB_AUTH           optional "user:password" for HTTP basic auth
  CACHE_TTL             seconds the roll call is cached  (default 120)
"""
import base64
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from vaxterm import PromptTimeout, TerminalError
from waxscrape import NotFound, WaxError, WaxSession

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
TYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
         ".ico": "image/x-icon", ".json": "application/json", ".txt": "text/plain; charset=utf-8"}


def env(name, default=None):
    return os.environ.get(name, default)


class App(object):
    def __init__(self):
        self.session = WaxSession(
            env("VAX_HOST", "127.0.0.1"), int(env("VAX_PORT", "2323")),
            env("VAX_USER", ""), env("VAX_PASS", ""),
            wax_dir=env("VAX_WAXDIR", "DUA1:[SYSTEM.WAXR]"),
            cache_ttl=int(env("CACHE_TTL", "120")))
        auth = env("WAXWEB_AUTH")
        self.auth = ("Basic " + base64.b64encode(auth.encode()).decode()) if auth else None
        self.started = time.time()


APP = None


class Handler(BaseHTTPRequestHandler):
    server_version = "waxweb/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # -- plumbing --------------------------------------------------------
    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if not isinstance(body, bytes):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def _authorised(self):
        if APP.auth is None or self.headers.get("Authorization") == APP.auth:
            return True
        self._send(401, "authentication required", "text/plain",
                   {"WWW-Authenticate": 'Basic realm="WAX & TAPE"'})
        return False

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        if n > 65536:
            raise WaxError("request too large")
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            raise WaxError("body must be JSON")

    def _guard(self, fn):
        """Run fn() and translate scraper exceptions to HTTP errors."""
        try:
            self._json(200, fn())
        except NotFound as e:
            self._json(404, {"ok": False, "error": str(e)})
        except WaxError as e:
            self._json(400, {"ok": False, "error": str(e)})
        except (TerminalError, PromptTimeout) as e:
            self._json(502, {"ok": False, "error": "the VAX is not answering: %s" % e})
        except Exception:                       # a bug, not a VMS problem
            traceback.print_exc()
            self._json(500, {"ok": False, "error": "internal error"})

    # -- routing --------------------------------------------------------------
    def do_GET(self):
        if not self._authorised():
            return
        url = urlparse(self.path)
        q = parse_qs(url.query)
        s = APP.session
        if url.path == "/api/health":
            return self._json(200, {"ok": True, "connected": s.term.connected, "atMenu": s.at_menu,
                                    "logins": s.logins, "lastError": s.last_error,
                                    "uptime": int(time.time() - APP.started),
                                    "vax": "%s:%s" % (s.host, s.port)})
        if url.path == "/api/collection":
            return self._guard(lambda: s.collection(refresh=q.get("refresh", ["0"])[0] == "1"))
        if url.path == "/api/stats":
            return self._guard(s.stats)
        if url.path == "/api/transcript":
            since = int(q.get("since", ["0"])[0] or 0)
            return self._json(200, {"entries": s.transcript(since)})
        return self._static(url.path)

    def do_POST(self):
        if not self._authorised():
            return
        path = urlparse(self.path).path
        s = APP.session
        try:
            b = self._body()
        except WaxError as e:
            return self._json(400, {"ok": False, "error": str(e)})
        if path == "/api/artist":
            return self._guard(lambda: s.add_artist(b.get("name"), b.get("origin"), b.get("hair")))
        if path == "/api/album":
            return self._guard(lambda: s.add_album(b.get("artist"), b.get("title"), b.get("year"),
                                                   b.get("label"), b.get("genre")))
        if path == "/api/copy":
            return self._guard(lambda: s.add_copy(b.get("artist"), b.get("album"), b.get("media"),
                                                  b.get("grade"), b.get("price"), b.get("year"),
                                                  b.get("notes")))
        if path == "/api/copy/sell":
            return self._guard(lambda: s.remove_copy(b.get("artist"), b.get("album"), b.get("index"),
                                                     b.get("media"), b.get("notes")))
        self._json(404, {"ok": False, "error": "no such endpoint"})

    def _static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        full = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if not full.startswith(STATIC + os.sep) or not os.path.isfile(full):
            return self._send(404, "not found", "text/plain")
        with open(full, "rb") as f:
            data = f.read()
        self._send(200, data, TYPES.get(os.path.splitext(full)[1].lower(), "application/octet-stream"))


def main():
    global APP
    APP = App()
    bind, port = env("WAXWEB_BIND", "0.0.0.0"), int(env("WAXWEB_PORT", "8088"))
    httpd = ThreadingHTTPServer((bind, port), Handler)
    httpd.daemon_threads = True
    print("WAX & TAPE web front end on http://%s:%d  (VAX at %s:%s as %s)"
          % (bind, port, APP.session.host, APP.session.port, APP.session.user or "?"), flush=True)

    def warm():                                  # pre-load the roll call so the first page is quick
        try:
            APP.session.collection()
        except Exception as e:                   # the VAX may be down; the UI will show it
            print("warm-up failed: %s" % e, flush=True)
    threading.Thread(target=warm, daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        APP.session.close()


if __name__ == "__main__":
    main()
