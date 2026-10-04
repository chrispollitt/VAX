"""waxscrape -- drive the WAXR COBOL/Rdb program on OpenVMS by screen scraping.

The VAX program is a menu-driven terminal application.  This module logs in
over telnet, starts it, and "types" at its menus exactly like a person would,
turning the text screens it prints back into structured data.  Nothing on the
VAX side knows (or needs to know) that a web server is on the other end.
"""
import re
import threading
import time
from collections import deque

from vaxterm import PromptTimeout, Term, TerminalError

# ---------------------------------------------------------------- prompts
MENU = r"Your pick, music lover: \Z"
MORE = r"-- more -- \(Enter = next page, Q = stop\): \Z"

MEDIA_CODES = {"12in LP": "L", "Cassette": "C", "12in single": "S", "7in single": "7"}
MEDIA_NAMES = {"L": "12in LP", "C": "Cassette", "S": "12in single", "7": "7in single"}
GRADES = ["M", "NM", "VG+", "VG", "G", "F", "P"]


class WaxError(Exception):
    """The VAX program refused or failed to do what was asked.

    at_menu is True when the program had already returned to its main menu.
    """

    def __init__(self, message, at_menu=False):
        Exception.__init__(self, message)
        self.at_menu = at_menu


class NotFound(WaxError):
    pass


# ---------------------------------------------------------------- parsers
# Fixed-width layouts straight from WAXR.SCO's DISPLAY statements.
RX_ARTIST = re.compile(r"^  \* (.{32}) \((.{16})\)  hair ([#.]{10})\s*$")
RX_ALBUM = re.compile(r"^      (\d{4}|\?{4})  (.{40}) \[(.{20})\] (.{16})\s*$")
RX_COPY = re.compile(r"^            - (.{12}) (.{3}) (.{10}) \((\d{4}|\?{4})\) (.*?)\s*$")
RX_NOTE = re.compile(r'^              "(.{40})"\s*$')
RX_QUIP = re.compile(r"^  -- (.*?)\s*$")
RX_ALBUM_BY = re.compile(r"^  (.{40}) \((\d{4}|\?{4})\) by (.{32})\s*$")
RX_STAT = re.compile(r"^( {2,4})(\S.*?) \.+ +(\S.*?)\s*$")
RX_LISTED = re.compile(r"^\s+(\d+)\) (.{12}) (.{3}) (.*?)\s*$")


def _year(text):
    return int(text) if text.isdigit() else None


def _price_cents(text):
    text = text.strip()
    m = re.match(r"^\$([\d,]+)\.(\d\d)$", text)
    if not m:
        return None            # "priceless"
    return int(m.group(1).replace(",", "")) * 100 + int(m.group(2))


def parse_roll_call(text):
    """Turn the roll-call screen text into {'artists': [...], 'quip': str}."""
    artists, quip = [], None
    artist = album = copy = None
    for line in text.split("\n"):
        m = RX_ARTIST.match(line)
        if m:
            artist = {"name": m.group(1).strip(), "origin": m.group(2).strip(),
                      "hair": m.group(3).count("#"), "albums": []}
            artists.append(artist)
            album = copy = None
            continue
        m = RX_ALBUM.match(line)
        if m and artist is not None:
            album = {"title": m.group(2).strip(), "year": _year(m.group(1)),
                     "label": m.group(3).strip(), "genre": m.group(4).strip(), "copies": []}
            artist["albums"].append(album)
            copy = None
            continue
        m = RX_COPY.match(line)
        if m and album is not None:
            media_name = m.group(1).strip()
            copy = {"media": MEDIA_CODES.get(media_name, "?"), "mediaName": media_name,
                    "grade": m.group(2).strip(), "gradeName": m.group(5).strip(),
                    "priceCents": _price_cents(m.group(3)), "year": _year(m.group(4)),
                    "notes": ""}
            album["copies"].append(copy)
            continue
        m = RX_NOTE.match(line)
        if m and copy is not None:
            copy["notes"] = m.group(1).strip()
            continue
        m = RX_QUIP.match(line)
        if m:
            quip = m.group(1)
    return {"artists": artists, "quip": quip}


def parse_stats(text):
    """Parse the 'stats for nerds' screen into {'rows': [...], 'verdicts': [...]}."""
    rows, verdicts, in_table = [], [], False
    for line in text.split("\n"):
        if "THE NUMBERS" in line:
            in_table = True
            continue
        if not in_table or not line.strip():
            continue
        if line.startswith("   1) Roll call"):
            break
        m = RX_STAT.match(line)
        if m:
            rows.append({"label": m.group(2), "value": m.group(3), "indent": len(m.group(1)) > 2})
        else:
            verdicts.append(line.strip())
    return {"rows": rows, "verdicts": verdicts}


def _clean_field(text, width):
    """Make a value safe to type at a COBOL ACCEPT: one line, printable, truncated."""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(text or "")).strip()
    return text[:width]


def _same(a, b):
    return " ".join(a.split()).casefold() == " ".join(b.split()).casefold()


# ---------------------------------------------------------------- session
class WaxSession(object):
    """One logged-in VMS session running WAXR, shared by all web requests."""

    def __init__(self, host, port, user, password, wax_dir="DUA1:[SYSTEM.WAXR]",
                 cache_ttl=120, log_size=600):
        self.host, self.port = host, port
        self.user, self.password, self.wax_dir = user, password, wax_dir
        self.cache_ttl = cache_ttl
        self.lock = threading.RLock()
        self.log = deque(maxlen=log_size)
        self._log_id = 0
        self.term = Term(host, port, on_io=self._io)
        self.at_menu = False
        self._cache = None             # (timestamp, data)
        self.last_error = None
        self.logins = 0

    # -- transcript -------------------------------------------------------
    def _io(self, direction, text):
        self._log_id += 1
        self.log.append({"id": self._log_id, "t": time.time(), "dir": direction, "text": text})

    def transcript(self, since=0):
        return [e for e in list(self.log) if e["id"] > since]

    # -- connect / login / start the program ---------------------------------
    def _start(self):
        t = self.term
        t.connect()
        self.at_menu = False
        t.read_until(r"Username: ?", 90)
        t.send(self.user)
        t.read_until(r"Password: ?", 30)
        t.send(self.password, log=False)
        # The system login procedure can be slow and may swallow anything typed while it runs
        # (SET TERMINAL/INQUIRE eats type-ahead), so wait for the plain DCL prompt first.
        idx, text = t.read_until([r"Username: ?\Z", r"authorization failure", r"(?:\A|\n)\$ \Z"], 180)
        if idx != 2:
            t.close()
            raise TerminalError("VMS login failed for %s" % self.user)
        t.send('SET PROMPT="<<WAX>> "')
        t.read_until(r"\n<<WAX>> \Z", 60)
        self._dcl('SET TERMINAL/NOBROADCAST/WIDTH=132/PAGE=0/DEVICE_TYPE=VT100')
        out = self._dcl("SET DEFAULT %s" % self.wax_dir)
        if "%" in out:
            raise TerminalError("cannot use %s: %s" % (self.wax_dir, out.strip()[:200]))
        t.send("@RUN_WAXR")
        idx, text = t.read_until([MENU, r"\n<<WAX>> \Z"], 90)
        if idx != 0:
            raise TerminalError("RUN_WAXR did not reach the menu: %s" % text.strip()[-300:])
        self.at_menu = True
        self.logins += 1

    def _dcl(self, command, timeout=60):
        self.term.send(command)
        _, text = self.term.read_until(r"\n<<WAX>> \Z", timeout)
        return text

    def _ensure(self):
        if self.term.connected and self.at_menu:
            return
        self._start()

    def close(self):
        with self.lock:
            try:
                if self.term.connected and self.at_menu:
                    self.term.send("0")
                    self.term.read_until(r"\n<<WAX>> \Z", 20)
                    self.term.send("LOGOUT")
            except TerminalError:
                pass
            self.term.close()
            self.at_menu = False

    # -- running one operation -------------------------------------------------
    def _run(self, fn):
        """Run fn() against a session that is sitting at the main menu."""
        with self.lock:
            try:
                self._ensure()
                self.at_menu = False         # we are about to leave the menu
                result = fn()
                self.at_menu = True          # every operation ends back at the menu
                self.last_error = None
                return result
            except WaxError as e:
                if e.at_menu:
                    self.at_menu = True
                else:
                    self._recover()
                raise
            except (TerminalError, PromptTimeout) as e:
                self.last_error = str(e)
                self.term.close()            # unknown state: log in afresh next time
                raise

    def _recover(self):
        """After a refused operation try to get back to the menu; else drop the session."""
        try:
            self.term.read_until(MENU, 20)
            self.at_menu = True
        except TerminalError:
            self.term.close()
            self.at_menu = False

    # -- reads --------------------------------------------------------------------
    def collection(self, refresh=False):
        with self.lock:
            if not refresh and self._cache and time.time() - self._cache[0] < self.cache_ttl:
                data = dict(self._cache[1])
                data["cached"] = True
                return data

            def go():
                self.term.send("1")
                pages = []
                while True:
                    idx, text = self.term.read_until([MORE, MENU], 120)
                    pages.append(text)
                    if idx == 0:
                        self.term.send("")       # Enter = next page
                    else:
                        break
                return parse_roll_call("".join(pages))

            data = self._run(go)
            data["fetchedAt"] = time.time()
            data["cached"] = False
            self._cache = (time.time(), data)
            return data

    def stats(self):
        def go():
            self.term.send("8")
            _, text = self.term.read_until(MENU, 60)
            return parse_stats(text)
        return self._run(go)

    def _invalidate(self):
        self._cache = None

    # -- the Y/N "is it this one?" pickers -----------------------------------
    def _pick_artist(self, artist):
        t = self.term
        t.read_until(r"Artist \(name or chunk\): ", 30)
        t.send(_clean_field(artist, 32))
        while True:
            idx, text = t.read_until([r"Is it (.*?)\? \(Y/N\) ", r"No artist selected\.[^\n]*\n"], 60)
            if idx == 1:
                raise NotFound("no artist called %r" % artist)
            shown = re.findall(r"Is it (.*?)\? \(Y/N\) ", text)[-1]
            if _same(shown, _clean_field(artist, 32)):
                t.send("Y")
                return
            t.send("N")

    def _pick_album(self, title, artist):
        t = self.term
        t.read_until(r"Album title \(or chunk\): ", 30)
        t.send(_clean_field(title, 40))
        while True:
            idx, text = t.read_until([r"This one\? \(Y/N\) ", r"No album selected\.[^\n]*\n"], 60)
            if idx == 1:
                raise NotFound("no album %r by %r" % (title, artist))
            found = [RX_ALBUM_BY.match(line) for line in text.split("\n")]
            found = [m for m in found if m]
            if found and _same(found[-1].group(1), _clean_field(title, 40)) \
                    and _same(found[-1].group(3), _clean_field(artist, 32)):
                t.send("Y")
                return
            t.send("N")

    @staticmethod
    def _expect_ok(text, marker, what):
        if marker in text:
            return
        m = re.search(r"Whoa, the database just scratched the record:\n(.*?)(?:\n   1\) Roll call|\Z)", text, re.S)
        detail = " ".join(m.group(1).split()) if m else " ".join(text.split())[-200:]
        raise WaxError("%s failed: %s" % (what, detail), at_menu=True)

    # -- writes ----------------------------------------------------------------------
    def add_artist(self, name, origin, hair):
        name, origin = _clean_field(name, 32), _clean_field(origin, 16)
        if not name:
            raise WaxError("artist name is required")
        hair = max(0, min(10, int(hair or 0)))

        def go():
            t = self.term
            t.send("4")
            t.read_until(r"Band / artist name: ", 30)
            t.send(name)
            t.read_until(r"Sweden\): ", 30)
            t.send(origin or "?")
            t.read_until(r"visible from orbit\): ", 30)
            t.send(str(hair))
            _, text = t.read_until(MENU, 60)
            self._expect_ok(text, "Welcome to the shelf", "adding the artist")
            return {"ok": True, "message": "Welcome to the shelf, %s." % name}

        try:
            return self._run(go)
        finally:
            self._invalidate()

    def add_album(self, artist, title, year, label, genre):
        title = _clean_field(title, 40)
        if not title:
            raise WaxError("album title is required")

        def go():
            t = self.term
            t.send("5")
            self._pick_artist(artist)
            t.read_until(r"Album title: ", 30)
            t.send(title)
            t.read_until(r"Release year \(19xx\): ", 30)
            t.send(str(int(year or 0)))
            t.read_until(r"Label: ", 30)
            t.send(_clean_field(label, 20) or "?")
            t.read_until(r"Genre \(.*?\): ", 30)
            t.send(_clean_field(genre, 16) or "?")
            _, text = t.read_until(MENU, 60)
            self._expect_ok(text, "Filed under cool", "adding the album")
            return {"ok": True, "message": "Filed under cool."}

        try:
            return self._run(go)
        finally:
            self._invalidate()

    def add_copy(self, artist, album, media, grade, price, year, notes):
        media = str(media or "L").upper()[:1]
        if media not in MEDIA_NAMES:
            raise WaxError("media must be one of L, C, S, 7")
        grade = str(grade or "VG").upper()
        if grade not in GRADES:
            raise WaxError("grade must be one of %s" % ", ".join(GRADES))
        price = re.sub(r"[^0-9.]", "", str(price or "0")) or "0"

        def go():
            t = self.term
            t.send("6")
            self._pick_album(album, artist)
            t.read_until(r"7\)7in single: ", 30)
            t.send(media)
            t.read_until(r"Condition \(M NM VG\+ VG G F P\): ", 30)
            t.send(grade)
            t.read_until(r"\(e\.g\. 8\.99\): ", 30)
            t.send(price)
            t.read_until(r"Year bought: ", 30)
            t.send(str(int(year or 0)))
            t.read_until(r"Notes \(where\? who\? why\?\): ", 30)
            t.send(_clean_field(notes, 40))
            _, text = t.read_until(MENU, 60)
            self._expect_ok(text, "Another one for the pile", "adding the copy")
            return {"ok": True, "message": "Another one for the pile. Respect."}

        try:
            return self._run(go)
        finally:
            self._invalidate()

    def remove_copy(self, artist, album, index, media=None, notes=None):
        """Sell copy number `index` (1-based, in the order the roll call lists them)."""
        index = int(index)

        def go():
            t = self.term
            t.send("7")
            self._pick_album(album, artist)
            idx, text = t.read_until([r"\(number, 0 = keep all\): ", r"You own none of those[^\n]*\n"], 60)
            if idx == 1:
                t.read_until(MENU, 30)
                raise NotFound("no copies of that album", at_menu=True)
            listed = {}
            for line in text.split("\n"):
                m = RX_LISTED.match(line)
                if m:
                    listed[int(m.group(1))] = (m.group(2).strip(), m.group(4).strip())
            row = listed.get(index)
            safe = row is not None
            if safe and media and MEDIA_CODES.get(row[0]) != media:
                safe = False
            if safe and notes and not row[1].startswith(_clean_field(notes, 40)[:30]):
                safe = False
            t.send(str(index) if safe else "0")        # 0 = keep everything
            _, text = t.read_until(MENU, 60)
            if not safe:
                raise WaxError("the copies changed under us; nothing was sold", at_menu=True)
            self._expect_ok(text, "Sold.", "selling the copy")
            return {"ok": True, "message": "Sold. Cash in hand, hole in heart."}

        try:
            return self._run(go)
        finally:
            self._invalidate()
