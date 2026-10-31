# games - what is on cpvax to play

The games live in `CPVAX$DUA1:[SYSTEM.GAMES]`, world-readable and world-executable so the GUEST account can run them.
`GAMES_SETUP.COM` defines the commands, `GAMES.COM` is a small menu.

| command | what | where it comes from |
|---------|------|---------------------|
| `GAMES` | menu of everything below | `GAMES.COM` here |
| `ARTY` | artillery duel against a CPU gunner | [`arty/`](arty), built on the VAX |
| `LIFE [generations] [R]` | the game of life on a wrap-around world | [`life/`](life), built on the VAX |
| `TETRIS` | falling blocks (VaxMagic, 1990); `I` shows the instructions | binary only, in `[SYSTEM.GAMES]` |
| `ZK` | Spitbrook, a 1985 text adventure from inside DEC (`QUIT` leaves it) | binary and `ZK*.ZKO` data, in `[SYSTEM.GAMES]` |
| `FROTZ file` | Infocom-style story player: `FROTZ ZCODE:ZORK.Z5` (`QUIT` leaves a story) | `VAXFROTZ.EXE`; the stories are in `[SYSTEM.GAMES.ZCODE]` |

`GAMES` lists the stories itself: every `*.Z3`/`*.Z5` file in the `ZCODE` directory, with a nicer title for the ones named
in its `TITLES` list. To add a story, copy the file into `ZCODE` (FTP in binary mode, then
`SET FILE/PROTECTION=(S:RWED,O:RWED,G:RE,W:RE)` on it).

## Who gets them

The commands exist only for accounts whose `LOGIN.COM` calls `GAMES_SETUP`: the GUEST account does (`../guest/CREATE_GUEST.COM`
writes that line). To give them to everyone, put the same line in `SYS$MANAGER:SYLOGIN.COM`:

```
$ IF F$SEARCH("CPVAX$DUA1:[SYSTEM.GAMES]GAMES_SETUP.COM") .NES. "" THEN @CPVAX$DUA1:[SYSTEM.GAMES]GAMES_SETUP
```

`GAMES_SETUP` also defines the logical names `GAMES:` (this directory) and `ZCODE:` (the stories).

## Install

As SYSTEM, copy `GAMES.COM` and `GAMES_SETUP.COM` next to the games by FTP in ASCII mode, then make them readable:

```
$ SET FILE/PROTECTION=(S:RWED,O:RWED,G:RE,W:RE) CPVAX$DUA1:[SYSTEM.GAMES]GAMES.COM,GAMES_SETUP.COM
```

The directories `[SYSTEM]` and `[SYSTEM.GAMES]` are already `W:RE`, which is all a visitor needs to run a game. Games that
save a position or a score write to the player's own default directory, or fail quietly for a guest.

## Notes

* The games only read from `[SYSTEM.GAMES]`; a guest cannot change them (world has no write access).
* `GAMES.COM` runs the stories through a foreign command symbol, `FROTZ := $...VAXFROTZ.EXE`; `ZK` and `TETRIS` are run
  with `RUN`.
* A game started from a batch job or with its input redirected fails (`%SYSTEM-F-FILNOTACC`, or spins writing output):
  they need a real terminal.
