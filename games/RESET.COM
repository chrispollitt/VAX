$ ! RESET.COM - put the terminal's display back in order after a full-screen program was interrupted
$ !
$ !   RESET         normal attributes and character set, cursor on, wrap on, insert off, full scroll region
$ !   RESET FULL    the VT100 full reset (ESC c) instead: also clears the screen and forgets everything
$ !
$ ! VMS undoes the terminal driver's own modes (echo, pass-all, type-ahead) when a program ends or is stopped, so
$ ! what an interrupted game leaves behind is only what it wrote as escape sequences: a hidden cursor, the
$ ! line-drawing character set (Tetris), reverse video, a scrolling region.  This writes the sequences that undo them.
$ ! GAMES_SETUP.COM makes RESET the command for it; GAMES.COM runs it every time the menu comes back.
$ !
$ ESC[0,8] = 27
$ IF F$EDIT(P1,"UPCASE,TRIM") .EQS. "FULL"
$ THEN
$   WRITE SYS$OUTPUT ESC + "c"
$ ELSE
$   WRITE SYS$OUTPUT ESC + "[0m" + ESC + "(B" + ESC + "[?25h" + ESC + "[?7h" + ESC + "[4l" + ESC + "[r" + ESC + ">"
$ ENDIF
$ DELETE/SYMBOL ESC
$ EXIT
