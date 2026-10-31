$! HTTPD_RUN.COM - the detached process's job: set up, then run the server.
$! START_HTTPD.COM starts this with RUN/DETACHED; it can also be run by hand to watch the log:
$!    $ @HTTPD_RUN
$ HERE = F$ENVIRONMENT("PROCEDURE")
$ HERE = F$PARSE(HERE,,,"DEVICE") + F$PARSE(HERE,,,"DIRECTORY")
$ SET DEFAULT 'HERE'
$ @HTTPD_CONFIG
$ RUN 'HERE'HTTPD.EXE
$ EXIT
