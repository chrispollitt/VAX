$! START_HTTPD.COM - start HTTPD as a detached process named HTTPD (needs privileges for
$! a port below 1024 and to create a detached process; SYSTEM has them).
$!
$!    $ @START_HTTPD            start it; the log goes to HTTPD.LOG next to this file
$!    $ @START_HTTPD STOP       stop it
$!
$ HERE = F$ENVIRONMENT("PROCEDURE")
$ HERE = F$PARSE(HERE,,,"DEVICE") + F$PARSE(HERE,,,"DIRECTORY")
$ IF P1 .EQS. "STOP" THEN GOTO STOP
$ CTX = ""
$ DUMMY = F$CONTEXT("PROCESS",CTX,"PRCNAM","HTTPD","EQL")
$ IF F$PID(CTX) .NES. "" THEN GOTO RUNNING
$! /AUTHORIZE: take the quotas from the account's UAF record.  Without it the process gets the
$! small system defaults, and Perl then runs out of byte-count quota (glob, system, %ENV...).
$ RUN SYS$SYSTEM:LOGINOUT.EXE /DETACHED /AUTHORIZE /PROCESS_NAME=HTTPD -
      /INPUT='HERE'HTTPD_RUN.COM /OUTPUT='HERE'HTTPD.LOG /ERROR='HERE'HTTPD.LOG
$ WRITE SYS$OUTPUT "HTTPD started; log is ''HERE'HTTPD.LOG"
$ EXIT
$RUNNING:
$ WRITE SYS$OUTPUT "HTTPD is already running."
$ EXIT
$STOP:
$ STOP HTTPD
$ WRITE SYS$OUTPUT "HTTPD stopped."
$ EXIT
