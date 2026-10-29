"""Tests for the VAX being on demand: off, still booting, refused logins, sessions the VAX
hung up on, and the HTTP/JSON side of all that.   Run:  python -m unittest discover -s tests -v
"""
import json
import os
import socket
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

import fakevax  # noqa: E402
import waxweb  # noqa: E402
from power import Power, PowerError  # noqa: E402
from vaxterm import VaxUnavailable  # noqa: E402
from waxscrape import WaxSession  # noqa: E402


class FakeSystemd(object):
    """Stands in for subprocess.run: a VAX unit that is on or off, and a start command."""

    def __init__(self, on=False, start_rc=0):
        self.on, self.start_rc, self.calls = on, start_rc, []

    def __call__(self, cmd, **kw):
        self.calls.append(list(cmd))
        r = type("R", (), {})()
        r.stdout = "boom" if self.start_rc else ""
        if "is-active" in cmd:
            r.returncode = 0 if self.on else 3
        else:
            r.returncode = self.start_rc
            if not self.start_rc:
                self.on = True
        return r


class Clock(object):
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def closed_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Tracking(fakevax.Session):
    """fakevax session that remembers its connection so a test can hang up on the client."""
    conns = []

    def setup(self):
        fakevax.Session.setup(self)
        Tracking.conns.append(self.request)


def fake_server(password="pw", cls=fakevax.Session):
    class Opts(object):
        user, delay = "waxweb", 0.0
    Opts.password = password    # allowlist secret: the fake VAX's test login
    srv = fakevax.Server(("127.0.0.1", 0), cls)
    srv.opts = Opts()
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class PowerTests(unittest.TestCase):
    def test_disabled_without_a_unit(self):
        p = Power()
        self.assertFalse(p.enabled)
        self.assertIsNone(p.is_on())
        with self.assertRaises(PowerError):
            p.power_on()

    def test_is_on_and_power_on(self):
        sd = FakeSystemd(on=False)
        p = Power("vax.service", run=sd, cache_secs=0)
        self.assertIs(p.is_on(), False)
        p.power_on()
        self.assertIs(p.is_on(), True)
        self.assertIn(["sudo", "-n", "/usr/bin/systemctl", "start", "vax.service"], sd.calls)

    def test_failed_start_is_reported(self):
        p = Power("vax.service", run=FakeSystemd(start_rc=1), cache_secs=0)
        with self.assertRaises(PowerError) as cm:
            p.power_on()
        self.assertIn("boom", str(cm.exception))

    def test_custom_start_command(self):
        sd = FakeSystemd()
        Power("vax.service", start_cmd="/usr/local/bin/wake vax", run=sd).power_on()
        self.assertEqual(sd.calls[-1], ["/usr/local/bin/wake", "vax"])

    def test_missing_systemctl_means_unknown(self):
        def nope(*a, **k):
            raise FileNotFoundError("systemctl")
        self.assertIsNone(Power("vax.service", run=nope).is_on())


class NotAnswering(unittest.TestCase):
    def session(self, sd):
        power = Power("vax.service", run=sd, cache_secs=0) if sd else None
        return WaxSession("127.0.0.1", closed_port(), "waxweb", "pw", power=power, connect_timeout=1)

    def test_off_fails_at_once_without_connecting(self):
        s = self.session(FakeSystemd(on=False))
        s.term.connect = None                 # would blow up if anything tried to connect
        t0 = time.time()
        with self.assertRaises(VaxUnavailable) as cm:
            s.stats()
        self.assertEqual(cm.exception.state, "off")
        self.assertLess(time.time() - t0, 1)
        self.assertEqual(s.vax_state(), "off")

    def test_on_but_not_answering_is_booting(self):
        s = self.session(FakeSystemd(on=True))
        with self.assertRaises(VaxUnavailable) as cm:
            s.stats()
        self.assertEqual(cm.exception.state, "booting")
        self.assertEqual(s.vax_state(probe=True), "booting")
        self.assertFalse(s.term.connected)

    def test_without_power_control_it_is_unreachable(self):
        s = self.session(None)
        with self.assertRaises(VaxUnavailable) as cm:
            s.stats()
        self.assertEqual(cm.exception.state, "unreachable")

    def test_up_once_telnet_answers_then_it_works(self):
        srv = fake_server()
        try:
            s = WaxSession("127.0.0.1", srv.server_address[1], "waxweb", "pw",
                           power=Power("vax.service", run=FakeSystemd(on=True), cache_secs=0))
            self.assertEqual(s.vax_state(probe=True), "up")
            self.assertEqual(s.vax_state(), "idle")
            self.assertGreaterEqual(len(s.collection()["artists"]), 105)
            self.assertEqual(s.vax_state(), "ready")
            s.close()
        finally:
            srv.shutdown()


class LoginRefused(unittest.TestCase):
    def test_backs_off_then_tries_again(self):
        srv, clock = fake_server(password="right"), Clock()
        try:
            s = WaxSession("127.0.0.1", srv.server_address[1], "waxweb", "wrong", clock=clock)
            with self.assertRaises(VaxUnavailable) as cm:
                s.stats()
            self.assertEqual(cm.exception.state, "login-failed")
            self.assertEqual(s.vax_state(), "login-failed")
            self.assertEqual(s.blocked_for(), 60)
            # inside the pause nothing touches the VAX at all
            s.term.connect = None
            with self.assertRaises(VaxUnavailable) as cm:
                s.stats()
            self.assertIn("not trying again", str(cm.exception))
            del s.term.connect
            # the pause ends; a fixed password gets in and clears the penalty
            clock.t += 61
            s.password = "right"
            self.assertIn("rows", s.stats())
            self.assertEqual((s.blocked_for(), s._login_failures), (0, 0))
            s.close()
        finally:
            srv.shutdown()

    def test_pause_grows_with_each_failure(self):
        srv, clock = fake_server(password="right"), Clock()
        try:
            s = WaxSession("127.0.0.1", srv.server_address[1], "waxweb", "wrong", clock=clock)
            waits = []
            for _ in range(4):
                with self.assertRaises(VaxUnavailable):
                    s.stats()
                waits.append(s.blocked_for())
                clock.t += 1000
            self.assertEqual(waits, [60, 300, 900, 900])
        finally:
            srv.shutdown()


class HungUpOn(unittest.TestCase):
    def test_session_the_vax_closed_is_replaced_quietly(self):
        Tracking.conns = []
        srv = fake_server(cls=Tracking)
        try:
            s = WaxSession("127.0.0.1", srv.server_address[1], "waxweb", "pw")
            s.stats()
            self.assertEqual(s.logins, 1)
            for c in Tracking.conns:           # the VAX shuts down and drops every connection
                c.shutdown(socket.SHUT_RDWR)
            time.sleep(0.2)
            self.assertIn("rows", s.stats())   # no error: it noticed, and logged in again
            self.assertEqual(s.logins, 2)
            s.close()
        finally:
            srv.shutdown()

    def test_idle_session_is_logged_out(self):
        srv, clock = fake_server(), Clock()
        try:
            s = WaxSession("127.0.0.1", srv.server_address[1], "waxweb", "pw", idle_close=600, clock=clock)
            s.stats()
            clock.t += 599
            s.release_if_idle()
            self.assertTrue(s.term.connected)
            clock.t += 2
            s.release_if_idle()
            self.assertFalse(s.term.connected)
            self.assertEqual(s.vax_state(), "idle")
            s.stats()                           # and the next request simply logs in again
            self.assertEqual(s.logins, 2)
            s.close()
        finally:
            srv.shutdown()


class HttpApi(unittest.TestCase):
    """waxweb's JSON API when the VAX is off, booting, and powered on from the page."""

    @classmethod
    def setUpClass(cls):
        cls.systemd = FakeSystemd(on=False)
        power = Power("vax.service", run=cls.systemd, cache_secs=0)
        cls.app = type("App", (), {})()
        cls.app.power = power
        cls.app.session = WaxSession("127.0.0.1", closed_port(), "waxweb", "pw", power=power, connect_timeout=1)
        cls.app.auth, cls.app.started = None, time.time()
        waxweb.APP = cls.app
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), waxweb.Handler)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        waxweb.APP = None

    def call(self, path, body=None):
        req = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

    def test_1_off(self):
        self.systemd.on = False
        code, j = self.call("/api/collection")
        self.assertEqual((code, j["vaxState"], j["canPowerOn"]), (503, "off", True))
        code, h = self.call("/api/health")
        self.assertEqual((code, h["vaxState"], h["canPowerOn"]), (200, "off", True))

    def test_2_power_on_then_booting(self):
        self.systemd.on = False
        code, j = self.call("/api/vax/power-on", {})
        self.assertEqual((code, j["vaxState"]), (200, "booting"))
        self.assertTrue(self.systemd.on)
        code, j = self.call("/api/collection")
        self.assertEqual((code, j["vaxState"]), (503, "booting"))
        code, h = self.call("/api/health?probe=1")
        self.assertEqual(h["vaxState"], "booting")

    def test_3_power_on_when_already_on_does_nothing(self):
        self.systemd.on = True
        n = len(self.systemd.calls)
        code, j = self.call("/api/vax/power-on", {})
        self.assertEqual((code, j["message"]), (200, "already on"))
        self.assertTrue(all("is-active" in c for c in self.systemd.calls[n:]))   # only questions, no start

    def test_4_failed_power_on_is_a_502(self):
        self.systemd.on, self.systemd.start_rc = False, 1
        try:
            code, j = self.call("/api/vax/power-on", {})
        finally:
            self.systemd.start_rc = 0
        self.assertEqual(code, 502)
        self.assertIn("could not start", j["error"])

    def test_5_no_power_control_configured(self):
        old = self.app.power
        self.app.power = Power()
        try:
            code, j = self.call("/api/vax/power-on", {})
        finally:
            self.app.power = old
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()
