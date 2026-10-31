"""Tests for the scraper: parsers against REAL captured VAX screens, and the full
session driver against the fake VAX.   Run:  python -m unittest discover -s tests -v
"""
import os
import sys
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

import fakevax  # noqa: E402
import waxscrape  # noqa: E402
from waxscrape import NotFound, WaxError, WaxSession  # noqa: E402


def read(name):
    with open(os.path.join(HERE, name), encoding="latin-1") as f:
        return f.read()


class RealScreens(unittest.TestCase):
    """Parsers vs. text captured from the real VAX (see tests/real_*.txt)."""

    @classmethod
    def setUpClass(cls):
        cls.rc = waxscrape.parse_roll_call(read("real_roll_call.txt"))

    def test_totals_match_the_database(self):
        artists = self.rc["artists"]
        albums = [al for a in artists for al in a["albums"]]
        copies = [c for al in albums for c in al["copies"]]
        self.assertEqual((len(artists), len(albums), len(copies)), (105, 146, 164))

    def test_first_artist_in_full(self):
        a = self.rc["artists"][0]
        self.assertEqual((a["name"], a["origin"], a["hair"]), ("A-ha", "Norway", 9))
        al = a["albums"][0]
        self.assertEqual((al["title"], al["year"], al["label"], al["genre"]),
                         ("Hunting High and Low", 1985, "Warner Bros.", "Synthpop"))
        c = al["copies"][0]
        self.assertEqual((c["media"], c["grade"], c["priceCents"], c["year"]), ("C", "VG+", 799, 1986))
        self.assertEqual(c["notes"], "Take On Me, rotoscope in my head")
        self.assertEqual(c["gradeName"], "Played. Loved. Cared for.")

    def test_unknown_values_become_none(self):
        amy = next(a for a in self.rc["artists"] if a["name"] == "Amy Grant")
        c = amy["albums"][0]["copies"][0]
        self.assertIsNone(c["priceCents"])
        self.assertIsNone(c["year"])
        self.assertEqual(c["grade"], "?")
        self.assertTrue(c["gradeName"].startswith("Grade unknown"))

    def test_unknown_album_year(self):
        sandi = next(a for a in self.rc["artists"] if a["name"] == "Sandi Patty")
        self.assertIsNone(sandi["albums"][0]["year"])

    def test_merged_album_has_all_three_formats(self):
        hl = next(a for a in self.rc["artists"] if a["name"] == "The Human League")
        dare = next(al for al in hl["albums"] if al["title"] == "Dare")
        self.assertEqual(sorted(c["media"] for c in dare["copies"]), ["C", "L", "S"])

    def test_names_with_odd_characters(self):
        names = {a["name"] for a in self.rc["artists"]}
        self.assertIn("Guns N' Roses", names)
        self.assertIn("Stanley Fisher, Ph.D.", names)
        titles = {al["title"] for a in self.rc["artists"] for al in a["albums"]}
        self.assertIn("Sign o' the Times", titles)

    def test_quip_is_scraped(self):
        self.assertTrue(self.rc["quip"])

    def test_stats(self):
        st = waxscrape.parse_stats(read("real_stats.txt"))
        rows = {r["label"]: r["value"] for r in st["rows"]}
        self.assertEqual(rows["Artists"], "105")
        self.assertEqual(rows["Cassettes"], "111")
        self.assertEqual(rows["Total spent"], "$768.13")
        self.assertEqual(rows["CanCon share"], "26 %")
        self.assertTrue(any("CanCon verdict" in v for v in st["verdicts"]))
        self.assertTrue(any("Walkman" in v for v in st["verdicts"]))


class AgainstFakeVax(unittest.TestCase):
    """The whole session driver (login, pager, Y/N pickers, writes) vs fakevax."""

    @classmethod
    def setUpClass(cls):
        class Opts(object):
            user, password, delay = "waxweb", "s3cr3t-pw!", 0.0
        cls.srv = fakevax.Server(("127.0.0.1", 0), fakevax.Session)
        cls.srv.opts = Opts()
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.s = WaxSession("127.0.0.1", cls.port, "waxweb", "s3cr3t-pw!", cache_ttl=0)

    @classmethod
    def tearDownClass(cls):
        cls.s.close()
        cls.srv.shutdown()

    def collection(self):
        return self.s.collection(refresh=True)

    def artist(self, name):
        return next((a for a in self.collection()["artists"] if a["name"] == name), None)

    def test_01_roll_call_through_the_pager(self):
        data = self.collection()
        self.assertEqual(len(data["artists"]), 105)
        copies = sum(len(al["copies"]) for a in data["artists"] for al in a["albums"])
        self.assertEqual(copies, 164)

    def test_02_stats(self):
        rows = {r["label"]: r["value"] for r in self.s.stats()["rows"]}
        self.assertEqual(rows["Albums"], "146")

    def test_03_add_artist_album_copy_then_sell(self):
        self.s.add_artist("Test Pattern", "Canada", 11)          # hair is clamped to 10
        a = self.artist("Test Pattern")
        self.assertEqual((a["origin"], a["hair"]), ("Canada", 10))
        self.s.add_album("Test Pattern", "Colour Bars", 1984, "Cathode", "New Wave")
        al = self.artist("Test Pattern")["albums"][0]
        self.assertEqual((al["title"], al["year"], al["genre"]), ("Colour Bars", 1984, "New Wave"))
        self.s.add_copy("Test Pattern", "Colour Bars", "c", "vg+", "$8.99", 1985, "Bought at the mall")
        self.s.add_copy("Test Pattern", "Colour Bars", "L", "NM", "12.5", 1986, "Second copy")
        copies = self.artist("Test Pattern")["albums"][0]["copies"]
        self.assertEqual([(c["media"], c["grade"], c["priceCents"]) for c in copies],
                         [("C", "VG+", 899), ("L", "NM", 1250)])
        self.s.remove_copy("Test Pattern", "Colour Bars", 1, media="C", notes="Bought at the mall")
        copies = self.artist("Test Pattern")["albums"][0]["copies"]
        self.assertEqual([c["notes"] for c in copies], ["Second copy"])

    def test_04_same_title_different_artist_is_picked_correctly(self):
        # "Greatest Hits"-style ambiguity: Symphony No. 5 exists for two composers
        self.s.add_copy("Gustav Mahler", "Symphony No. 5", "C", "VG", "1", 1990, "mahler copy")
        mahler = self.artist("Gustav Mahler")["albums"][0]["copies"]
        shosta = self.artist("Dmitri Shostakovich")["albums"][0]["copies"]
        self.assertEqual(len(mahler), 2)
        self.assertEqual(len(shosta), 1)

    def test_05_errors(self):
        with self.assertRaises(NotFound):
            self.s.add_album("Nobody At All", "Nothing", 1999, "x", "y")
        with self.assertRaises(NotFound):
            self.s.add_copy("Rush", "No Such Album", "L", "VG", "5", 1990, "")
        with self.assertRaises(WaxError):
            self.s.add_artist("Rush", "Canada", 7)               # duplicate name
        with self.assertRaises(WaxError):
            self.s.add_copy("Rush", "Signals", "X", "VG", "5", 1990, "")   # bad media code
        # and the session is still healthy afterwards
        self.assertEqual(len(self.collection()["artists"]) >= 105, True)

    def test_06_refused_sale_does_not_sell(self):
        before = len(self.artist("Rush")["albums"][1]["copies"])
        with self.assertRaises(WaxError):
            self.s.remove_copy("Rush", "Signals", 1, media="L")   # the only copy is a cassette
        self.assertEqual(len(self.artist("Rush")["albums"][1]["copies"]), before)

    def test_07_transcript_never_contains_the_password(self):
        fresh = WaxSession("127.0.0.1", self.port, "waxweb", "s3cr3t-pw!", log_size=5000)
        try:
            fresh.stats()                       # forces a login
            text = " ".join(e["text"] for e in fresh.transcript())
        finally:
            fresh.close()
        self.assertNotIn("s3cr3t-pw!", text)
        self.assertIn("********", text)

    def test_09_login_survives_a_slow_typeahead_eating_login_script(self):
        class SlowOpts(object):
            user, password, delay, login_delay = "waxweb", "pw", 0.0, 0.6
        srv = fakevax.Server(("127.0.0.1", 0), fakevax.Session)
        srv.opts = SlowOpts()
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        slow = WaxSession("127.0.0.1", srv.server_address[1], "waxweb", "pw")
        try:
            # (fakevax's collection is shared by the whole test run, so earlier tests may have added to it)
            self.assertGreaterEqual(len(slow.collection(refresh=True)["artists"]), 105)
        finally:
            slow.close()
            srv.shutdown()

    def test_08_wrong_password_is_reported(self):
        bad = WaxSession("127.0.0.1", self.port, "waxweb", "nope")
        try:
            with self.assertRaises(waxscrape.TerminalError):
                bad.stats()
        finally:
            bad.close()


if __name__ == "__main__":
    unittest.main()
