$! TEST_WAXR.COM -- drive WAXR with canned input (TESTIN.TXT), keep the output
$!
$! Exercises: roll call, artist search, album search, add artist, add album,
$! add copy, find, remove copy, stats.  Output: TESTOUT.LOG
$! Afterwards run @BUILD_WAXR REBUILD to get a pristine collection back.
$ HERE = F$ENVIRONMENT("DEFAULT")
$ DEFINE/NOLOG WAXDB 'HERE'WAXDB
$ DEFINE/USER SYS$INPUT 'HERE'TESTIN.TXT
$ DEFINE/USER SYS$OUTPUT 'HERE'TESTOUT.LOG
$ RUN WAXR
$ WRITE SYS$OUTPUT "Test run finished; see TESTOUT.LOG"
$ SEARCH TESTOUT.LOG "Whoa","SQLCODE","Bananarama","Deep Sea","Sold.","Artists ....","Albums ...","Physical","Total spent"
$ EXIT
