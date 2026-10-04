# VAX

Little programs for a real (well, hobbyist) **OpenVMS VAX V7.3** system, written in
**DEC C V6.4** (ANSI C89) and **DEC COBOL** (with embedded SQL on **DEC Rdb**) for
**VT100 terminals** over telnet.

| Program | What it is |
|---------|------------|
| [`life/`](life) | Conway's Game of Life on a wrap-around 22x78 world |
| [`arty/`](arty) | **ARTY** - an artillery duel against a CPU gunner, with a shop, wind, craters, MIRVs... |
| [`waxr/`](waxr) | **WAX & TAPE** - an 80s vinyl + cassette collection tracker: DEC COBOL + embedded SQL on DEC Rdb |
| [`waxweb/`](waxweb) | a modern web front end for WAXR that **screen-scrapes** the VAX over telnet (Python, no dependencies) |

Each directory holds the source plus a `BUILD_*.COM` DCL procedure that compiles it
and links it (the C programs also define a foreign command to run them).

## Building on the VAX

Get the files onto the VAX in **ASCII** mode and build from the directory they land in:

```
$ @BUILD_ARTY
$ ARTY
```

`BUILD_*.COM` does `CC`, then `LINK`, and if the plain link fails it retries with
`SYS$SHARE:VAXCRTL/SHAREABLE` (some DEC C/VAX setups need the C run-time library named).
It finishes by defining a foreign command in your process, e.g. `ARTY :== $dev:[dir]ARTY.EXE`;
put that line in your `LOGIN.COM` to keep it.

Ways to get a file there:

* **FTP** (ASCII mode) - `ftp vaxhost`, `ascii`, `put ARTY.C`.
* **Paste** into `$ CREATE ARTY.C` over telnet, finish with Ctrl-Z. Fine for the shorter files;
  none of the sources has a line longer than 100 characters.

## ARTY

```
ARTILLERY    You 0   CPU 0   (first to 3)    Wind >>>>      +4
                                   ######
                                 #########
                                ############
                               ##############                               ##
##                           ##################     ####                  ####
###               ######  ################################               #####
####            ############################################           #######
#####         ###############################################         ########
##### (P)   ################################################## (C)   #########
##############################################################################
$600  Shield:no  Weapons: 1 Baby  2 Big(0)  3 MIRV(0)  4 Dirt(0)
Weapon (1-4) [1]:
```

You are `(P)`; the CPU is `(C)`. Each turn pick a **weapon**, an **angle** (1-89 degrees)
and a **power** (1-100). Press Enter at a prompt to repeat your last value, `Q` to quit.
Shells fly in a parabola and are pushed by the **wind** shown at the top (arrows point the
way it blows, more arrows = stronger; it drifts a little every turn). A shell that goes off
the top of the screen is shown as `^` along the top row. After each shot you are told how
many columns short or long it landed.

Every blast digs a crater, and a tank whose ground is blown away **drops into the hole**.
First to 3 rounds wins the match.

### Money and the shop

Winning a round pays **$1000**; the loser still gets **$300**. You start with $600 and the
shop opens before every round. The CPU shops too.

| Item | Price | Effect |
|------|------:|--------|
| Baby shell | free | the standard shell |
| Big shell | $300 | bigger crater, bigger kill radius |
| MIRV | $500 | splits into three shells at the top of its arc |
| Dirt bomb | $150 | builds a hill instead of digging a crater (bury your target, or cover yourself) |
| Shield | $400 | absorbs one blast; your tank is drawn `[P]` while it holds |

(Shop numbers are Big, MIRV, Dirt, Shield = 1-4; in-game weapon numbers are
Baby, Big, MIRV, Dirt = 1-4. Each screen labels its own.)

### The CPU

The gunner makes an estimate for its first shot, then corrects from where each miss landed:
it backs off hard if it fires off the map, lobs a steeper shot if it hits a hill by its own
gun, and otherwise scales its power by how far it fell short or long. It is deliberately a
little sloppy and trash-talks. In testing it needs about three shots to kill a player who
doesn't shoot back.

### Test hooks

Two environment variables / logicals, handy for testing and not needed for play:

* `ARTY_SEED` - fixed random seed (`$ DEFINE ARTY_SEED 7`)
* `ARTY_FAST` - if defined at all, no animation delays

## WAXR (WAX & TAPE)

A cheeky collection tracker for 80s records and tapes: **DEC COBOL** with embedded SQL on
**DEC Rdb V6.0**. 105 artists, 146 albums and 164 LPs, cassettes and 12" singles come pre-loaded:
a made-up shelf of 80s classics (including 22 Canadian artists - Rush, Bryan Adams, Leonard Cohen,
Platinum Blonde, the Hip...) plus a real shoebox of cassettes transcribed from a photo (lots of
CCM, some Canadian, some Shostakovich, one self-hypnosis tape). Condition, price and purchase
year of the real tapes are unknown, so they show as "Grade unknown. Spooky.", "priceless" and
"????". The stats screen reports your **CanCon** share against the CRTC's 35% radio quota.
Sorry.

```
  ================================================
   W A X   &   T A P E
   the totally tubular 80s collection tracker
   (powered by DEC Rdb, because spreadsheets are
    for people who never owned a perm)
  ================================================
   1) Roll call   - every artist, album and copy
   2) Who is this - look up an artist
   3) Needle drop - find an album by title
   4) New band    - add an artist
   5) New record  - add an album
   6) Fresh wax   - add a copy (LP, tape, 12in)
   7) Sell out    - remove a copy
   8) Stats for nerds
   0) Eject
```

```
  * Duran Duran                      (UK              )  hair ##########
      1982  Rio                                      [EMI                 ]
            - 12in LP      VG+      $8.99 (1983) Played. Loved. Cared for.
              "Bought with lawn-mowing money           "
```

Needs **Rdb** (the full development kit, for the SQL precompiler) and DEC COBOL, with the Rdb
monitor running (`@SYS$STARTUP:RMONSTART`). Put the files in one directory (ASCII transfer):

```
$ @BUILD_WAXR            ! create + load the database, precompile, compile, link
$ @RUN_WAXR
$ @BUILD_WAXR REBUILD    ! start over with a pristine collection
```

| File | Purpose |
|------|---------|
| `WAXDB.SQL` | schema: `ARTIST`, `ALBUM`, `HOLDING` tables and indexes |
| `WAXDATA.SQL` | the sample collection (generated by `gen_sql.py` from the table in `gen_data.py`) |
| `WAXLOAD.SQL`, `WAXDROP.SQL` | create-and-load / drop the database (used by the build) |
| `WAXR.SCO` | the program (precompiled with `SQL$PRE/COBOL`) |
| `TEST_WAXR.COM`, `TESTIN.TXT` | run the program on canned input; output goes to `TESTOUT.LOG` |

Long listings (roll call, artist lookup, album find) are paged: every 20 lines the program shows
`-- more -- (Enter = next page, Q = stop)`.

An *album* is the music; a *holding* is a physical thing you own, so owning Rio on both vinyl and
tape is one album with two holdings. Searches are case-insensitive partial matches (`dur` finds
Duran Duran). Hair scores are the artists' (a 10 is visible from orbit).

Things learned getting it to build on DEC COBOL / Rdb 6.0:

* SQL cursor names cannot contain hyphens (COBOL host variables can).
* `ACCEPT` straight into a numeric field fails on input like `9.50` (`%COB-F-INVDECDAT`), so the
  program reads numbers as text and parses them itself.
* Link with `SYS$LIBRARY:SQL$USER/LIBRARY` and `SYS$LIBRARY:RDBVMS/OPTIONS`; the
  `%LINK-W-MULPSC` warnings are normal for precompiled Rdb programs.
* The `.SCO` file is in COBOL "terminal" reference format (no sequence-number columns).

## WAXWEB (a web front end that screen-scrapes the VAX)

[`waxweb/`](waxweb) puts a modern single-page web UI (search, filters, add/sell dialogs, stats, a live
"VAX terminal" drawer) on top of WAXR - without touching the COBOL program's interface. The server logs in
to the VAX over telnet, starts `@RUN_WAXR`, and *types at its menus like a person*: it answers the pager,
answers the "Is it this one? (Y/N)" pickers by exact match, parses the fixed-width screens into JSON, and
double-checks before it sells anything.

```
 browser  <--HTTP-->  waxweb.py  <--telnet-->  VAX: @RUN_WAXR  ->  COBOL + embedded SQL  ->  Rdb
```

Plain Python 3.7+ (standard library only) and a no-build-step vanilla JS front end. It ships with a fake
VAX (`fakevax.py`) so you can try the UI and run the tests without a VAX: `python3 waxweb/run_demo.py`.
The tests also parse real captured VAX screens. See [`waxweb/README.md`](waxweb/README.md) for the
architecture, the dedicated low-privilege VMS account it needs, running it behind an ssh tunnel, and the
security notes (it holds a VMS password and can delete records - keep it on a trusted network).

## LIFE

```
$ LIFE            ! random soup, 500 generations
$ LIFE 300 R      ! R-pentomino, 300 generations
```

The world is a 22x78 torus, so gliders wrap around the edges. It stops early if the world
dies out or settles into a still life or a period-2 oscillator. Ctrl-Y aborts.

## Developing off the VAX

The sources are plain ANSI C89 with two VMS-only bits (`<lib$routines.h>` and `lib$wait()` for
sub-second frame delays, both under `#ifdef __VMS`), so they build and run anywhere with a
VT100-ish terminal. That is how they get tested before they go over to the VAX:

```
gcc -ansi -pedantic -Wall -Wextra -o arty arty/ARTY.C -lm && ./arty
gcc -ansi -pedantic -Wall -Wextra -o life life/LIFE.C && ./life 300 R
```

Both are kept clean under `-ansi -pedantic -Wall -Wextra` (and ARTY under
`-fsanitize=address,undefined`), which is close to what DEC C will accept.

## Notes

* The math functions (`sin`, `cos`, `sqrt`) come from the C run-time library, so there is no
  separate math library to link on VMS.
* Files are stored with Unix (LF) line endings in git (`.gitattributes`); the VAX's FTP server
  converts them in ASCII mode.
* Inspired by the classic DOS artillery games - Tank Wars (Kenneth Morse, 1990) and
  Scorched Earth. No code or assets from either; ARTY is written from scratch.

## Ideas

* Two-player hot-seat mode
* Tank hit points and fuel (drive a few columns between shots)
* Napalm / roller / "funky bomb" weapons
* A Fortran, Pascal or BASIC program for the rest of the compilers on the box

## License

[MIT](LICENSE)
