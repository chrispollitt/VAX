$ ! SYSOP.COM - call the sysop, BBS style: it is just  TALK SYSTEM  on this VAX
$ !
$ ! If SYSTEM is logged in at a terminal, TALKD rings it there and the sysop answers with  talk user@cpvax
$ ! (or PHONE).  Ctrl-C ends the call.  Lives next to TALK.COM in CPVAX$DUA1:[TALK]; the guest account
$ ! defines SYSOP as  @CPVAX$DUA1:[TALK]SYSOP  in its LOGIN.COM.
$ !
$ SET NOON
$ PROC = F$ENVIRONMENT("PROCEDURE")
$ DIR  = F$PARSE(PROC,,,"DEVICE") + F$PARSE(PROC,,,"DIRECTORY")
$ WRITE SYS$OUTPUT ""
$ WRITE SYS$OUTPUT "Paging the sysop (TALK SYSTEM) ... Ctrl-C hangs up."
$ @'DIR'TALK SYSTEM
$ WRITE SYS$OUTPUT ""
$ WRITE SYS$OUTPUT "Back at the VAX.  If nobody answered, the sysop is away from the terminal."
$ EXIT
