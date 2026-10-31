$ ! GAMES.COM - a menu of the games on this VAX.   Usage:  GAMES
$ !
$ ! Run from the directory that holds the games (CPVAX$DUA1:[SYSTEM.GAMES]); GAMES_SETUP.COM makes GAMES the
$ ! command for it.  The Infocom-style stories are the .Z3/.Z5 files in the ZCODE subdirectory: add a file there
$ ! and it shows up in the story list (give it a nicer title in the TITLES list below, if you like).
$ !
$ SET NOON
$ PROC = F$ENVIRONMENT("PROCEDURE")
$ DIR  = F$PARSE(PROC,,,"DEVICE") + F$PARSE(PROC,,,"DIRECTORY")
$ ZD   = F$EXTRACT(0,F$LENGTH(DIR) - 1,DIR) + ".ZCODE]"
$ DEFINE/NOLOG ZCODE 'ZD'
$ FROTZ := $'DIR'VAXFROTZ.EXE
$ TITLES = "HHGG=The Hitchhiker Guide to the Galaxy,ZORK=Zork,PLANETFALL=Planetfall,STATIONFALL=Stationfall,"
$ TITLES = TITLES + "BUREAUCRACY=Bureaucracy,ROGUE=Rogue,ADVENT=Colossal Cave Adventure,"
$ TITLES = TITLES + "COLOSSALCAVE=Colossal Cave Adventure (another port),ZDUNGEON=Dungeon,BAZIC=BAZIC,SPACEST2=Space Station 2"
$MENU:
$ WRITE SYS$OUTPUT ""
$ WRITE SYS$OUTPUT "  ==========  C P V A X   A R C A D E  =========="
$ WRITE SYS$OUTPUT ""
$ WRITE SYS$OUTPUT "   1  ARTY      artillery duel against a CPU gunner (Q quits)"
$ WRITE SYS$OUTPUT "   2  LIFE      the game of life, 500 generations (Ctrl-Y stops it)"
$ WRITE SYS$OUTPUT "   3  TETRIS    falling blocks (press I for the instructions)"
$ WRITE SYS$OUTPUT "   4  ZK        Spitbrook, a 1985 text adventure from DEC (QUIT leaves it)"
$ WRITE SYS$OUTPUT "   5  STORIES   Infocom-style text adventures: Zork, Hitchhiker, Planetfall ..."
$ WRITE SYS$OUTPUT "   0  quit"
$ WRITE SYS$OUTPUT ""
$ READ/END_OF_FILE=BYE/PROMPT="  Which one? " SYS$COMMAND CH
$ CH = F$EDIT(CH,"TRIM,UPCASE")
$ IF CH .EQS. "" THEN GOTO MENU
$ IF CH .EQS. "0" .OR. CH .EQS. "Q" .OR. CH .EQS. "QUIT" .OR. CH .EQS. "EXIT" THEN GOTO BYE
$ IF CH .EQS. "1" .OR. CH .EQS. "ARTY" THEN RUN 'DIR'ARTY
$ IF CH .EQS. "2" .OR. CH .EQS. "LIFE" THEN RUN 'DIR'LIFE
$ IF CH .EQS. "3" .OR. CH .EQS. "TETRIS" THEN RUN 'DIR'TETRIS
$ IF CH .EQS. "4" .OR. CH .EQS. "ZK" THEN RUN 'DIR'ZK
$ IF CH .EQS. "5" .OR. CH .EQS. "STORIES" .OR. CH .EQS. "FROTZ" THEN GOTO STORIES
$ GOTO MENU
$!
$STORIES:
$ N = 0
$ LIST = ","                            ! ,NAME.TYPE,NAME.TYPE, ... : element K is story K
$ WRITE SYS$OUTPUT ""
$ WRITE SYS$OUTPUT "  Stories (type QUIT inside a story to leave it):"
$ WRITE SYS$OUTPUT ""
$SLOOP:
$ F = F$SEARCH("''ZD'*.Z%",1)
$ IF F .EQS. "" THEN GOTO SDONE
$ NAME = F$PARSE(F,,,"NAME")
$ IF NAME .EQS. "UNICODE" THEN GOTO SLOOP
$ IF F$LOCATE("," + NAME + ".",LIST) .NE. F$LENGTH(LIST) THEN GOTO SLOOP     ! another version of one already listed
$ N = N + 1
$ LIST = LIST + NAME + F$PARSE(F,,,"TYPE") + ","
$ TITLE = NAME
$ I = 0
$TLOOP:
$ T = F$ELEMENT(I,",",TITLES)
$ IF T .EQS. "," THEN GOTO TDONE
$ IF F$ELEMENT(0,"=",T) .EQS. NAME THEN TITLE = F$ELEMENT(1,"=",T)
$ I = I + 1
$ GOTO TLOOP
$TDONE:
$ WRITE SYS$OUTPUT F$FAO("   !2SL  !AS",N,TITLE)
$ GOTO SLOOP
$SDONE:
$ IF N .EQ. 0
$ THEN
$   WRITE SYS$OUTPUT "  There are no stories in ''ZD'."
$   GOTO MENU
$ ENDIF
$ WRITE SYS$OUTPUT "    0  back to the menu"
$ WRITE SYS$OUTPUT ""
$ READ/END_OF_FILE=MENU/PROMPT="  Which story? " SYS$COMMAND CH
$ CH = F$EDIT(CH,"TRIM,UPCASE")
$ IF CH .EQS. "" .OR. CH .EQS. "0" .OR. CH .EQS. "Q" THEN GOTO MENU
$ K = F$INTEGER(CH)
$ IF K .LT. 1 .OR. K .GT. N THEN GOTO STORIES
$ STORY = F$ELEMENT(K,",",LIST)
$ WRITE SYS$OUTPUT ""
$ SPEC = ZD + STORY
$ FROTZ 'SPEC'
$ GOTO STORIES
$BYE:
$ WRITE SYS$OUTPUT "  Thanks for playing."
$ EXIT
