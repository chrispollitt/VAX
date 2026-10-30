#!/usr/bin/env python3
"""Tests for vax-ctl: the idle decision, the /proc and /sys readers, the config, and the SHUTDOWN login against a
fake VMS telnet server.  No root, no VAX, nothing on the network but loopback.

    python3 -m unittest discover -s VAX/simh/ondemand/tests -v
"""
import importlib.machinery
import importlib.util
import os
import re
import select
import socket
import tempfile
import threading
import time
import types
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

    def test_typing_at_the_console_resets_the_count(self):
        # the web console window talks to simh over a local socket, never over the tap interface
        def con(t, n, b):
            return dict(sample(t, 10.0, 0), con_n=n, con_in=b)
        st, _ = vc.step({}, con(0, 1, 100), CFG)
        st, info = vc.step(st, con(60, 1, 100), CFG)                  # window open, nobody typing
        self.assertFalse(info["busy"], info)
        st, info = vc.step(st, con(120, 1, 100), CFG)
        self.assertGreater(info["idle_min"], 1.9)
        st, info = vc.step(st, con(180, 1, 136), CFG)                 # four "sho time" lines: 36 keystroke bytes
        self.assertTrue(info["busy"])
        self.assertIn("typing", info["why"])
        self.assertEqual(info["idle_min"], 0.0)

    def test_opening_or_closing_a_console_window_counts_as_activity(self):
        def con(t, n, b):
            return dict(sample(t, 10.0, 0), con_n=n, con_in=b)
        st, _ = vc.step({}, con(0, 0, 0), CFG)
        st, info = vc.step(st, con(60, 1, 0), CFG)
        self.assertTrue(info["busy"])
        self.assertIn("opened or closed", info["why"])
        st, info = vc.step(st, con(120, 1, 0), CFG)
        self.assertFalse(info["busy"])
        st, info = vc.step(st, con(180, 0, 0), CFG)                   # closed again (its counters are gone)
        self.assertTrue(info["busy"])

    def test_samples_without_console_numbers_still_work(self):
        # `ss` missing or failing gives None, and state files from before this signal have no such keys
        st, _ = vc.step({}, dict(sample(0, 10.0, 0), con_n=None, con_in=None), CFG)
        st, info = vc.step(st, dict(sample(60, 10.0, 0), con_n=None, con_in=None), CFG)
        self.assertFalse(info["busy"])
        st, _ = vc.step({}, sample(0, 10.0, 0), CFG)
        st, info = vc.step(st, dict(sample(60, 10.0, 0), con_n=1, con_in=50), CFG)
        self.assertFalse(info["busy"])                                # nothing to compare with yet


class ConsoleSampleTests(unittest.TestCase):
    SS_OUT = ("0      0      [::ffff:127.0.0.1]:2323  [::ffff:127.0.0.1]:56566\n"
              "\t cubic wscale:7,7 rto:204 bytes_sent:10904 bytes_acked:10904 bytes_received:126 segs_out:50\n"
              "0      0      [::ffff:127.0.0.1]:2323  [::ffff:127.0.0.1]:56570\n"
              "\t cubic wscale:7,7 bytes_sent:20 bytes_acked:20 bytes_received:9 segs_out:3\n")

    def test_parse_counts_only_what_simh_received(self):
        self.assertEqual(vc.parse_ss(self.SS_OUT), (2, 135))          # 126 + 9; the 10904 bytes sent are output
        self.assertEqual(vc.parse_ss(""), (0, 0))

    def test_console_sample_runs_ss_for_the_console_port(self):
        with tempfile.TemporaryDirectory() as d:
            fake = os.path.join(d, "ss")
            with open(fake, "w") as f:
                f.write("#!/bin/sh\necho \"$@\" > %s/args\ncat <<'EOF'\n%sEOF\n" % (d, self.SS_OUT))
            os.chmod(fake, 0o755)
            old = vc.SS
            vc.SS = [fake]
            try:
                self.assertEqual(vc.console_sample(CFG), (2, 135))
            finally:
                vc.SS = old
            with open(os.path.join(d, "args")) as f:
                self.assertIn("sport = :%d" % CFG["CONSOLE_PORT"], f.read())

    def test_console_sample_is_none_when_ss_is_missing_or_fails(self):
        old = vc.SS
        try:
            vc.SS = ["/nonexistent/ss"]
            self.assertEqual(vc.console_sample(CFG), (None, None))
            vc.SS = ["false"]
            self.assertEqual(vc.console_sample(CFG), (None, None))
        finally:
            vc.SS = old


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

    def __init__(self, user, phrase, prompts, ending="close", banner_split=False, after_login=None,
                 banner=None, prompt=b"$ ", answer_marker=True, swallow_markers=0, drop_after=None, finale=None):
        super().__init__(daemon=True)
        self.user, self.phrase, self.prompts, self.ending = user, phrase, prompts, ending
        self.banner_split = banner_split
        self.after_login = after_login          # bytes sent instead of the login banner and prompt, then silence
        self.banner = banner                    # what the login procedure prints (default: one "Last login" line)
        self.prompt = prompt                    # the DCL prompt: cpvax's is "CPVAX$DUA1:[SYSTEM]", not "$ "
        self.answer_marker = answer_marker      # False: echo the marker command but never print its answer
        self.swallow_markers = swallow_markers  # the first N marker commands vanish, as in cpvax's SET TERMINAL/INQUIRE
        self.swallowed = 0
        self.drop_after = drop_after            # the session dies after this many SHUTDOWN questions were answered
        self.finale = finale                    # what VMS prints after the last question (default: SHUTDOWN COMPLETE)
        self.early_answers = 0                  # answers that came before the question line was complete
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
            if self.after_login is not None:
                c.sendall(self.after_login)
                while c.recv(1):                                          # then say nothing until the client leaves
                    pass
                return
            banner = self.banner
            if banner is None:
                banner = b"\r\n    Last interactive login on Monday, 26-OCT-2026 10:00\r\n"
            c.sendall(banner + self.prompt)
            while True:
                marker_cmd = self.readline(c)                             # the client's "am I logged in?" command
                self.got.append(marker_cmd)
                if marker_cmd is None or not marker_cmd.startswith("WRITE SYS$OUTPUT"):
                    c.sendall(b"\r\n%DCL-W-IVVERB, unrecognized command\r\n")
                    return
                if self.swallowed < self.swallow_markers:
                    self.swallowed += 1                                   # eaten by the login procedure: no echo, no answer
                    continue
                break
            c.sendall(marker_cmd.encode() + b"\r\n")                      # the terminal echoes what was typed
            if not self.answer_marker:
                while c.recv(1):
                    pass
                return
            c.sendall(b"VAXCTL-OK\r\n" + self.prompt)
            self.got.append(self.readline(c))                             # @SYS$SYSTEM:SHUTDOWN
            for k, (text, want) in enumerate(self.prompts):
                for n, part in enumerate(text.split("\x00")):             # "\x00" marks where the line arrives in pieces
                    if n:
                        ready, _, _ = select.select([c], [], [], 0.15)
                        if ready:
                            self.early_answers += 1                       # the client answered before the line was complete
                    c.sendall(part.encode())
                got = self.readline(c)
                self.got.append(got)
                if got != want:
                    c.sendall(b"\r\n%DCL-W-IVVERB, unrecognized command\r\n")
                    return
                if self.drop_after is not None and k + 1 >= self.drop_after:
                    return                                                # the session dies in the middle of the dialogue
            if self.finale is not None:
                c.sendall(self.finale)
            if self.ending == "hang":                                     # VMS halts, simh exits: no goodbye, no close
                while c.recv(1):
                    pass
                return
            if self.finale is None:
                c.sendall(b"\r\nSYSTEM SHUTDOWN COMPLETE - use console to halt system\r\n")
        except (socket.timeout, OSError):
            pass
        finally:
            c.close()
            self.srv.close()


PROMPTS = [
    # as cpvax printed them on 2026-10-29 (OpenVMS VAX V7.3): this question comes first, and its default is NO
    ("\r\nCPVAX$DUA1:[SYSTEM]\r\n\r\n\r\n        SHUTDOWN -- Perform an Orderly System Shutdown\r\n"
     # (the question arrives in two pieces, and the next one is wrapped at 80 columns in the middle of a word, as on cpvax)
     "                    on node CPVAX\r\n\rDo you really want to shutdown\x00 node CPVAX [NO]? ", "YES"),
    (" How many minutes until final shu\r\ntdown [0]: ", "2"),
    ("Reason for shutdown [Standalone]: ", "Idle timeout (vax-ctl)"),
    ("Do you want to spin down the disk volumes? [NO]: ", "NO"),
    ("Do you want to invoke the site-specific shutdown procedure? [YES]: ", "YES"),
    ("Should an automatic system reboot be performed? [NO]: ", "NO"),
    ("When will the system be rebo\r\noted [later]: ", ""),       # asked even after NO; wrapped as on cpvax
    ("Shutdown options [NONE]: ", ""),
]
OPENING = [("", "@SYS$SYSTEM:SHUTDOWN")]


def shutdown_against(fake, user="SYSTEM", phrase="x1", **kw):
    del LOG[:]
    kw.setdefault("t_quiet", 0.3)                    # the real wait for VMS to go quiet is 4 s
    kw.setdefault("t_progress", 0.5)                 # and the real progress line is every 30 s
    kw.setdefault("t_settle", 0.3)                   # and the real wait for a question to be complete is 1 s
    kw.setdefault("t_poll", 0.2)                     # and the real check that the simulator is still running is every 2 s
    kw.setdefault("command", "@SYS$SYSTEM:SHUTDOWN")  # the long dialogue, which most tests exercise (the default is SHUTDOWN)
    return vc.vms_shutdown("127.0.0.1", fake.port, user, phrase, 2, "Idle timeout (vax-ctl)",
                           t_login=3, t_down=3, **kw)


class ShutdownTests(unittest.TestCase):
    def test_full_dialogue(self):
        fake = FakeVMS("SYSTEM", "x1", PROMPTS)
        self.assertTrue(shutdown_against(fake))
        fake.join(5)
        self.assertEqual(fake.got[:4], ["SYSTEM", "x1", vc.MARKER_COMMAND, "@SYS$SYSTEM:SHUTDOWN"])
        self.assertEqual(fake.got[4:], [w for _, w in PROMPTS])
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

    def test_the_real_cpvax_login_with_no_dollar_prompt(self):
        # What cpvax really sent on 2026-10-29 after the password: the login procedure's terminal queries (nobody
        # answers them), SET warnings, window-title escapes, "Ready!", and the DCL prompt CPVAX$DUA1:[SYSTEM] with no
        # "$ ".  The first real shutdown waited for "$ " and timed out; this must now go through.
        banner = (b" \r\n Welcome to OpenVMS (TM) VAX Operating System, Version V7.3\r\n"
                  b"    Last interactive login on Thursday, 29-OCT-2026 18:29\r\n"
                  b"    Last non-interactive login on Wednesday, 28-OCT-2026 23:47\r"
                  b"\x1b[c\x1b\\\x1bZ\x1b[0c\r\n%SET-W-NOTSET, error modifying NTA1:\r\n-SET-I-UNKTERM, unknown terminal type\r"
                  b"\x1b[c\x1b\\\x1bZ\x1b[0c\r\n%SET-W-NOTSET, error modifying NTA1:\r\n-SET-I-UNKTERM, unknown terminal type\r\n"
                  b"\x1b]0;SYSTEM@CPVAX[NTA1]\x07\r\n\x1b]1;SYSTEM@CPVAX[NTA1]\x07\r\nReady!\r\n")
        fake = FakeVMS("SYSTEM", "x1", PROMPTS, banner=banner, prompt=b"CPVAX$DUA1:[SYSTEM]")
        self.assertTrue(shutdown_against(fake))
        fake.join(5)
        self.assertEqual(fake.got[2:4], [vc.MARKER_COMMAND, "@SYS$SYSTEM:SHUTDOWN"])
        self.assertTrue(any("logged in" in l for l in LOG), LOG)

    def test_the_answer_waits_for_the_end_of_the_question(self):
        # cpvax, 2026-10-29: the reply "YES" was sent as soon as "Do you really want to shutdown" had arrived, before
        # " node CPVAX [NO]? ".  The fake sends that question in two pieces and notes an answer that comes between.
        fake = FakeVMS("SYSTEM", "x1", PROMPTS)
        self.assertTrue(shutdown_against(fake))
        fake.join(5)
        self.assertEqual(fake.early_answers, 0)

    def test_a_question_wrapped_in_the_middle_of_a_word_is_matched(self):
        self.assertTrue(re.search(vc.loose("how many minutes until final shutdown"),
                                  "How many minutes until final shu\r\ntdown [0]: ", re.I))
        self.assertTrue(re.search(vc.loose("shutdown complete"), "SYSTEM SHUTDOWN\r\n COMPLETE", re.I))
        self.assertFalse(re.search(vc.loose("final shutdown"), "final startup", re.I))

    def test_the_simulator_stopping_after_the_shutdown_messages_is_the_end(self):
        # 2026-10-29, the first good shutdown: VMS halted, simh exited, and the telnet connection did not close: it
        # just vanished.  vax-ctl waited the full 7 minutes for a close, and would have reported a failure.
        stopped_at = time.time() + 0.8
        fake = FakeVMS("SYSTEM", "x1", PROMPTS[:1], ending="hang",
                       finale=(b"\r\n%SHUTDOWN-I-OPERATOR, this terminal is now an operator's console\r\n"
                               b"%SHUTDOWN-I-DISLOGINS, interactive logins will now be disabled\r\n"))
        self.assertTrue(shutdown_against(fake, command="SHUTDOWN", halted=lambda: time.time() >= stopped_at))
        self.assertTrue(any("VMS has halted" in l for l in LOG), LOG)

    def test_the_simulator_stopping_before_the_shutdown_started_is_not_a_success(self):
        stopped_at = time.time() + 0.8
        fake = FakeVMS("SYSTEM", "x1", PROMPTS[:1], ending="hang", finale=b"\r\nNothing about a shutdown here.\r\n")
        self.assertFalse(shutdown_against(fake, command="SHUTDOWN", halted=lambda: time.time() >= stopped_at))
        self.assertTrue(any("not counting it as one" in l for l in LOG), LOG)

    def test_a_running_simulator_that_says_nothing_still_times_out(self):
        fake = FakeVMS("SYSTEM", "x1", PROMPTS[:1], ending="hang",
                       finale=b"\r\n%SHUTDOWN-I-OPERATOR, this terminal is now an operator's console\r\n")
        self.assertFalse(shutdown_against(fake, command="SHUTDOWN", halted=lambda: False))
        self.assertTrue(any("left running" in l for l in LOG), LOG)

    def test_cpvaxs_own_shutdown_command_asks_one_question(self):
        # what Chris typed by hand on 2026-10-29: SHUTDOWN, one question, YES, then %SHUTDOWN-I- lines and the end
        fake = FakeVMS("SYSTEM", "x1", PROMPTS[:1],
                       finale=(b"\r\n%SHUTDOWN-I-OPERATOR, this terminal is now an operator's console\r\n"
                               b"%SHUTDOWN-I-DISLOGINS, interactive logins will now be disabled\r\n"))
        self.assertTrue(shutdown_against(fake, command="SHUTDOWN"))
        fake.join(5)
        self.assertEqual(fake.got[2:5], [vc.MARKER_COMMAND, "SHUTDOWN", "YES"])

    def test_the_command_is_configurable(self):
        self.assertEqual(vc.DEFAULTS["SHUTDOWN_COMMAND"], "SHUTDOWN")
        fake = FakeVMS("SYSTEM", "x1", PROMPTS)
        self.assertTrue(shutdown_against(fake, command="@SYS$SYSTEM:SHUTDOWN"))
        fake.join(5)
        self.assertEqual(fake.got[3], "@SYS$SYSTEM:SHUTDOWN")

    def test_a_question_nobody_listed_is_answered_with_its_default(self):
        # cpvax asked "When will the system be rebooted [later]:" after a NO; the next version of VMS may ask more
        extra = ("Flush the widgets before the shutdown? [YES]: ", "")
        fake = FakeVMS("SYSTEM", "x1", PROMPTS[:-1] + [extra] + PROMPTS[-1:])
        self.assertTrue(shutdown_against(fake))
        fake.join(5)
        self.assertEqual(fake.got[4:], [w for _, w in PROMPTS[:-1]] + [""] + [""])
        self.assertTrue(any("not a question this program knows" in l for l in LOG), LOG)

    def test_runaway_unknown_questions_stop_it(self):
        many = [("Question number %d? [X]: " % k, "") for k in range(vc.MAX_UNKNOWN + 3)]
        fake = FakeVMS("SYSTEM", "x1", PROMPTS[:1] + many)
        self.assertFalse(shutdown_against(fake))
        self.assertTrue(any("questions this program does not know" in l for l in LOG), LOG)

    def test_the_shutdown_messages_show_it_has_started_even_without_a_complete_line(self):
        # after the last answer cpvax prints %SHUTDOWN-I-... lines and then the session goes away: that is a shutdown,
        # but a session that dies in the middle of the questions (below) is not
        fake = FakeVMS("SYSTEM", "x1", PROMPTS[:2], finale=(b"\r\n%SHUTDOWN-I-OPERATOR, this terminal is now an "
                                                          b"operator's console\r\n%SHUTDOWN-I-DISLOGINS, interactive "
                                                          b"logins will now be disabled\r\n"))
        self.assertTrue(shutdown_against(fake))
        self.assertTrue(any("has started the shutdown" in l for l in LOG), LOG)

    def test_a_session_that_dies_mid_dialogue_is_not_a_shutdown(self):
        # a closed connection means "VMS is going down" only after the LAST question was answered
        fake = FakeVMS("SYSTEM", "x1", PROMPTS, drop_after=2)
        self.assertFalse(shutdown_against(fake))
        self.assertTrue(any("before the SHUTDOWN questions were all answered" in l for l in LOG), LOG)

    def test_a_stall_after_the_shutdown_command_is_reported_while_it_happens(self):
        # 2026-10-29: after "@SYS$SYSTEM:SHUTDOWN" nothing matched and the log said nothing for 7 minutes.  Now every
        # t_progress seconds it says what has arrived, so the question VMS really asked can be seen at once.
        odd = [("\r\nSomething unexpected: the system wants to know your favourite colour? ", "blue")]
        fake = FakeVMS("SYSTEM", "x1", odd, ending="hang")
        self.assertFalse(shutdown_against(fake))
        progress = [l for l in LOG if "still waiting for a SHUTDOWN question" in l]
        self.assertTrue(progress, LOG)
        self.assertIn("favourite colour", progress[0])
        self.assertTrue(any("matched nothing" in l for l in LOG), LOG)

    def test_a_marker_command_swallowed_by_the_login_procedure_is_sent_again(self):
        # cpvax, 2026-10-29: VMS went quiet while SET TERMINAL/INQUIRE waited for a reply, the first marker command
        # was taken as that reply, and nothing came back: not even an echo.  Asking again must get through.
        fake = FakeVMS("SYSTEM", "x1", PROMPTS, swallow_markers=2, prompt=b"CPVAX$DUA1:[SYSTEM]")
        self.assertTrue(shutdown_against(fake))
        fake.join(5)
        self.assertEqual(fake.got[2:5], [vc.MARKER_COMMAND] * 3)           # two swallowed, the third answered
        self.assertEqual(fake.got[5], "@SYS$SYSTEM:SHUTDOWN")
        self.assertTrue(any("no answer to the marker command yet" in l for l in LOG), LOG)
        self.assertTrue(any("try 3" in l for l in LOG), LOG)

    def test_a_marker_command_that_is_never_answered_gives_up_and_says_what_arrived(self):
        fake = FakeVMS("SYSTEM", "x1", PROMPTS, swallow_markers=99)
        self.assertFalse(shutdown_against(fake))
        fake.join(5)
        self.assertEqual(fake.got[2:].count(vc.MARKER_COMMAND), vc.MARKER_TRIES)   # tried, and stopped
        self.assertTrue(any("left running" in l for l in LOG), LOG)
        self.assertTrue(any("matched nothing" in l for l in LOG), LOG)

    def test_the_echo_of_the_marker_command_is_not_a_login(self):
        # the terminal echoes what is typed, so the marker must not appear in its own echo
        fake = FakeVMS("SYSTEM", "x1", PROMPTS, answer_marker=False)
        self.assertFalse(shutdown_against(fake))
        self.assertTrue(any("left running" in l for l in LOG), LOG)
        self.assertFalse(any("logged in" in l for l in LOG), LOG)

    def test_the_connection_closing_before_the_marker_answer_is_not_success(self):
        class Closer(FakeVMS):
            def run(self):
                c, _ = self.srv.accept()
                c.settimeout(5)
                try:
                    c.sendall(b"\r\nUsername: ")
                    self.readline(c)
                    c.sendall(b"Password: ")
                    self.readline(c)
                    c.sendall(b"\r\nReady!\r\nCPVAX$DUA1:[SYSTEM]")
                    self.readline(c)                                      # the marker command, then hang up
                finally:
                    c.close()
                    self.srv.close()
        fake = Closer("SYSTEM", "x1", PROMPTS)
        self.assertFalse(shutdown_against(fake))
        self.assertTrue(any("before it answered the marker" in l for l in LOG), LOG)

    def test_a_login_that_never_reaches_a_prompt_shows_what_vms_sent(self):
        # the real failure of 2026-10-29: after the password VMS sent neither "$ " nor a login failure, and the log
        # said only "no match for [...]".  Now it shows what did arrive, escapes visible, and blanks the password.
        word = "zq7secret"
        fake = FakeVMS("SYSTEM", word, PROMPTS,
                       after_login=("\r\n\x1b[?25h Echoed: %s\r\nYour password has expired; you must set a new one."
                                    "\r\nNew password: " % word).encode())
        self.assertFalse(shutdown_against(fake, phrase=word))
        text = "\n".join(LOG)
        self.assertIn("matched nothing", text)
        self.assertIn("must set a new one", text)             # the question VMS asked is there to read
        self.assertIn("\\x1b", text)                           # escape characters are shown, not interpreted
        self.assertIn("<password>", text)                      # the echoed password is blanked
        self.assertNotIn(word, text)
        self.assertTrue(any("left running" in l for l in LOG), LOG)

    def test_nothing_listening(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        self.assertFalse(vc.vms_shutdown("127.0.0.1", port, "SYSTEM", "x1", 2, "r", t_login=1))


# ---------------------------------------------------------------- boot-watch
#
# What is real here: the console texts below were captured from throwaway simh instances on cpbee (same ROM, buffered
# console, nobody attached), a passing self-test and a failing one (`?53 2 0A FF 00 0000`).  What is not: the failure
# cannot be forced, so everything else here (the console, the clock, systemctl, the unit's pid) is a fake, and these
# tests show the decisions and the counting, not that a real `systemctl restart vax.service` brings the VAX back.

SIMH_HELLO = bytes([255, 251, 34, 255, 251, 3, 255, 251, 1, 255, 251, 0, 255, 253, 0])      # IAC WILL/DO ..., as simh sends
BANNER = ("\n\r\nConnected to the MicroVAX 3900 simulator CON-TELNET device\r\n\n\r\n\x1b[c\r\n\rKA655-B V5.3, VMB 2.7\r\n"
          "Performing normal system tests.\r\n")
COUNT_1 = "40..39..38..37..36..35..34..33..32..31..\r\n"
PASS_REST = ("30..29..28..27..26..25..\r\n24..23..22..21..20..19..18..17..16..15..14..13..12..11..10..09..\r\n"
             "08..07..06..05..04..03..\r\nTests completed.\r\nLoading system software.\r\n(BOOT/R5:0 DUA0\r\n\r\n\r\n\n  2..\r\n"
             "?4D DEVOFFLINE, DUA0\r\n?06 HLT INST\r\n        PC = 00000C1A\r\nFailure.\r\n>>>")
FAIL_REST = ("\r\n?53 2 0A FF 00 0000\r\n\r\nP1=00000002  P2=00000028  P3=0000270E  P4=00D40077  P5=00000001\r\n"
             "P6=FFFFFFFF  P7=00000000  P8=00000000  P9=20051BD0 P10=20051CE0\r\n"
             "r0=00000004  r1=20140110  r2=AAFDCD91  r3=000300C8  r4=AAFDCD9B\r\n"
             "r5=2004E8F9  r6=00018678  r7=000186C8  r8=0001ADAE ERF=82000180\r\n"
             "30..29..28..27..26..25..\r\n24..23..22..21..20..19..18..17..16..15..14..13..12..11..10..09..\r\n"
             "08..07..06..05..04..03..\r\nNormal operation not possible.\r\n\r\n>>>")
PASSING = [(0, (BANNER + COUNT_1 + PASS_REST).encode("latin-1"))]
FAILING = [(0, (BANNER + COUNT_1 + FAIL_REST).encode("latin-1"))]
# the same, but the first read ends mid-test and the verdict comes 1.2 s later on the same connection
SLOW_PASSING = [(0, (BANNER + COUNT_1).encode("latin-1")), (1.2, PASS_REST.encode("latin-1"))]
SLOW_FAILING = [(0, (BANNER + COUNT_1).encode("latin-1")), (1.2, FAIL_REST.encode("latin-1"))]
STALLED = [(0, (BANNER + COUNT_1).encode("latin-1"))]


class FakeConsole(threading.Thread):
    """The simh console on a telnet port with a buffered console: the first client gets the scripted text, (delay in
    seconds, bytes) pieces, and its connection stays open.  A later client gets the same text again if `replay` (what a
    simh built like cpbee's does, measured), and nothing if not (what the README once said it does)."""

    def __init__(self, script, replay=False):
        super().__init__(daemon=True)
        self.script = script
        self.replay = replay
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(5)
        self.srv.settimeout(0.1)
        self.port = self.srv.getsockname()[1]
        self.connections = 0
        self.received = b""
        self.closing = False
        self.start()

    def run(self):
        while not self.closing:
            try:
                c, _ = self.srv.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.connections += 1
            script = self.script if self.connections == 1 else [(0, d) for _, d in self.script] if self.replay else []
            threading.Thread(target=self.serve, args=(c, script, self.connections == 1), daemon=True).start()

    def serve(self, c, script, first):
        c.settimeout(0.1)
        try:
            c.sendall(SIMH_HELLO)
            for delay, data in script:
                end = time.time() + delay
                while time.time() < end and not self.closing:
                    time.sleep(0.02)
                c.sendall(data)
            while not self.closing:
                try:
                    chunk = c.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                if first:
                    self.received += chunk
        except OSError:
            pass
        finally:
            c.close()

    def close(self):
        self.closing = True
        self.srv.close()


class BootWatchTests(unittest.TestCase):
    TM = {"first_age": 0.2, "quiet": 0.4, "read_limit": 3.0, "again": 0.5, "give_up_age": 2.5, "restart_window": 300.0}
    PATCHED = ("BOOT_LOG", "BOOT_STATE", "unit_active", "main_pid", "proc_age", "systemctl")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = {n: getattr(vc, n) for n in self.PATCHED}
        self.t0, self.age_offset, self.pid, self.restart_rc = time.time(), 0.0, 4242, 0
        self.calls, self.consoles = [], []
        vc.BOOT_LOG = self.tmp.name + "/run/console-boot.txt"
        vc.BOOT_STATE = self.tmp.name + "/lib/boot.json"
        vc.unit_active = lambda cfg: True
        vc.main_pid = lambda cfg: self.pid
        vc.proc_age = lambda pid: time.time() - self.t0 + self.age_offset       # the "VAX" was started at setUp
        vc.systemctl = self.fake_systemctl
        del LOG[:]

    def tearDown(self):
        for n, v in self.saved.items():
            setattr(vc, n, v)
        for c in self.consoles:
            c.close()
        self.tmp.cleanup()

    def fake_systemctl(self, *args):
        self.calls.append(args)
        return types.SimpleNamespace(returncode=self.restart_rc, stdout="", stderr="Failed to restart: fake")

    def console(self, script, replay=False):
        c = FakeConsole(script, replay)
        self.consoles.append(c)
        return c

    def watch(self, console, retries=3, boot=None, **tm):
        if boot is not None:
            vc.save_state(boot, vc.BOOT_STATE)
        cfg = dict(CFG, CONSOLE_HOST="127.0.0.1", CONSOLE_PORT=console.port, BOOT_RETRIES=retries)
        return vc.cmd_boot_watch(cfg, None, dict(self.TM, **tm))

    def state(self):
        return vc.load_state(vc.BOOT_STATE)

    def boot_text(self):
        with open(vc.BOOT_LOG, encoding="latin-1", newline="") as f:
            return f.read()

    RESTART = [("--no-block", "restart", "vax.service")]

    # --- the verdict on the text

    def test_verdict_of_the_real_self_tests(self):
        self.assertEqual(vc.boot_verdict(BANNER + COUNT_1 + PASS_REST), "passed")
        self.assertEqual(vc.boot_verdict(BANNER + COUNT_1 + FAIL_REST), "failed")

    def test_no_verdict_before_the_end_of_the_test(self):
        self.assertIsNone(vc.boot_verdict(""))
        self.assertIsNone(vc.boot_verdict(BANNER + COUNT_1))

    def test_a_pass_wins_over_a_failure_text(self):
        self.assertEqual(vc.boot_verdict(FAIL_REST + "Tests completed."), "passed")

    # --- passing

    def test_passed_selftest_is_not_restarted(self):
        con = self.console(PASSING)
        self.assertEqual(self.watch(con), 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.state()["result"], "passed")
        self.assertTrue(any("passed" in l for l in LOG), LOG)

    def test_success_resets_the_counter(self):
        con = self.console(PASSING)
        self.watch(con, boot={"restarts": 2, "restarted_at": time.time()})
        self.assertEqual(self.state()["restarts"], 0)
        self.assertEqual(self.calls, [])

    def test_slow_pass_is_read_on_the_same_connection_and_not_restarted(self):
        con = self.console(SLOW_PASSING)
        self.assertEqual(self.watch(con), 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(con.connections, 2)                              # the reads share one; the second asks about replay
        self.assertEqual(self.state()["result"], "passed")
        self.assertGreater(time.time() - self.t0, 1.2)                    # it did wait for the second read

    # --- failing

    def test_failed_selftest_restarts_the_unit_once_and_counts_it(self):
        con = self.console(FAILING)
        self.assertEqual(self.watch(con), 0)
        self.assertEqual(self.calls, self.RESTART)
        st = self.state()
        self.assertEqual((st["restarts"], st["result"]), (1, "failed"))
        self.assertTrue(any("restarting vax.service" in l and "1 of 3" in l for l in LOG), LOG)

    def test_slow_failure_is_found_on_the_second_read(self):
        con = self.console(SLOW_FAILING)
        self.assertEqual(self.watch(con), 0)
        self.assertEqual(self.calls, self.RESTART)
        self.assertEqual(con.connections, 1)

    def test_counts_up_to_the_limit_then_gives_up_and_leaves_the_vax_alone(self):
        for k in range(1, 4):                                             # BOOT_RETRIES=3: three restarts
            self.t0 = time.time()
            self.assertEqual(self.watch(self.console(FAILING)), 0, k)
            self.assertEqual(self.state()["restarts"], k)
        self.assertEqual(len(self.calls), 3)
        self.t0 = time.time()
        self.assertEqual(self.watch(self.console(FAILING)), 3)            # the fourth failure
        self.assertEqual(len(self.calls), 3)                              # no fourth restart
        self.assertTrue(any("Giving up" in l and ">>>" in l for l in LOG), LOG)
        self.assertEqual(self.state()["result"], "gave up")

    def test_a_new_power_on_after_giving_up_gets_a_new_count(self):
        self.watch(self.console(FAILING), boot={"restarts": 3, "restarted_at": time.time()})      # at the limit
        self.assertEqual(self.calls, [])
        self.t0 = time.time()
        self.assertEqual(self.watch(self.console(FAILING)), 0)             # given-up state is not "recent"
        self.assertEqual(self.calls, self.RESTART)
        self.assertEqual(self.state()["restarts"], 1)

    def test_an_old_count_is_not_ours_any_more(self):
        self.watch(self.console(FAILING), boot={"restarts": 3, "restarted_at": time.time() - 1000})
        self.assertEqual(self.calls, self.RESTART)
        self.assertEqual(self.state()["restarts"], 1)

    def test_the_limit_comes_from_the_setting(self):
        self.watch(self.console(FAILING), retries=0)
        self.assertEqual(self.calls, [])
        self.watch(self.console(FAILING), retries=1, boot={"restarts": 0})
        self.assertEqual(self.calls, self.RESTART)

    def test_a_restart_that_systemctl_refuses_is_reported(self):
        self.restart_rc = 1
        self.assertEqual(self.watch(self.console(FAILING)), 1)
        self.assertTrue(any("failed" in l and "fake" in l for l in LOG), LOG)

    def test_not_restarted_if_the_unit_changed_under_it(self):
        con = self.console(FAILING)
        threading.Timer(0.45, lambda: setattr(self, "pid", 9999)).start()   # after the first_age wait, before the verdict
        self.assertEqual(self.watch(con), 0)
        self.assertEqual(self.calls, [])

    # --- no verdict, no action

    def test_stalled_selftest_gets_no_verdict_and_no_restart(self):
        con = self.console(STALLED)
        self.assertEqual(self.watch(con), 2)
        self.assertEqual(self.calls, [])
        self.assertGreaterEqual(time.time() - self.t0, 2.5)               # waited up to the give-up age
        self.assertTrue(any("no verdict" in l for l in LOG), LOG)

    def test_console_that_cannot_be_reached_gets_no_verdict_and_no_restart(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        cfg = dict(CFG, CONSOLE_PORT=port)
        self.assertEqual(vc.cmd_boot_watch(cfg, None, dict(self.TM, give_up_age=1.5)), 2)
        self.assertEqual(self.calls, [])

    def test_a_vax_that_is_already_up_is_not_touched(self):
        con = self.console(FAILING)
        self.age_offset = 500.0
        self.assertEqual(self.watch(con), 0)
        self.assertEqual((self.calls, con.connections), ([], 0))          # not even connected: no console stolen

    def test_unit_not_running(self):
        vc.unit_active = lambda cfg: False
        con = self.console(FAILING)
        self.assertEqual(self.watch(con), 0)
        self.assertEqual((self.calls, con.connections), ([], 0))

    # --- the console text

    def test_what_was_read_is_kept_for_the_console_window(self):
        os.makedirs(os.path.dirname(vc.BOOT_LOG))
        with open(vc.BOOT_LOG, "w") as f:
            f.write("left over from the last boot\r\n")
        self.watch(self.console(FAILING))
        text = self.boot_text()
        self.assertNotIn("left over", text)                               # truncated at the start of the cycle
        self.assertIn("Performing normal system tests.", text)
        self.assertIn("?53 2 0A FF 00 0000", text)
        self.assertTrue(text.endswith(">>>"))
        self.assertNotIn("\x1b[c", text)                                  # the terminal-identify query is left out
        self.assertNotIn("\xff", text)                                    # and no telnet commands
        self.assertEqual(os.stat(vc.BOOT_LOG).st_mode & 0o777, 0o644)     # readable by the web terminal's user

    def test_the_copy_is_kept_while_the_vax_is_restarted(self):
        con = self.console(FAILING, replay=True)
        self.watch(con)
        self.assertIn("Normal operation not possible", self.boot_text())
        self.assertEqual(con.connections, 1)                              # no second connection before a restart

    def test_the_copy_is_kept_if_the_console_does_not_replay_its_text(self):
        con = self.console(PASSING, replay=False)
        self.watch(con)
        self.assertEqual(con.connections, 2)
        self.assertIn("Tests completed", self.boot_text())
        self.assertTrue(any("did not send the boot text again" in l for l in LOG), LOG)

    def test_the_copy_is_dropped_if_the_console_replays_its_text(self):
        con = self.console(PASSING, replay=True)                          # the window would print it twice otherwise
        self.watch(con)
        self.assertEqual(self.boot_text(), "")
        self.assertTrue(any("no copy is kept" in l for l in LOG), LOG)
        self.assertEqual(self.state()["result"], "passed")

    def test_the_copy_is_dropped_after_giving_up_too_if_the_console_replays(self):
        con = self.console(FAILING, replay=True)
        self.assertEqual(self.watch(con, boot={"restarts": 3, "restarted_at": time.time()}), 3)
        self.assertEqual(self.boot_text(), "")

    def test_the_copy_is_kept_when_there_was_no_verdict(self):
        self.watch(self.console(STALLED, replay=True))
        self.assertIn("Performing normal system tests.", self.boot_text())

    def test_the_telnet_options_are_refused(self):
        con = self.console(PASSING)
        self.watch(con)
        time.sleep(0.3)
        self.assertEqual(con.received, bytes([255, 254, 34, 255, 254, 3, 255, 254, 1, 255, 254, 0, 255, 252, 0]))


class ReadQuietTests(unittest.TestCase):
    def test_stops_when_the_line_has_been_quiet(self):
        con = FakeConsole([(0, b"abc"), (0.1, b"def"), (5, b"late")])
        try:
            t = vc.Telnet("127.0.0.1", con.port)
            t0, seen = time.time(), []
            got = t.read_quiet(0.5, 10, seen.append)
            self.assertEqual(got, "abcdef")
            self.assertEqual("".join(seen), "abcdef")
            self.assertLess(time.time() - t0, 2.0)
            t.close()
        finally:
            con.close()

    def test_stops_at_the_limit_while_text_keeps_coming(self):
        con = FakeConsole([(0.2, b"x")] * 30)
        try:
            t = vc.Telnet("127.0.0.1", con.port)
            t0 = time.time()
            got = t.read_quiet(1.0, 1.0)
            self.assertTrue(0.9 < time.time() - t0 < 2.0)
            self.assertTrue(0 < len(got) < 29)
            t.close()
        finally:
            con.close()


class BootWatchSetupTests(unittest.TestCase):
    def test_boot_retries_and_console_defaults(self):
        self.assertEqual(vc.DEFAULTS["BOOT_RETRIES"], 3)
        self.assertEqual((vc.DEFAULTS["CONSOLE_HOST"], vc.DEFAULTS["CONSOLE_PORT"]), ("127.0.0.1", 2323))

    def test_boot_retries_from_the_config_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False) as f:
            f.write("BOOT_RETRIES=5\nCONSOLE_PORT=2400\n")
        try:
            cfg = vc.load_conf(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual((cfg["BOOT_RETRIES"], cfg["CONSOLE_PORT"]), (5, 2400))

    def test_age_of_a_process(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(d + "/proc/77")
            hz = os.sysconf("SC_CLK_TCK")
            fields = ["S"] + ["0"] * 18 + ["3000"]                        # starttime is field 22 of proc(5)
            with open(d + "/proc/77/stat", "w") as f:
                f.write("77 (simh-vax) " + " ".join(fields) + " 0 0\n")
            with open(d + "/proc/uptime", "w") as f:
                f.write("%f 0.0\n" % (3000.0 / hz + 61.5))
            old, vc.PROC = vc.PROC, d + "/proc"
            try:
                self.assertAlmostEqual(vc.proc_age(77), 61.5, places=3)
            finally:
                vc.PROC = old


if __name__ == "__main__":
    unittest.main()
