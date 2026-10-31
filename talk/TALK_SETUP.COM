$ ! TALK_SETUP.COM - make TALK and PHONE the procedures next to this file
$ ! Called from SYS$MANAGER:SYLOGIN.COM (after TCPWARE_COMMANDS, which defines TALK as the TCPware image).
$ PROC = F$ENVIRONMENT("PROCEDURE")
$ DIR  = F$PARSE(PROC,,,"DEVICE") + F$PARSE(PROC,,,"DIRECTORY")
$ TALK  == "@" + DIR + "TALK"
$ PHONE == "@" + DIR + "PHONE"
$ EXIT
