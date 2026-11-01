$ ! GAMES_SETUP.COM - the game commands for this VAX:  GAMES (a menu), ARTY, LIFE, TETRIS, ZK, FROTZ
$ !
$ ! Lives with the games, in CPVAX$DUA1:[GAMES].  Call it from a LOGIN.COM (the GUEST account does):
$ !     $ IF F$SEARCH("CPVAX$DUA1:[GAMES]GAMES_SETUP.COM") .NES. "" THEN @CPVAX$DUA1:[GAMES]GAMES_SETUP
$ ! It finds the games next to itself, so moving the directory only needs the LOGIN.COM line changed.
$ !
$ ! CLEAR   clear the screen (CLS is the same)
$ ! RESET   tidy the terminal after an interrupted full-screen program (RESET FULL = full VT100 reset)
$ ! GAMES   the menu (GAMES.COM)          FROTZ   an Infocom story player: FROTZ ZCODE:ZORK.Z5
$ ! ARTY    artillery duel                ZK      Spitbrook, a text adventure
$ ! LIFE    game of life, LIFE [gens] [R] TETRIS  falling blocks
$ !
$ PROC = F$ENVIRONMENT("PROCEDURE")
$ DIR  = F$PARSE(PROC,,,"DEVICE") + F$PARSE(PROC,,,"DIRECTORY")
$ ZD   = F$EXTRACT(0,F$LENGTH(DIR) - 1,DIR) + ".ZCODE]"
$ DEFINE/NOLOG GAMES 'DIR'
$ DEFINE/NOLOG ZCODE 'ZD'
$ GAMES  == "@" + DIR + "GAMES"
$ RESET  == "@" + DIR + "RESET"
$ CLEAR  == "@" + DIR + "CLEAR"
$ CLS    == "@" + DIR + "CLEAR"
$ ARTY   == "$" + DIR + "ARTY.EXE"
$ LIFE   == "$" + DIR + "LIFE.EXE"
$ TETRIS == "$" + DIR + "TETRIS.EXE"
$ ZK     == "$" + DIR + "ZK.EXE"
$ FROTZ  == "$" + DIR + "VAXFROTZ.EXE"
$ EXIT
