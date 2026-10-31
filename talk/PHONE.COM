$ ! PHONE.COM - PHONE on this VAX calls through TALK
$ !
$ ! The VMS PHONE facility reaches only other users of this VAX (there is no DECnet here).  TALK_SETUP.COM
$ ! makes PHONE a symbol for this procedure, so PHONE and TALK end up in the same place: TCPware's TALK
$ ! and TALKD, which speak ntalk with the LAN's talkd on cpbee.
$ !
$ ! Usage:  PHONE [DIAL] user[@host] [ttyname]    call a user
$ !         PHONE                                  asks who
$ !         PHONE ANSWER                           how to answer a call
$ !         PHONE NATIVE                           the VMS PHONE, as it was
$ !
$ SET NOON
$ PROC = F$ENVIRONMENT("PROCEDURE")
$ DIR  = F$PARSE(PROC,,,"DEVICE") + F$PARSE(PROC,,,"DIRECTORY")
$ ARG  = F$EDIT(P1,"TRIM,UPCASE")
$ IF ARG .EQS. "NATIVE" THEN GOTO NATIVE
$ IF ARG .EQS. "DIAL"
$ THEN
$   P1 = P2
$   P2 = P3
$ ENDIF
$ ARG = F$EDIT(P1,"TRIM,UPCASE")
$ IF ARG .EQS. "ANSWER" .OR. ARG .EQS. "HELP" .OR. ARG .EQS. "?" THEN GOTO HELP
$ IF ARG .EQS. "HANGUP" .OR. ARG .EQS. "EXIT" .OR. ARG .EQS. "QUIT" THEN EXIT
$ IF ARG .NES. "" THEN GOTO CALL
$ READ/END_OF_FILE=DONE/PROMPT="Who do you want to call (user or user@host)? " SYS$COMMAND P1
$ P1 = F$EDIT(P1,"TRIM")
$ IF P1 .EQS. "" THEN EXIT
$CALL:
$ @'DIR'TALK 'P1' 'P2'
$DONE:
$ EXIT
$HELP:
$ WRITE SYS$OUTPUT "PHONE calls through TALK, which also reaches users on the LAN:"
$ WRITE SYS$OUTPUT "  PHONE user          a user on this VAX"
$ WRITE SYS$OUTPUT "  PHONE user@host     a user on another machine, e.g.  PHONE chris@cpbee"
$ WRITE SYS$OUTPUT "To answer a call, type what the message on your terminal says,  talk user@host,"
$ WRITE SYS$OUTPUT "or PHONE user@host.  End a call with Ctrl-C.  PHONE NATIVE runs the VMS PHONE."
$ EXIT
$NATIVE:
$ ! the symbol hides the verb: take it away for one run of the real PHONE, then put it back
$ ON CONTROL_Y THEN GOTO RESTORE
$ DELETE/SYMBOL/GLOBAL PHONE
$ PHONE
$RESTORE:
$ PHONE == "@" + PROC
$ EXIT
