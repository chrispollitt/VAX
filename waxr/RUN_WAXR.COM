$! RUN_WAXR.COM -- point the logical at the database and start WAX & TAPE
$ HERE = F$ENVIRONMENT("DEFAULT")
$ DEFINE/NOLOG WAXDB 'HERE'WAXDB
$ RUN WAXR
$ EXIT
