#!/usr/bin/env python3
"""fakevax -- a stand-in for the VAX, for developing/testing waxweb without it.

Speaks just enough telnet to look like a VMS login, then emulates the DCL
commands the scraper uses and a faithful Python port of the WAXR program's
screens (same prompts, same fixed-width lines) over the same sample data.

    python3 fakevax.py [--port 2399] [--user waxweb] [--password demo] [--delay 0.0]
"""
import argparse
import os
import random
import re
import socketserver
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(HERE, "..", "waxrdb"), os.path.join(HERE, "..", "waxr"), HERE):
    if os.path.exists(os.path.join(cand, "gen_sql.py")):
        sys.path.insert(0, cand)
        break
import gen_sql  # noqa: E402  (provides merged(): the sample collection)

IAC, DONT, DO, WONT, WILL = 255, 254, 253, 252, 251
GRADE_NAMES = {"M": "Mint. Never played, you monster.", "NM": "Near mint. Handled with oven mitts.",
               "VG+": "Played. Loved. Cared for.", "VG": "Pops a bit. Authentic!",
               "G": "Well-loved (read: thrashed).", "F": "Fair. Plays like a bag of crisps.",
               "P": "Poor. Sentimental value only."}
MEDIA_NAMES = {"L": "12in LP", "C": "Cassette", "S": "12in single", "7": "7in single"}
QUIPS = ["Side B is where the good stuff hides.", "Have you tried turning the Walkman off and on again?",
         "Be kind, rewind.", "Mixtapes: the original playlist, with 100% more hiss.",
         "Big hair, bigger synths, biggest shoulder pads.", "If it ain't got a gatefold, is it even an album?",
         "Somewhere, a pencil is still rewinding a cassette.", "Fun fact: the 12-inch remix is never shorter.",
         "Sorry! (We say that a lot. It is in the database.)", "Hockey Night in Canada starts at 7. The tape can wait.",
         "Brought to you by CanCon. The CRTC approves this message.", "Double-double and a Rush album: a perfect day, eh."]


class DB(object):
    """The collection, with a lock so concurrent sessions behave."""

    def __init__(self):
        self.lock = threading.RLock()
        self.artists, self.albums, self.holdings = [], [], []
        aid = alb = hid = 0
        for name, origin, hair, albums in gen_sql.merged():
            aid += 1
            self.artists.append({"id": aid, "name": name[:32], "origin": origin[:16], "hair": hair})
            for title, year, label, genre, holds in albums.values():
                alb += 1
                self.albums.append({"id": alb, "artist": aid, "title": title[:40], "year": year,
                                    "label": label[:20], "genre": genre[:16]})
                for media, grade, cents, bought, notes in holds:
                    hid += 1
                    self.holdings.append({"id": hid, "album": alb, "media": media, "grade": grade.strip(),
                                          "cents": cents, "year": bought, "notes": notes[:40]})

    def artist(self, aid):
        return next(a for a in self.artists if a["id"] == aid)


DATABASE = DB()


class Session(socketserver.BaseRequestHandler):
    # ------------------------------------------------------------------ io
    def setup(self):
        self.rbuf = b""
        self.closed = False
        self.opts = self.server.opts

    def out(self, text):
        if self.opts.delay:
            time.sleep(self.opts.delay)
        data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("latin-1", "replace")
        try:
            self.request.sendall(data.replace(b"\xff", b"\xff\xff"))
        except OSError:
            self.closed = True
            raise ConnectionError()

    def readline(self, echo=True):
        while True:
            if b"\r" in self.rbuf or b"\n" in self.rbuf:
                m = re.search(rb"\r\x00|\r\n|\r|\n", self.rbuf)
                line, self.rbuf = self.rbuf[:m.start()], self.rbuf[m.end():]
                text = line.decode("latin-1")
                if echo:
                    self.out(text + "\n")
                else:
                    self.out("\n")
                return text
            try:
                data = self.request.recv(4096)
            except OSError:
                data = b""
            if not data:
                self.closed = True
                raise ConnectionError()
            self.rbuf += self._strip_iac(data)

    @staticmethod
    def _strip_iac(data):
        out, i = bytearray(), 0
        while i < len(data):
            if data[i] != IAC:
                out.append(data[i])
                i += 1
            elif i + 1 < len(data) and data[i + 1] in (DO, DONT, WILL, WONT):
                i += 3
            elif i + 1 < len(data) and data[i + 1] == 250:      # subnegotiation
                j = data.find(bytes(bytearray([IAC, 240])), i)
                i = len(data) if j < 0 else j + 2
            elif i + 1 < len(data) and data[i + 1] == IAC:
                out.append(255)
                i += 2
            else:
                i += 2
        return bytes(out)

    # ----------------------------------------------------------------- run
    def handle(self):
        try:
            self.request.sendall(bytes(bytearray([IAC, DO, 24, IAC, WILL, 1, IAC, WILL, 3, IAC, DO, 31])))
            self.out("\n Welcome to OpenVMS (TM) VAX Operating System, Version V7.3 (fake)\n\n")
            self.login()
            self.dcl()
        except ConnectionError:
            pass
        finally:
            try:
                self.request.close()
            except OSError:
                pass

    def login(self):
        while True:
            self.out("Username: ")
            user = self.readline()
            self.out("Password: ")
            pw = self.readline(echo=False)
            if user.strip().lower() == self.opts.user.lower() and pw == self.opts.password:
                self.out("\n    Last interactive login on Saturday,  3-OCT-2026 12:00\n\n")
                if getattr(self.opts, "login_delay", 0):
                    # like SYLOGIN's SET TERMINAL/INQUIRE: busy for a while, and anything typed
                    # during that time is thrown away
                    self.out("%SET-W-NOTSET, error modifying NTA2:\n-SET-I-UNKTERM, unknown terminal type\n")
                    deadline = time.time() + self.opts.login_delay
                    self.request.settimeout(0.05)
                    while time.time() < deadline:
                        try:
                            if not self.request.recv(4096):
                                break
                        except OSError:
                            pass
                    self.request.settimeout(None)
                    self.rbuf = b""
                return
            self.out("\nUser authorization failure\n\n")

    def dcl(self):
        prompt = "$ "
        while True:
            self.out(prompt)
            cmd = self.readline().strip()
            up = cmd.upper()
            m = re.match(r'SET PROMPT="(.*)"$', cmd, re.I)
            if m:
                prompt = m.group(1)
            elif up.startswith("SET TERMINAL") or up.startswith("SET DEFAULT") or not up:
                pass
            elif up == "@RUN_WAXR":
                self.waxr()
            elif up in ("LOGOUT", "LO"):
                self.out("  WAXWEB       logged out at  3-OCT-2026 12:30:00.00\n")
                return
            else:
                self.out("%%DCL-W-IVVERB, unrecognized command verb - check validity and spelling\n \\%s\\\n" % up.split(" ")[0])

    # --------------------------------------------------------------- WAXR
    def waxr(self):
        self.lines, self.quit = 0, False
        self.banner()
        while True:
            self.menu()
            choice = self.ask("  Your pick, music lover: ")[:1]
            if choice == "1":
                self.roll_call()
            elif choice == "2":
                self.lookup_artist()
            elif choice == "3":
                self.find_album()
            elif choice == "4":
                self.add_artist()
            elif choice == "5":
                self.add_album()
            elif choice == "6":
                self.add_holding()
            elif choice == "7":
                self.remove_holding()
            elif choice == "8":
                self.stats()
            elif choice == "0":
                self.quip()
                self.out(" \n  Ejecting... please return the tape to its case.\n"
                         "  Thanks for keeping it analog, you magnificent\n  hoarder.\n")
                return
            else:
                self.out("  That is not on the tracklist.\n")

    def ask(self, prompt):
        self.out(prompt)
        return self.readline()

    def banner(self):
        self.out(" \n  ================================================\n   W A X   &   T A P E\n"
                 "   the totally tubular 80s collection tracker\n   (powered by DEC Rdb, because spreadsheets are\n"
                 "    for people who never owned a perm)\n   Proudly Canadian content. Sorry for the hair.\n"
                 "  ================================================\n")

    def menu(self):
        self.out(" \n   1) Roll call   - every artist, album and copy\n   2) Who is this - look up an artist\n"
                 "   3) Needle drop - find an album by title\n   4) New band    - add an artist\n"
                 "   5) New record  - add an album\n   6) Fresh wax   - add a copy (LP, tape, 12in)\n"
                 "   7) Sell out    - remove a copy\n   8) Stats for nerds\n   0) Eject\n")

    def quip(self):
        self.out("  -- %s\n" % random.choice(QUIPS).ljust(60))

    # -- pager (NEED-LINES) --
    def need(self, n):
        if self.quit:
            return
        if self.lines + n > 20:
            ans = self.ask("  -- more -- (Enter = next page, Q = stop): ")
            if ans[:1] in ("Q", "q"):
                self.quit = True
            self.lines = 0
        self.lines += n

    # -- formatting helpers --
    @staticmethod
    def ytxt(y):
        return "%04d" % y if y else "????"

    def show_copy(self, h):
        price = "priceless".rjust(10) if h["cents"] == 0 else ("$%s" % format(h["cents"] / 100.0, ",.2f")).rjust(10)
        grade = h["grade"].ljust(3)
        name = GRADE_NAMES.get(h["grade"], "Grade unknown. Spooky.")
        self.out("            - %s %s %s (%s) %s\n" % (MEDIA_NAMES.get(h["media"], "Mystery disc").ljust(12), grade,
                                                      price, self.ytxt(h["year"]), name.ljust(36)))
        if h["notes"].strip():
            self.out('              "%s"\n' % h["notes"].ljust(40))

    def copies_of(self, album):
        return sorted((h for h in DATABASE.holdings if h["album"] == album["id"]), key=lambda h: h["id"])

    def show_copies(self, album):
        for h in self.copies_of(album):
            self.need(2 if h["notes"].strip() else 1)
            if self.quit:
                return
            self.show_copy(h)

    def show_artist_full(self, a):
        self.need(2)
        if self.quit:
            return
        bar = ("#" * min(a["hair"], 10)).ljust(10, ".")
        self.out(" \n  * %s (%s)  hair %s\n" % (a["name"].ljust(32), a["origin"].ljust(16), bar))
        for al in sorted((x for x in DATABASE.albums if x["artist"] == a["id"]), key=lambda x: (x["year"], x["title"])):
            self.need(1)
            if self.quit:
                return
            self.out("      %s  %s [%s] %s\n" % (self.ytxt(al["year"]), al["title"].ljust(40), al["label"].ljust(20),
                                                  al["genre"].ljust(16)))
            self.show_copies(al)
            if self.quit:
                return

    def by_name(self):
        return sorted(DATABASE.artists, key=lambda a: a["name"])

    def albums_by_title(self):
        return sorted(DATABASE.albums, key=lambda x: (x["title"], x["year"]))

    # -- 1) roll call --
    def roll_call(self):
        self.lines, self.quit, n = 0, False, 0
        for a in self.by_name():
            if self.quit:
                break
            self.show_artist_full(a)
            n += 1
        if n == 0:
            self.out("  The shelf is bare. A tragedy in three acts.\n")
        else:
            self.out(" \n")
            self.quip()

    # -- 2) / 3) searches --
    def search_text(self, prompt):
        return self.ask(prompt).upper().rstrip()

    def lookup_artist(self):
        s = self.search_text("  Name (or a chunk of it, Enter = everyone): ")
        self.lines, self.quit, n = 0, False, 0
        for a in self.by_name():
            if self.quit:
                break
            if s in a["name"].upper():
                n += 1
                self.show_artist_full(a)
        if n == 0:
            self.out("  Never heard of 'em. (Neither has the database.)\n")

    def album_line(self, al):
        artist = DATABASE.artist(al["artist"])
        self.out("  %s (%s) by %s\n" % (al["title"].ljust(40), self.ytxt(al["year"]), artist["name"].ljust(32)))

    def find_album(self):
        s = self.search_text("  Title (or chunk, Enter = all): ")
        self.lines, self.quit, n = 0, False, 0
        for al in self.albums_by_title():
            if self.quit:
                break
            if s in al["title"].upper():
                n += 1
                self.need(1)
                if not self.quit:
                    self.album_line(al)
                    self.show_copies(al)
        if n == 0:
            self.out("  Not in the crates. Time to go digging.\n")

    # -- pickers --
    def pick_artist(self):
        s = self.search_text("  Artist (name or chunk): ")
        for a in self.by_name():
            if s in a["name"].upper():
                if self.ask("  Is it %s? (Y/N) " % a["name"].ljust(32))[:1] in ("Y", "y"):
                    return a
        self.out("  No artist selected. Awkward silence.\n")
        return None

    def pick_album(self):
        s = self.search_text("  Album title (or chunk): ")
        for al in self.albums_by_title():
            if s in al["title"].upper():
                self.album_line(al)
                if self.ask("  This one? (Y/N) ")[:1] in ("Y", "y"):
                    return al
        self.out("  No album selected. Rewind and retry.\n")
        return None

    @staticmethod
    def num(text):
        m = re.match(r"\d+", text.strip())
        return int(m.group(0)) if m else 0

    def db_error(self, msg):
        self.out(" \n  Whoa, the database just scratched the record:\n  SQLCODE = -1\n  %s\n" % msg)

    # -- 4) add artist --
    def add_artist(self):
        name = self.ask("  Band / artist name: ")[:32]
        origin = self.ask("  Where from? (e.g. UK, USA, Sweden): ")[:16]
        hair = min(10, self.num(self.ask("  Hair score 0-10 (10 = visible from orbit): ")))
        with DATABASE.lock:
            if any(a["name"].rstrip() == name.rstrip() for a in DATABASE.artists):
                return self.db_error("%RDB-E-NO_DUP, index field value already exists")
            DATABASE.artists.append({"id": max([a["id"] for a in DATABASE.artists] or [0]) + 1,
                                     "name": name, "origin": origin, "hair": hair})
        self.out("  Welcome to the shelf, %s.\n" % name.ljust(32))

    # -- 5) add album --
    def add_album(self):
        a = self.pick_artist()
        if not a:
            return
        title = self.ask("  Album title: ")[:40]
        year = self.num(self.ask("  Release year (19xx): "))
        label = self.ask("  Label: ")[:20]
        genre = self.ask("  Genre (New Wave, Synthpop, Hair Metal...): ")[:16]
        with DATABASE.lock:
            DATABASE.albums.append({"id": max([x["id"] for x in DATABASE.albums] or [0]) + 1, "artist": a["id"],
                                    "title": title, "year": year, "label": label, "genre": genre})
        self.out("  Filed under cool.\n")

    # -- 6) add copy --
    def add_holding(self):
        al = self.pick_album()
        if not al:
            return
        media = self.ask("  Format: L)P  C)assette  S)12in single  7)7in single: ")[:1].upper()
        grade = self.ask("  Condition (M NM VG+ VG G F P): ")[:3].upper().strip()
        price = self.ask("  Price paid, dollars (e.g. 8.99): ")
        year = self.num(self.ask("  Year bought: "))
        notes = self.ask("  Notes (where? who? why?): ")[:40]
        m = re.match(r"(\d*)(?:\.(\d?)(\d?))?", price.strip())
        cents = int(m.group(1) or 0) * 100 + int((m.group(2) or "0")) * 10 + int((m.group(3) or "0"))
        with DATABASE.lock:
            DATABASE.holdings.append({"id": max([h["id"] for h in DATABASE.holdings] or [0]) + 1, "album": al["id"],
                                      "media": media, "grade": grade, "cents": cents, "year": year, "notes": notes})
        self.out("  Another one for the pile. Respect.\n")

    # -- 7) sell --
    def remove_holding(self):
        al = self.pick_album()
        if not al:
            return
        hs = self.copies_of(al)[:30]
        for i, h in enumerate(hs, 1):
            self.out("   %4d) %s %s %s\n" % (i, MEDIA_NAMES.get(h["media"], "Mystery disc").ljust(12),
                                              h["grade"].ljust(3), h["notes"]))
        if not hs:
            self.out("  You own none of those. Can't sell air.\n")
            return
        pick = self.num(self.ask("  Which copy goes to the record fair? (number, 0 = keep all): "))
        if 0 < pick <= len(hs):
            with DATABASE.lock:
                DATABASE.holdings.remove(hs[pick - 1])
            self.out("  Sold. Cash in hand, hole in heart.\n")
        else:
            self.out("  Wise. Never sell the hits.\n")

    # -- 8) stats --
    def stats(self):
        H, A, AR = DATABASE.holdings, DATABASE.albums, DATABASE.artists
        lp = sum(1 for h in H if h["media"] == "L")
        tape = sum(1 for h in H if h["media"] == "C")
        s12 = sum(1 for h in H if h["media"] == "S")
        doubles = sum(1 for al in A if sum(1 for h in H if h["album"] == al["id"]) > 1)
        can = sum(1 for a in AR if a["origin"].strip() == "Canada")
        spent = sum(h["cents"] for h in H) / 100.0
        row = lambda label, val, ind="  ": "%s%s %s %s\n" % (ind, label, "." * max(2, 24 - len(label) - 1 - len(ind) + 2), val)
        ed = lambda n: str(n).rjust(4)
        self.out(" \n  ---- THE NUMBERS (nerd mode engaged) ----\n")
        self.out("  Artists ................ %s\n" % ed(len(AR)))
        self.out("  Albums ................. %s\n" % ed(len(A)))
        self.out("  Physical objects ....... %s\n" % ed(len(H)))
        self.out("    12in LPs ............. %s\n" % ed(lp))
        self.out("    Cassettes ............ %s\n" % ed(tape))
        self.out("    12in singles ......... %s\n" % ed(s12))
        self.out("  Albums owned twice+ .... %s\n" % ed(doubles))
        self.out("  Total spent ............ %s\n" % ("$%s" % format(spent, ",.2f")).rjust(10))
        self.out("  Canadian artists (eh?) . %s\n" % ed(can))
        pct = int(can * 100 / len(AR)) if AR else 0
        self.out("  CanCon share ........... %s %%\n" % str(pct).rjust(3))
        self.out("  CanCon verdict: quota met. The CRTC salutes you.\n" if pct >= 35
                 else "  CanCon verdict: under the CRTC's 35%. Sorry.\n")
        if AR:
            avg = sum(a["hair"] for a in AR) // len(AR)
            avg10 = (sum(a["hair"] for a in AR) * 10 // len(AR)) / 10.0
            self.out("  Average artist hair .... %s / 10\n" % ("%.1f" % avg10).rjust(4))
            self.out("  Verdict: aerosol-grade. Wear a hard hat.\n" if avg10 > 7 else
                     ("  Verdict: respectable volume.\n" if avg10 > 4 else "  Verdict: suspiciously well-behaved.\n"))
        self.out("  More tape than vinyl. Walkman gang rules.\n" if tape > lp
                 else "  More vinyl than tape. Audiophile alert.\n")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=2399)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--user", default="waxweb")
    ap.add_argument("--password", default="demo")
    ap.add_argument("--delay", type=float, default=0.0, help="seconds of latency per output chunk")
    ap.add_argument("--login-delay", type=float, default=0.0, dest="login_delay",
                    help="seconds the fake login procedure is busy (type-ahead is discarded)")
    opts = ap.parse_args()
    srv = Server((opts.host, opts.port), Session)
    srv.opts = opts
    print("fakevax listening on %s:%d (login %s / %s)" % (opts.host, opts.port, opts.user, opts.password), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
