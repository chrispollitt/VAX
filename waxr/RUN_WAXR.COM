$! RUN_WAXR.COM -- point the logical at the database and start WAX & TAPE
$!
$! Inside a command procedure SYS$INPUT is the procedure file itself, so
$! hand the program the terminal (SYS$COMMAND) for its ACCEPTs.
$ HERE = F$ENVIRONMENT("DEFAULT")
$ DEFINE/NOLOG WAXDB 'HERE'WAXDB
$ DEFINE/USER SYS$INPUT SYS$COMMAND
$ RUN WAXR
$ EXIT
