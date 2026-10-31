$ ! TALK.COM - TCPware's TALK, with the user name written the way the LAN's talkd wants it
$ !
$ ! TALK_SETUP.COM makes TALK a symbol for this procedure, so  TALK user@host  comes here first.
$ ! DCL upcases an unquoted parameter and the LAN's talkd (chat-setup's talkd.py on cpbee) compares names
$ ! as written, so for a user on another host the name and the host are put in lower case.  A name with
$ ! no host, or on this VAX, is left alone: those are VMS users, and VMS names are upper case.
$ !
$ ! Usage:  TALK user[@host] [ttyname]
$ !
$ SET NOON
$ TCPTALK := $TCPWARE:TALK          ! TCPware's image, as a foreign command (the TALK symbol is this procedure)
$ NAME = F$EDIT(P1,"TRIM")
$ IF NAME .EQS. "" THEN GOTO USAGE
$ AT = F$LOCATE("@",NAME)
$ IF AT .EQ. F$LENGTH(NAME) THEN GOTO RUN
$ USER = F$EXTRACT(0,AT,NAME)
$ HOST = F$EDIT(F$EXTRACT(AT+1,255,NAME),"UPCASE")
$ NODE = F$GETSYI("NODENAME")
$ IF HOST .EQS. NODE .OR. HOST .EQS. "LOCALHOST" THEN GOTO RUN
$ IF F$LOCATE(NODE + ".",HOST) .EQ. 0 THEN GOTO RUN
$ NAME = F$EDIT(USER,"LOWERCASE") + "@" + F$EDIT(HOST,"LOWERCASE")
$ P2 = F$EDIT(P2,"LOWERCASE")        ! a Linux terminal: "pts/3" (quote it, DCL reads the / as a qualifier)
$RUN:
$ DEFINE/USER_MODE SYS$INPUT SYS$COMMAND     ! TALK wants a terminal, and in a procedure SYS$INPUT is the procedure
$ TCPTALK 'NAME' 'P2'
$ EXIT
$USAGE:
$ WRITE SYS$OUTPUT "Usage: TALK user[@host] [ttyname]"
$ WRITE SYS$OUTPUT "  TALK chris@cpbee   a user on cpbee (or one using tvchat there)"
$ WRITE SYS$OUTPUT "  TALK guest         a user on this VAX"
$ EXIT
