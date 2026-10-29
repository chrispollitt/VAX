#!/usr/bin/env python3
"""Tests for vax-ctl: the idle decision, the /proc and /sys readers, the config, and the SHUTDOWN login against a
fake VMS telnet server.  No root, no VAX, nothing on the network but loopback.

    python3 -m unittest discover -s VAX/simh/ondemand/tests -v
"""
import importlib.machinery
import importlib.util
import os
import re
import socket
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_path = os.path.join(HERE, "..", "vax-ctl")
_loader = importlib.machinery.SourceFileLoader("vax_ctl", _path)
_spec = importlib.util.spec_from_loader("vax_ctl", _loader)
vc = importlib.util.module_from_spec(_spec)
_loader.exec_module(vc)
vc.log = lambda msg: LOG.append(msg)
LOG = []

CFG = dict(vc.DEFAULTS)


def sample(t, cpu_s, net_b, age_s=3600):
    return {"t": t, "cpu_s": cpu_s, "net_b": net_b, "age_s": age_s}


class StepTests(unittest.TestCase):
    def test_grace_period_is_never_idle(self):
        st, info = vc.step({}, sample(100, 1, 1, age_s=60), CFG)
        self.assertTrue(info["busy"])
        self.assertEqual(info["why"], "starting up")
        st, info = vc.step(st, sample(160, 1, 1, age_s=120), CFG)
        self.assertTrue(info["busy"])
        self.assertIsNone(st["idle_since"])

    def test_first_sample_after_grace_cannot_be_judged(self):
        st, info = vc.step({}, sample(100, 5, 5), CFG)
        self.assertTrue(info["busy"])
        self.assertEqual(info["why"], "first sample")

    def test_quiet_minutes_add_up(self):
        st, _ = vc.step({}, sample(0, 10.0, 1000), CFG)
        for k in range(1, 6):
            st, info = vc.step(st, sample(60 * k, 10.0 + 0.2 * k, 1000 + 100 * k), CFG)
            self.assertFalse(info["busy"], info)
        self.assertAlmostEqual(info["idle_min"], 5.0, places=3)

    def test_cpu_use_resets_the_count(self):
        st, _ = vc.step({}, sample(0, 10.0, 1000), CFG)
        st, info = vc.step(st, sample(60, 10.1, 1000), CFG)
        st, info = vc.step(st, sample(120, 10.2, 1000), CFG)
        self.assertGreater(info["idle_min"], 1.9)
        st, info = vc.step(st, sample(180, 40.0, 1000), CFG)          # 50% of a core for a minute
        self.assertTrue(info["busy"])
        self.assertIn("cpu", info["why"])
        self.assertEqual(info["idle_min"], 0.0)
        st, info = vc.step(st, sample(240, 40.1, 1000), CFG)
        self.assertAlmostEqual(info["idle_min"], 1.0, places=3)       # counting again from the last busy sample

    def test_network_traffic_resets_the_count(self):
        st, _ = vc.step({}, sample(0, 10.0, 0), CFG)
        st, info = vc.step(st, sample(60, 10.0, 500000), CFG)
        self.assertTrue(info["busy"])
        self.assertIn("network", info["why"])

    def test_limits_come_from_the_config(self):
        cfg = dict(CFG, CPU_PCT_MAX=60.0)
        st, _ = vc.step({}, sample(0, 10.0, 0), cfg)
        st, info = vc.step(st, sample(60, 40.0, 0), cfg)              # 50%: under the raised limit
        self.assertFalse(info["busy"])


class ConfTests(unittest.TestCase):
    def test_types_and_unknown_keys(self):
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as f:
            f.write("# comment\nIDLE_MINUTES=45\nCPU_PCT_MAX = 1.5\nVMS_HOST=\"10.0.0.9\"\nNOPE=1\n\n")
        try:
            cfg = vc.load_conf(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(cfg["IDLE_MINUTES"], 45)
        self.assertEqual(cfg["CPU_PCT_MAX"], 1.5)
        self.assertEqual(cfg["VMS_HOST"], "10.0.0.9")
        self.assertNotIn("NOPE", cfg)
        self.assertEqual(cfg["UNIT"], "vax.service")                 # untouched default

    def test_missing_file_is_all_defaults(self):
        self.assertEqual(vc.load_conf("/nonexistent/vax-ctl.conf"), vc.DEFAULTS)


class SampleTests(unittest.TestCase):
    def test_reads_proc_and_sys(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(d + "/proc/321")
            os.makedirs(d + "/sys/class/net/vaxtap/statistics")
            hz = os.sysconf("SC_CLK_TCK")
            # field 2 has spaces and a ')' in it: the parser must cope.  utime 200 ticks, stime 100, starttime 1000.
            fields = ["S", "1", "1", "1", "0", "-1", "4194560", "0", "0", "0", "0", "200", "100"] + ["0"] * 6 + ["1000"]
            with open(d + "/proc/321/stat", "w") as f:
                f.write("321 (simh (vax)) " + " ".join(fields) + " 0 0\n")
            with open(d + "/proc/uptime", "w") as f:
                f.write("%f 0.0\n" % (2000.0 / hz + 50.0))
            for n, v in (("rx_bytes", 1000), ("tx_bytes", 234)):
                with open(d + "/sys/class/net/vaxtap/statistics/" + n, "w") as f:
                    f.write("%d\n" % v)
            old = vc.PROC, vc.SYS
            vc.PROC, vc.SYS = d + "/proc", d + "/sys"
            try:
                s = vc.sample(CFG, 321)
            finally:
                vc.PROC, vc.SYS = old
        self.assertAlmostEqual(s["cpu_s"], 300.0 / hz, places=4)
        self.assertEqual(s["net_b"], 1234)
        self.assertAlmostEqual(s["age_s"], 2000.0 / hz + 50.0 - 1000.0 / hz, places=3)


class FakeVMS(threading.Thread):
    """One connection of OpenVMS' telnet service: negotiation noise, Username/Password, a DCL prompt, then the
    SHUTDOWN dialogue.  `prompts` are (text, answer it must get); `ending` is "close" or "hang"."""

    def __init__(self, user, phrase, prompts, ending="close", banner_split=False):
        super().__init__(daemon=True)
        self.user, self.phrase, self.prompts, self.ending = user, phrase, prompts, ending
        self.banner_split = banner_split
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(1)
        self.port = self.srv.getsockname()[1]
        self.got = []
        self.start()

    def readline(self, c):
        data = b""
        while not data.endswith(b"\r\0") and not data.endswith(b"\r\n"):
            chunk = c.recv(1)
            if not chunk:
                return None
            data += chunk
        data = re.sub(rb"\xff[\xfb-\xfe].", b"", data)               # the client's refusals of our IAC DO / WILL
        return data.replace(b"\0", b"").decode().strip()

    def run(self):
        c, _ = self.srv.accept()
        c.settimeout(5)
        try:
            c.sendall(bytes([255, 253, 24, 255, 251, 1]))                 # IAC DO TERMINAL-TYPE, IAC WILL ECHO
            c.sendall(b"\r\n  Welcome to OpenVMS (TM) VAX Operating System, Version V7.3\r\n\r\nUsername: ")
            if self.banner_split:
                c.sendall(bytes([255]))                                   # IAC GA, in two pieces: the second
                time.sleep(0.3)                                           # arrives in a later read and must
                c.sendall(bytes([249]))                                   # not be taken for text
            self.got.append(self.readline(c))
            c.sendall(b"Password: ")
            self.got.append(self.readline(c))
            if self.got[0] != self.user or self.got[1] != self.phrase:
                c.sendall(b"\r\n%LOGIN-F-INVPWD, invalid password\r\n")
                return
            c.sendall(b"\r\n    Last interactive login on Monday, 26-OCT-2026 10:00\r\n$ ")
            self.got.append(self.readline(c))
            for text, want in self.prompts:
                c.sendall(text.encode())
                got = self.readline(c)
                self.got.append(got)
                if got != want:
                    c.sendall(b"\r\n%DCL-W-IVVERB, unrecognized command\r\n")
                    return
            if self.ending == "hang":
                c.recv(1)
                return
            c.sendall(b"\r\nSYSTEM SHUTDOWN COMPLETE - use console to halt system\r\n")
        except (socket.timeout, OSError):
            pass
        finally:
            c.close()
            self.srv.close()


PROMPTS = [
    ("\r\n        SHUTDOWN -- Perform an Orderly System Shutdown\r\n\r\nHow many minutes until final shutdown [0]: ", "2"),
    ("Reason for shutdown [Standalone]: ", "Idle timeout (vax-ctl)"),
    ("Do you want to spin down the disk volumes? [NO]: ", "NO"),
    ("Do you want to invoke the site-specific shutdown procedure? [YES]: ", "YES"),
    ("Should an automatic system reboot be performed? [NO]: ", "NO"),
    ("Shutdown options [NONE]: ", ""),
]
OPENING = [("", "@SYS$SYSTEM:SHUTDOWN")]


def shutdown_against(fake, user="SYSTEM", phrase="x1", **kw):
    del LOG[:]
    return vc.vms_shutdown("127.0.0.1", fake.port, user, phrase, 2, "Idle timeout (vax-ctl)",
                           t_login=3, t_down=3, **kw)


class ShutdownTests(unittest.TestCase):
    def test_full_dialogue(self):
        fake = FakeVMS("SYSTEM", "x1", PROMPTS)
        self.assertTrue(shutdown_against(fake))
        fake.join(5)
        self.assertEqual(fake.got[:3], ["SYSTEM", "x1", "@SYS$SYSTEM:SHUTDOWN"])
        self.assertEqual(fake.got[3:], [w for _, w in PROMPTS])
        self.assertTrue(any("going down" in l or "complete" in l for l in LOG), LOG)

    def test_password_is_never_logged(self):
        fake = FakeVMS("SYSTEM", "tOpS3cr3t", PROMPTS)
        shutdown_against(fake, phrase="tOpS3cr3t")
        self.assertFalse(any("tOpS3cr3t" in l for l in LOG), LOG)

    def test_split_telnet_command_across_reads(self):
        fake = FakeVMS("SYSTEM", "x1", PROMPTS, banner_split=True)
        self.assertTrue(shutdown_against(fake))

    def test_wrong_password_stops_before_any_command(self):
        fake = FakeVMS("SYSTEM", "right", PROMPTS)
        self.assertFalse(shutdown_against(fake, phrase="wrong"))
        fake.join(5)
        self.assertEqual(len(fake.got), 2)                           # never got as far as @SYS$SYSTEM:SHUTDOWN
        self.assertTrue(any("login failed" in l for l in LOG), LOG)

    def test_a_prompt_that_never_comes_leaves_the_vax_alone(self):
        fake = FakeVMS("SYSTEM", "x1", PROMPTS[:2], ending="hang")
        self.assertFalse(shutdown_against(fake))
        self.assertTrue(any("left running" in l for l in LOG), LOG)

    def test_nothing_listening(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        self.assertFalse(vc.vms_shutdown("127.0.0.1", port, "SYSTEM", "x1", 2, "r", t_login=1))


if __name__ == "__main__":
    unittest.main()
