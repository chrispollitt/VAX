$ ! CLEAR.COM - clear the screen and put the cursor at the top left (VT100 and look-alikes).  Usage:  CLEAR   or   CLS
$ !
$ ! GAMES_SETUP.COM makes CLEAR and CLS the commands for it; GAMES.COM runs it before it draws the menu.
$ !
$ ESC[0,8] = 27
$ WRITE SYS$OUTPUT ESC + "[H" + ESC + "[2J"
$ DELETE/SYMBOL ESC
$ EXIT
