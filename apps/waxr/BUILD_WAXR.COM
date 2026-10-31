$! BUILD_WAXR.COM -- build WAX & TAPE (DEC COBOL + embedded SQL on DEC Rdb)
$!
$! Usage:  @BUILD_WAXR [REBUILD]
$!   (default)  create the database if it is missing, load the sample
$!              collection, precompile + compile + link WAXR.
$!   REBUILD    drop and recreate the database (and reload the data).
$!
$! Run it from the directory that holds the sources.  The database
$! files (WAXDB.RDB/.RDA/.SNP) live in that same directory; the
$! logical name WAXDB points at them.
$!
$ ON CONTROL_Y THEN GOTO FAIL
$ HERE = F$ENVIRONMENT("DEFAULT")
$ DEFINE/NOLOG WAXDB 'HERE'WAXDB
$!
$ IF P1 .EQS. "REBUILD"
$ THEN
$    WRITE SYS$OUTPUT "== Dropping the old database =="
$    SET NOON
$    DEFINE/USER SYS$INPUT 'HERE'WAXDROP.SQL
$    MCR SQL$
$    SET ON
$ ENDIF
$!
$ IF F$SEARCH("WAXDB.RDB") .EQS. ""
$ THEN
$    WRITE SYS$OUTPUT "== Creating the database and loading the crates =="
$    SET NOON
$    DEFINE/USER SYS$INPUT 'HERE'WAXLOAD.SQL
$    MCR SQL$
$    SET ON
$ ELSE
$    WRITE SYS$OUTPUT "== Database exists (use @BUILD_WAXR REBUILD to reset) =="
$ ENDIF
$!
$ WRITE SYS$OUTPUT "== Precompiling + compiling WAXR (SQL$PRE/COBOL) =="
$ SQLPRE_COBOL :== $SYS$SYSTEM:SQL$PRE/COBOL
$ SET NOON
$ SQLPRE_COBOL WAXR.SCO
$ IF $SEVERITY .GE. 2 THEN GOTO FAIL
$ WRITE SYS$OUTPUT "== Linking =="
$ LINK WAXR,SYS$LIBRARY:SQL$USER/LIBRARY,SYS$LIBRARY:RDBVMS/OPTIONS
$ IF $SEVERITY .GE. 2 THEN GOTO FAIL
$!
$ WRITE SYS$OUTPUT "== Done.  Start the app with @RUN_WAXR =="
$ EXIT
$!
$ FAIL:
$ WRITE SYS$OUTPUT "BUILD_WAXR failed (see messages above)."
$ EXIT
