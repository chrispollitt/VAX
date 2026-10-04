#!/usr/bin/env python3
"""Run the web front end against the built-in fake VAX -- no VAX needed.

    python3 run_demo.py [web-port]        # then browse to http://localhost:8088
"""
import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fakevax  # noqa: E402


def main():
    web_port = sys.argv[1] if len(sys.argv) > 1 else "8088"
    opts = type("Opts", (), {"user": "waxweb", "password": "demo", "delay": 0.0})()
    srv = fakevax.Server(("127.0.0.1", 0), fakevax.Session)
    srv.opts = opts
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ.update({"VAX_HOST": "127.0.0.1", "VAX_PORT": str(srv.server_address[1]),
                       "VAX_USER": "waxweb", "VAX_PASS": "demo", "WAXWEB_PORT": web_port,
                       "WAXWEB_BIND": os.environ.get("WAXWEB_BIND", "127.0.0.1")})
    import waxweb
    waxweb.main()


if __name__ == "__main__":
    main()
