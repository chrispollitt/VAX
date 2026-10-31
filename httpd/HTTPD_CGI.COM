$! HTTPD_CGI.COM - run one CGI script for HTTPD.EXE (it calls this through LIB$SPAWN)
$!
$!   P1 = PERL or DCL       P2 = the script's file spec       P3 = the script's directory
$!   P4 = the file holding the request body (NL: for none)
$!
$! SYS$INPUT is the request body and SYS$OUTPUT is the reply, as for any CGI.  HTTPD has
$! already set the CGI variables (REQUEST_METHOD, QUERY_STRING...) as DCL symbols.
$! Anything that has to be set up for Perl (logicals, PERL_ENV_TABLES...) goes here.
$ SET NOVERIFY
$ SET NOON
$ SET DEFAULT 'P3'
$ IF P1 .EQS. "DCL" THEN GOTO RUN_DCL
$! Perl's %ENV does not look at DCL symbols unless told to; HTTPD sets the CGI variables as symbols
$ DEFINE/NOLOG PERL_ENV_TABLES CLISYM_LOCAL, LNM$FILE_DEV, CRTL_ENV
$ SETUP = F$TRNLNM("HTTPD_PERL_SETUP")          ! defines PERLSHR and so on
$ IF (SETUP .NES. "") .AND. (F$TRNLNM("PERLSHR") .EQS. "") THEN @'SETUP'
$ PERLEXE = F$TRNLNM("HTTPD_PERL")
$ DEFINE/USER_MODE SYS$INPUT 'P4'
$ MCR 'PERLEXE' 'P2'
$ EXIT
$RUN_DCL:
$ DEFINE/USER_MODE SYS$INPUT 'P4'
$ @'P2'
$ EXIT
