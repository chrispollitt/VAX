# games - what is on cpvax to play

The games live in `CPVAX$DUA1:[GAMES]` (`[000000.GAMES]`, a top-level directory of their own, moved there from
`[SYSTEM.GAMES]` on 2026-10-31 so that visitors do not need to go through SYSTEM's home directory), world-readable and
world-executable so the GUEST account can run them. `GAMES_SETUP.COM` defines the commands, `GAMES.COM` is a small menu.

| command | what | where it comes from |
|---------|------|---------------------|
| `GAMES` | menu of everything below | `GAMES.COM` here |
| `RESET` | tidy the terminal after an interrupted full-screen game (`RESET FULL`: full VT100 reset) | `RESET.COM` here |
| `ARTY` | artillery duel against a CPU gunner | [`arty/`](arty), built on the VAX |
| `LIFE [generations] [R]` | the game of life on a wrap-around world | [`life/`](life), built on the VAX |
| `TETRIS` | falling blocks (VaxMagic, 1990); `I` shows the instructions | binary only, in `[GAMES]` |
| `ZK` | Spitbrook, a 1985 text adventure from inside DEC (`QUIT` leaves it) | binary and `ZK*.ZKO` data, in `[GAMES]` |
| `FROTZ file` | Infocom-style story player: `FROTZ ZCODE:ZORK.Z5` (`QUIT` leaves a story) | `VAXFROTZ.EXE`; the stories are in `[GAMES.ZCODE]` |

`GAMES` lists the stories itself: every `*.Z3`/`*.Z5` file in the `ZCODE` directory, with a nicer title for the ones named
in its `TITLES` list. To add a story, copy the file into `ZCODE` (FTP in binary mode, then
`SET FILE/PROTECTION=(S:RWED,O:RWED,G:RE,W:RE)` on it).

## Who gets them

The commands exist only for accounts whose `LOGIN.COM` calls `GAMES_SETUP`: the GUEST account does (`../guest/CREATE_GUEST.COM`
writes that line). To give them to everyone, put the same line in `SYS$MANAGER:SYLOGIN.COM`:

```
$ IF F$SEARCH("CPVAX$DUA1:[GAMES]GAMES_SETUP.COM") .NES. "" THEN @CPVAX$DUA1:[GAMES]GAMES_SETUP
```

`GAMES_SETUP` also defines the logical names `GAMES:` (this directory) and `ZCODE:` (the stories).

## Install

As SYSTEM, copy `GAMES.COM` and `GAMES_SETUP.COM` next to the games by FTP in ASCII mode, then make them readable:

```
$ SET FILE/PROTECTION=(S:RWED,O:RWED,G:RE,W:RE) CPVAX$DUA1:[GAMES]GAMES.COM,GAMES_SETUP.COM
```

A visitor (the GUEST account is UIC `[200,200]`, so "world" to everything here) needs **world read and execute on the
directories and on every file the games use**: the `.EXE` files, `ZK*.ZKO`, `TET*.DAT`, `*.PEN`, `TETRIS.ACN` and the
stories in `ZCODE`. Files made by SYSTEM or copied in by FTP start with no world access, and the first guest to start a game
gets `%RMS-E-PRV, insufficient privilege or file protection violation`. After adding or rebuilding anything:

```
$ SET FILE/PROTECTION=(W:RE) CPVAX$DUA1:[GAMES]*.EXE;*,*.ZKO;*,*.DAT;*,*.PEN;*,*.ACN;*
$ SET FILE/PROTECTION=(W:RE) CPVAX$DUA1:[GAMES.ZCODE]*.*;*
```

(`(W:RE)` changes only the world field.) Games that save a position or a score write to the player's own default
directory, or fail quietly for a guest.

## Notes

* The games only read from `[GAMES]`; a guest cannot change them (world has no write access).
* `GAMES.COM` runs the stories through a foreign command symbol, `FROTZ := $...VAXFROTZ.EXE`; `ZK` and `TETRIS` are run
  with `RUN`.
* A game started from a batch job or with its input redirected fails (`%SYSTEM-F-FILNOTACC`, or spins writing output):
  they need a real terminal.
* Inside a DCL procedure `SYS$INPUT` is the procedure file, not the terminal, and the games read their keys from it: ARTY quit
  at once and ZK/Tetris failed with `%SYSTEM-F-NOPRIV`. `GAMES.COM` therefore does `DEFINE/USER_MODE SYS$INPUT SYS$COMMAND`
  before each game (as `apps/talk/TALK.COM` does for TCPware's TALK). Do the same in any new launcher.
* To try a game "as the guest" without the guest's login: in a SYSTEM session, open your terminal to the world
  (`SET PROTECTION=(S:RWLP,O:RWLP,G:RWLP,W:RWLP)/DEVICE TT:`), then `SET UIC [200,200]` and
  `SET PROCESS/PRIVILEGES=(NOALL,TMPMBX,NETMBX)`, and run it. (Without the first step Pascal programs such as ZK and Tetris
  fail with NOPRIV, because the terminal belongs to SYSTEM; that is a test artifact, not a problem in a real guest login.)
* The Tetris scoreboard is `[GAMES]TETRIS.ACN`, updated in place. A guest needs write access to it or a game that
  beats the player's best stops at "Enter Your Name": it carries an ACL for the guest's UIC
  (`SET FILE/ACL=(IDENTIFIER=[200,200],ACCESS=READ+WRITE) CPVAX$DUA1:[GAMES]TETRIS.ACN`). Other users keep their normal access.
* Ctrl-Y: `GAMES.COM` catches it (`ON CONTROL_Y`), so inside a game it ends only the game and the menu comes back, and at a
  menu it leaves the arcade. `LIFE` also stops on any key.
* Terminals and full-screen programs on VMS: the driver's modes (echo, pass-all, type-ahead...) are undone when a program is
  stopped (checked: `SHOW TERMINAL` is unchanged after interrupting Tetris, ARTY and ZK), so there is no Unix-style wedged
  terminal. What can be left is display state the program wrote as escape sequences (Tetris hides the cursor and switches
  to the line-drawing character set); `RESET` writes the sequences that undo that, and `GAMES.COM` runs it each time the
  menu comes back. There is no `reset` in stock DCL; `SET TERMINAL/INQUIRE` re-reads the terminal type but sends no reset.
* Window size: TCPware's telnet server takes the client's size (NAWS) at login and again when the window is resized (checked:
  31x101 at login, 43x133 after a resize, no command needed), so `SHOW TERMINAL` is always current. VMS has no SIGWINCH, though:
  nothing tells a running program, which must query the terminal characteristics itself (SMG reads them when it starts). The
  games here draw a fixed 80x24 screen and ignore the size.
* Saved games (Frotz `.QZL`, ZK `.ZKO`) go to the player's default directory; for the guest that is `[VMSGUEST.TEMP]`
  (see `../guest`).
