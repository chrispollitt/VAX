$ ! BUILD_LIFE.COM - compile and link LIFE.C, then define the LIFE command
$ ! Run from the directory that holds LIFE.C:  @BUILD_LIFE
$ !
$ CC LIFE
$ IF .NOT. $STATUS THEN GOTO FAIL
$ LINK LIFE
$ IF $STATUS THEN GOTO LINKED
$ ! Some DEC C/VAX setups need the C run-time library named explicitly
$ LINK LIFE, SYS$SHARE:VAXCRTL/SHAREABLE
$ IF .NOT. $STATUS THEN GOTO FAIL
$LINKED:
$ LIFE :== $'F$ENVIRONMENT("DEFAULT")'LIFE.EXE
$ WRITE SYS$OUTPUT "Built.  Try:  LIFE 300 R   or   LIFE"
$ EXIT
$FAIL:
$ WRITE SYS$OUTPUT "Build failed."
$ EXIT
