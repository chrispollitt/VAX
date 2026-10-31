$ ! BUILD_ARTY.COM - compile and link ARTY.C, then define the ARTY command
$ ! Run from the directory that holds ARTY.C:  @BUILD_ARTY
$ !
$ CC ARTY
$ IF .NOT. $STATUS THEN GOTO FAIL
$ LINK ARTY
$ IF $STATUS THEN GOTO LINKED
$ ! Some DEC C/VAX setups need the C run-time library named explicitly
$ LINK ARTY, SYS$SHARE:VAXCRTL/SHAREABLE
$ IF .NOT. $STATUS THEN GOTO FAIL
$LINKED:
$ ARTY :== $'F$ENVIRONMENT("DEFAULT")'ARTY.EXE
$ WRITE SYS$OUTPUT "Built.  Type ARTY to play."
$ EXIT
$FAIL:
$ WRITE SYS$OUTPUT "Build failed."
$ EXIT
