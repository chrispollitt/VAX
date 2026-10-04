"""vaxterm -- a tiny telnet terminal for scraping an OpenVMS login session.

Standard library only (runs on Python 3.7).  It answers just enough telnet
option negotiation to look like a VT100 (TTYPE, NAWS 132x24), strips the
VT100 escape sequences from what the host sends, and offers a small
"send a line / read until a prompt appears" API.
"""
import re
import socket
import time

IAC, DONT, DO, WONT, WILL, SB, SE = 255, 254, 253, 252, 251, 250, 240
OPT_ECHO, OPT_SGA, OPT_TTYPE, OPT_NAWS = 1, 3, 24, 31

# Queries a host can send to find out what terminal it is talking to
_DA_QUERY = re.compile(r"\[0?c|Z")          # "who are you?"  (DA / DECID)
_DSR_QUERY = re.compile(r"\[5n")                 # "are you OK?"
_CPR_QUERY = re.compile(r"\[6n")                 # "where is the cursor?"

# VT100 / ANSI escape sequences and stray control characters
_ESC = re.compile(r"\x1b(?:\[[0-9;?]*[ -/]*[@-~]|[()][0-9A-Za-z]|[=>78DEHMNOc])")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class TerminalError(Exception):
    """Connection lost, login failed, or the host stopped making sense."""


class PromptTimeout(TerminalError):
    def __init__(self, patterns, tail):
        TerminalError.__init__(self, "timed out waiting for %r; last text: %r" % (patterns, tail[-200:]))
        self.tail = tail


def clean(text):
    """Remove escape sequences / control chars and normalise line ends to \\n."""
    text = _ESC.sub("", text)
    text = text.replace("\r\n", "\n").replace("\n\r", "\n").replace("\r", "\n")
    return _CTRL.sub("", text)


class Term(object):
    def __init__(self, host, port, ttype=b"VT100", cols=132, rows=24, on_io=None):
        self.host, self.port = host, port
        self.ttype, self.cols, self.rows = ttype, cols, rows
        self.on_io = on_io           # callback(direction, text) for the transcript
        self.sock = None
        self.buf = ""                # cleaned text received but not yet consumed
        self._pending = b""          # partial IAC sequence between recv() calls
        self._sent_opts = set()      # (verb, option) we already answered

    # -- connection -------------------------------------------------------
    def connect(self, timeout=15):
        self.close()
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=timeout)
        except (OSError, socket.error) as e:
            raise TerminalError("cannot connect to %s:%s (%s)" % (self.host, self.port, e))
        self.sock.settimeout(1.0)
        self.buf, self._pending, self._sent_opts = "", b"", set()

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except (OSError, socket.error):
                pass
        self.sock = None

    @property
    def connected(self):
        return self.sock is not None

    # -- telnet negotiation ----------------------------------------------
    def _raw_send(self, data):
        try:
            self.sock.sendall(data)
        except (OSError, socket.error, AttributeError) as e:
            self.close()
            raise TerminalError("connection lost while sending (%s)" % (e,))

    def _answer(self, verb, opt):
        # reply once per (verb, option) so we never ping-pong with the server
        if (verb, opt) in self._sent_opts:
            return
        self._sent_opts.add((verb, opt))
        self._raw_send(bytes(bytearray([IAC, verb, opt])))

    def _negotiate(self, verb, opt):
        if verb == DO:
            if opt in (OPT_TTYPE, OPT_NAWS):
                self._answer(WILL, opt)
                if opt == OPT_NAWS:
                    self._raw_send(bytes(bytearray([IAC, SB, OPT_NAWS, 0, self.cols, 0, self.rows, IAC, SE])))
            else:
                self._answer(WONT, opt)
        elif verb == WILL:
            if opt in (OPT_ECHO, OPT_SGA):
                self._answer(DO, opt)
            else:
                self._answer(DONT, opt)
        # DONT / WONT need no answer

    def _filter(self, data):
        """Strip telnet commands from raw bytes, answering negotiation. Returns text."""
        data = self._pending + data
        self._pending = b""
        out = bytearray()
        i, n = 0, len(data)
        while i < n:
            b = data[i]
            if b != IAC:
                out.append(b)
                i += 1
                continue
            if i + 1 >= n:
                self._pending = data[i:]
                break
            c = data[i + 1]
            if c == IAC:                       # escaped 255
                out.append(255)
                i += 2
            elif c in (DO, DONT, WILL, WONT):
                if i + 2 >= n:
                    self._pending = data[i:]
                    break
                self._negotiate(c, data[i + 2])
                i += 3
            elif c == SB:
                end = data.find(bytes(bytearray([IAC, SE])), i + 2)
                if end < 0:
                    self._pending = data[i:]
                    break
                sub = data[i + 2:end]
                if len(sub) >= 2 and sub[0] == OPT_TTYPE and sub[1] == 1:    # TTYPE SEND
                    self._raw_send(bytes(bytearray([IAC, SB, OPT_TTYPE, 0])) + self.ttype
                                   + bytes(bytearray([IAC, SE])))
                i = end + 2
            else:                              # NOP, GA, etc.
                i += 2
        return out.decode("latin-1")

    # -- reading / writing -------------------------------------------------
    def _pump(self, wait):
        """Read whatever has arrived (up to `wait` seconds). Returns True if data came."""
        if self.sock is None:
            raise TerminalError("not connected")
        self.sock.settimeout(wait)
        try:
            data = self.sock.recv(8192)
        except socket.timeout:
            return False
        except (OSError, socket.error) as e:
            self.close()
            raise TerminalError("connection lost (%s)" % (e,))
        if not data:
            self.close()
            raise TerminalError("connection closed by the VAX")
        raw = self._filter(data)
        if _DA_QUERY.search(raw):
            self._raw_send(b"[?1;2c")            # a plain VT100 with the advanced video option
        if _DSR_QUERY.search(raw):
            self._raw_send(b"[0n")
        if _CPR_QUERY.search(raw):
            self._raw_send(b"[1;1R")
        text = clean(raw)
        if text:
            self.buf += text
            if self.on_io:
                self.on_io("in", text)
        return True

    def send(self, line="", end="\r", log=True):
        """Send a line (CR terminated, as VMS wants) -- the text is logged unless log=False."""
        data = (line + end).encode("latin-1", "replace").replace(b"\xff", b"\xff\xff")
        self._raw_send(data)
        if self.on_io:
            self.on_io("out", line if log else "********")

    def read_until(self, patterns, timeout=30):
        """Wait until the buffered text matches one of the regexes.

        Returns (index, text) where text is everything up to and including the match;
        the buffer keeps whatever follows.
        """
        if isinstance(patterns, str):
            patterns = [patterns]
        regs = [re.compile(p, re.S) for p in patterns]
        deadline = time.time() + timeout
        while True:
            best = None
            for idx, rx in enumerate(regs):
                m = rx.search(self.buf)
                if m and (best is None or m.end() < best[1].end()):
                    best = (idx, m)
            if best is not None:
                idx, m = best
                text, self.buf = self.buf[:m.end()], self.buf[m.end():]
                return idx, text
            left = deadline - time.time()
            if left <= 0:
                raise PromptTimeout([r.pattern for r in regs], self.buf)
            self._pump(min(1.0, left))

    def drain(self, quiet=1.0, limit=20):
        """Discard incoming text until the line has been quiet for `quiet` seconds."""
        end = time.time() + limit
        while time.time() < end:
            if not self._pump(quiet):
                break
        text, self.buf = self.buf, ""
        return text
