$ ! CREATE_GUEST.COM - create a shared, unprivileged GUEST account (OpenVMS VAX V7.3)
$ !
$ ! Run as SYSTEM (needs SYSPRV):
$ !     $ @CREATE_GUEST [user] [password] [uic] [device]
$ !
$ !   user      account name                  default GUEST
$ !   password  the shared visitor pw; if omitted it is asked for, no echo
$ !   uic       UIC as [group,member] (octal) default [200,200]
$ !   device    home directory device         default SYS$SYSDEVICE:
$ !
$ ! The home directory is [user] on the device, e.g. SYS$SYSDEVICE:[GUEST].
$ !
$ ! Safe to run twice: if the account already exists it reports that and
$ ! changes nothing.  The password is never printed.  It does sit in a
$ ! temporary command file in SYS$SCRATCH for a moment; that file is made
$ ! unreadable to group and world and deleted again.
$ !
$ ! What it does, step by step (each step prints a line as it runs):
$ !   1 check privileges and parameters
$ !   2 look for an existing account (AUTHORIZE SHOW)
$ !   3 AUTHORIZE ADD with the core qualifiers
$ !   4 AUTHORIZE MODIFY, one hardening qualifier per run, so one that this
$ !     VMS does not know cannot stop the account being created
$ !   5 create the home directory, closed to group and world
$ !   6 write a minimal LOGIN.COM in it
$ !   7 show the account record and print a summary and how to undo it
$ !
$ SET NOON
$ SET NOVERIFY
$ SAY = "WRITE SYS$OUTPUT"
$ !
$ ! How AUTHORIZE is run.  If DEFINE/USER does not reach it through MCR on
$ ! your system, change this to:  RUN SYS$SYSTEM:AUTHORIZE
$ AUTH_CMD = "MCR AUTHORIZE"
$ !
$ FINAL = 1
$ FAILSTAT = %X10000002
$ ECHO_OFF = 0
$ PROT_SAVED = 0
$ OLD_PROT = ""
$ ST_ADD = "not done"
$ ST_HARD = "not done"
$ ST_DIR = "not done"
$ ST_LOGIN = "not done"
$ MOD_BAD = 0
$ UE_SILENT == 0
$ UE_NOUAF == 0
$ UAF_DEF = 0
$ RL_DEF = 0
$ UAF_TXT = ""
$ G_USER = ""
$ G_UIC = ""
$ G_DEV = ""
$ G_DIR = ""
$ G_HOME = ""
$ ALNUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$_"
$ ON CONTROL_Y THEN GOTO ABORTED
$ !
$ SAY ""
$ SAY "CREATE_GUEST - shared guest account on OpenVMS"
$ SAY ""
$ !
$ ! ---------------------------------------------------------------- step 1
$ SAY "Step 1 of 7: check privileges and parameters"
$ IF F$PRIVILEGE("SYSPRV") THEN GOTO PRIV_OK
$ SAY "  ERROR: SYSPRV is needed to change the UAF.  Run this as SYSTEM."
$ GOTO FAIL
$PRIV_OK:
$ !
$ ! Where AUTHORIZE finds the user and rights-list files.  Some systems never
$ ! define the logical names SYSUAF and RIGHTSLIST; LOGINOUT does not need
$ ! them, but AUTHORIZE then looks in the current default directory (for
$ ! SYSTEM that is [SYSTEM], not SYS$SYSTEM) and fails with NAOFIL.  If they
$ ! are not defined, define them for this process only, and remove them at
$ ! the end.  If they are defined, they are left alone.
$ IF F$TRNLNM("SYSUAF") .NES. "" THEN GOTO UAF_HAVE
$ DEFINE/PROCESS SYSUAF SYS$SYSTEM:SYSUAF.DAT
$ UAF_DEF = 1
$UAF_HAVE:
$ IF F$TRNLNM("RIGHTSLIST") .NES. "" THEN GOTO RL_HAVE
$ DEFINE/PROCESS RIGHTSLIST SYS$SYSTEM:RIGHTSLIST.DAT
$ RL_DEF = 1
$RL_HAVE:
$ UAF_TXT = F$TRNLNM("SYSUAF")
$ !
$ G_USER =F$EDIT(P1,"UPCASE,COLLAPSE")
$ IF G_USER .EQS. "" THEN G_USER = "GUEST"
$ CALL CHECK_CHARS "''G_USER'" "''ALNUM'" 1 12
$ IF .NOT. $STATUS THEN GOTO BAD_USER
$ !
$ G_UIC = F$EDIT(P3,"UPCASE,COLLAPSE")
$ IF G_UIC .EQS. "" THEN G_UIC = "[200,200]"
$ IF F$EXTRACT(0,1,G_UIC) .NES. "[" THEN GOTO BAD_UIC
$ IF F$EXTRACT(F$LENGTH(G_UIC)-1,1,G_UIC) .NES. "]" THEN GOTO BAD_UIC
$ INNER = F$EXTRACT(1,F$LENGTH(G_UIC)-2,G_UIC)
$ COMMA = F$LOCATE(",",INNER)
$ IF COMMA .EQ. F$LENGTH(INNER) THEN GOTO BAD_UIC
$ G_GRP = F$EXTRACT(0,COMMA,INNER)
$ G_MEM = F$EXTRACT(COMMA+1,99,INNER)
$ CALL CHECK_CHARS "''G_GRP'" "01234567" 1 6
$ IF .NOT. $STATUS THEN GOTO BAD_UIC
$ CALL CHECK_CHARS "''G_MEM'" "01234567" 1 6
$ IF .NOT. $STATUS THEN GOTO BAD_UIC
$ !
$ G_DEV = F$EDIT(P4,"UPCASE,COLLAPSE")
$ IF G_DEV .EQS. "" THEN G_DEV = "SYS$SYSDEVICE:"
$ IF F$EXTRACT(F$LENGTH(G_DEV)-1,1,G_DEV) .NES. ":" THEN G_DEV = G_DEV + ":"
$ DEVCH = ALNUM + ":"
$ CALL CHECK_CHARS "''G_DEV'" "''DEVCH'" 2 32
$ IF .NOT. $STATUS THEN GOTO BAD_DEV
$ IF .NOT. F$GETDVI(G_DEV,"EXISTS") THEN GOTO BAD_DEV
$ !
$ G_DIR = G_USER
$ G_HOME = G_DEV + "[" + G_DIR + "]"
$ !
$ G_PW = F$EDIT(P2,"UPCASE,COLLAPSE")
$ IF G_PW .NES. "" THEN GOTO PW_GOT
$ IF F$MODE() .NES. "INTERACTIVE" THEN GOTO NO_PW
$ SAY "  No password was given.  Typing is not echoed."
$ SET TERMINAL/NOECHO
$ ECHO_OFF = 1
$ READ/END_OF_FILE=PW_EOF/PROMPT="  Password for ''G_USER': " SYS$COMMAND G_PW
$ SAY ""
$ READ/END_OF_FILE=PW_EOF/PROMPT="  Same password once more: " SYS$COMMAND G_PW2
$ SAY ""
$ SET TERMINAL/ECHO
$ ECHO_OFF = 0
$ G_PW = F$EDIT(G_PW,"UPCASE,COLLAPSE")
$ G_PW2 = F$EDIT(G_PW2,"UPCASE,COLLAPSE")
$ IF G_PW .NES. G_PW2 THEN GOTO PW_MISMATCH
$PW_GOT:
$ CALL CHECK_CHARS "''G_PW'" "''ALNUM'" 1 32
$ IF .NOT. $STATUS THEN GOTO BAD_PW
$ IF F$LENGTH(G_PW) .LT. 6 THEN SAY "  Note: the password is under 6 characters; AUTHORIZE may reject it."
$ !
$ PID = F$GETJPI("","PID")
$ BASE = "SYS$SCRATCH:CRG_" + F$STRING(PID)
$ OLD_PROT = F$ENVIRONMENT("PROTECTION")
$ SET PROTECTION=(S:RWED,O:RWED,G,W)/DEFAULT
$ PROT_SAVED = 1
$ !
$ SAY "  account   : ''G_USER'"
$ SAY "  UIC       : ''G_UIC'"
$ SAY "  device    : ''G_DEV'"
$ SAY "  home      : ''G_HOME'"
$ SAY "  password  : (not shown)"
$ IF UAF_DEF THEN SAY "  UAF       : ''UAF_TXT'  (SYSUAF was not defined; defined for this run only)"
$ IF .NOT. UAF_DEF THEN SAY "  UAF       : ''UAF_TXT'"
$ SAY ""
$ !
$ ! ---------------------------------------------------------------- step 2
$ SAY "Step 2 of 7: look for an existing ''G_USER' account"
$ CALL USER_EXISTS "''G_USER'" "SHOW0"
$ IF $STATUS THEN GOTO ALREADY
$ IF UE_NOUAF THEN GOTO NO_UAF
$ IF .NOT. UE_SILENT THEN GOTO NOT_FOUND
$ SAY "  AUTHORIZE printed nothing with:  ''AUTH_CMD'"
$ SAY "  Trying  RUN SYS$SYSTEM:AUTHORIZE  instead."
$ AUTH_CMD = "RUN SYS$SYSTEM:AUTHORIZE"
$ CALL USER_EXISTS "''G_USER'" "SHOW0B"
$ IF $STATUS THEN GOTO ALREADY
$ IF UE_NOUAF THEN GOTO NO_UAF
$ IF .NOT. UE_SILENT THEN GOTO NOT_FOUND
$ SAY "  ERROR: AUTHORIZE printed nothing that way either.  Nothing was changed."
$ SAY "  Try it by hand:  $ MCR AUTHORIZE  then  UAF> SHOW ''G_USER'"
$ GOTO FAIL
$NOT_FOUND:
$ SAY "  not found - will create it"
$ !
$ ! ---------------------------------------------------------------- step 3
$ SAY "Step 3 of 7: AUTHORIZE ADD ''G_USER' (core qualifiers)"
$ F_ADDC = BASE + "_ADDC.TMP"
$ F_ADDO = BASE + "_ADDO.TMP"
$ OPEN/WRITE/ERROR=ADD_NOFILE CRGF 'F_ADDC'
$ WRITE CRGF "ADD ''G_USER' /PASSWORD=''G_PW' /OWNER=""Guest visitor"" /UIC=''G_UIC' -"
$ WRITE CRGF "   /DEVICE=''G_DEV' /DIRECTORY=[''G_DIR'] /PRIVILEGES=(TMPMBX,NETMBX) -"
$ WRITE CRGF "   /DEFPRIVILEGES=(TMPMBX,NETMBX) /FLAGS=(LOCKPWD)"
$ WRITE CRGF "EXIT"
$ CLOSE CRGF
$ F_ADDE = BASE + "_ADDE.TMP"
$ F_ADDOE = F_ADDO + "," + F_ADDE
$ CALL RUN_AUTH "''F_ADDC'" "''F_ADDO'" "''F_ADDE'"
$ DELETE/NOLOG 'F_ADDC';*
$ CALL USER_EXISTS "''G_USER'" "SHOW1"
$ IF $STATUS THEN GOTO ADD_OK
$ ST_ADD = "FAILED"
$ SAY "  ERROR: the account is not in the UAF after ADD."
$ CALL NO_OUTPUT "''F_ADDO'" "''F_ADDE'"
$ IF $STATUS THEN GOTO ADD_SILENT
$ SAY "  AUTHORIZE said:"
$ TYPE 'F_ADDOE'
$ GOTO FAIL_SUMMARY
$ADD_SILENT:
$ SAY "  AUTHORIZE printed nothing at all."
$ GOTO FAIL_SUMMARY
$ADD_NOFILE:
$ ST_ADD = "FAILED"
$ SAY "  ERROR: cannot create the temporary command file ''F_ADDC'"
$ GOTO FAIL_SUMMARY
$ADD_OK:
$ ST_ADD = "done"
$ SAY "  account ''G_USER' added"
$ SAY ""
$ !
$ ! ---------------------------------------------------------------- step 4
$ SAY "Step 4 of 7: hardening, one AUTHORIZE MODIFY per qualifier"
$ SAY "  (a FAILED line is not fatal: the account already exists)"
$ CALL MOD_ONE "/NOPWDEXPIRED" "M1"
$ IF .NOT. $STATUS THEN MOD_BAD = MOD_BAD + 1
$ CALL MOD_ONE "/PWDLIFETIME=NONE" "M2"
$ IF .NOT. $STATUS THEN MOD_BAD = MOD_BAD + 1
$ CALL MOD_ONE "/NOEXPIRATION" "M3"
$ IF .NOT. $STATUS THEN MOD_BAD = MOD_BAD + 1
$ CALL MOD_ONE "/ACCOUNT=GUEST" "M4"
$ IF .NOT. $STATUS THEN MOD_BAD = MOD_BAD + 1
$ CALL MOD_ONE "/MAXJOBS=4" "M5"
$ IF .NOT. $STATUS THEN MOD_BAD = MOD_BAD + 1
$ CALL MOD_ONE "/PRCLM=3" "M6"
$ IF .NOT. $STATUS THEN MOD_BAD = MOD_BAD + 1
$ CALL MOD_ONE "/FLAGS=(DISMAIL)" "M7"
$ IF .NOT. $STATUS THEN MOD_BAD = MOD_BAD + 1
$ CALL MOD_ONE "/NOBATCH" "M8"
$ IF .NOT. $STATUS THEN MOD_BAD = MOD_BAD + 1
$ ! A new account copies the DEFAULT record, which on this system has DISUSER set,
$ ! and DISUSER means "User authorization failure" at every login.
$ CALL MOD_ONE "/FLAGS=(NODISUSER)" "M9"
$ IF .NOT. $STATUS THEN MOD_BAD = MOD_BAD + 1
$ ST_HARD = "done"
$ IF MOD_BAD .GT. 0 THEN ST_HARD = "done, but ''MOD_BAD' of 9 MODIFY runs reported errors"
$ SAY ""
$ !
$ ! ---------------------------------------------------------------- step 5
$ SAY "Step 5 of 7: home directory ''G_HOME'"
$ IF F$SEARCH("''G_DEV'[000000]''G_DIR'.DIR;1",1) .EQS. "" THEN GOTO DIR_MAKE
$ SAY "  the directory already exists - left as it is"
$ ST_DIR = "already there"
$ GOTO DIR_DONE
$DIR_MAKE:
$ CREATE/DIRECTORY 'G_HOME' /OWNER_UIC='G_UIC' /PROTECTION=(S:RWE,O:RWE,G,W)
$ IF $STATUS THEN GOTO DIR_CREATED
$ ST_DIR = "FAILED"
$ SAY "  ERROR: CREATE/DIRECTORY failed (message above)"
$ GOTO DIR_DONE
$DIR_CREATED:
$ ST_DIR = "done"
$ SAY "  created, owner ''G_UIC', no group or world access"
$DIR_DONE:
$ SAY ""
$ !
$ ! ---------------------------------------------------------------- step 6
$ SAY "Step 6 of 7: ''G_HOME'LOGIN.COM"
$ IF ST_DIR .EQS. "FAILED" THEN GOTO LOGIN_SKIP
$ IF F$SEARCH("''G_HOME'LOGIN.COM",2) .EQS. "" THEN GOTO LOGIN_MAKE
$ SAY "  LOGIN.COM already exists - left as it is"
$ ST_LOGIN = "already there"
$ GOTO LOGIN_DONE
$LOGIN_SKIP:
$ SAY "  skipped, there is no home directory"
$ ST_LOGIN = "skipped"
$ GOTO LOGIN_DONE
$LOGIN_MAKE:
$ OPEN/WRITE/ERROR=LOGIN_NOFILE CRGF 'G_HOME'LOGIN.COM
$ WRITE CRGF "$ ! LOGIN.COM for ''G_USER' - written by CREATE_GUEST.COM"
$ WRITE CRGF "$ SET TERMINAL/INQUIRE"
$ WRITE CRGF "$ SET PROMPT=""''G_USER'> """
$ WRITE CRGF "$ WRITE SYS$OUTPUT "" """
$ WRITE CRGF "$ WRITE SYS$OUTPUT ""Welcome, visitor!  This is a shared guest account."""
$ WRITE CRGF "$ WRITE SYS$OUTPUT ""Please do not keep anything here that you care about."""
$ WRITE CRGF "$ WRITE SYS$OUTPUT "" """
$ WRITE CRGF "$ ! Foreign commands for the hobbyist programs.  Edit the device and"
$ WRITE CRGF "$ ! directory to where ARTY.EXE and LIFE.EXE really live, then remove"
$ WRITE CRGF "$ ! the leading ! on the lines (same form as BUILD_ARTY.COM / BUILD_LIFE.COM)."
$ WRITE CRGF "$ ! ARTY :== $SYS$SYSDEVICE:[GAMES]ARTY.EXE"
$ WRITE CRGF "$ ! LIFE :== $SYS$SYSDEVICE:[GAMES]LIFE.EXE"
$ WRITE CRGF "$ EXIT"
$ CLOSE CRGF
$ SET FILE/OWNER_UIC='G_UIC' 'G_HOME'LOGIN.COM
$ SET FILE/PROTECTION=(S:RWED,O:RE,G,W) 'G_HOME'LOGIN.COM
$ ST_LOGIN = "done"
$ SAY "  written, owned by ''G_UIC', read-only for the account"
$ GOTO LOGIN_DONE
$LOGIN_NOFILE:
$ ST_LOGIN = "FAILED"
$ SAY "  ERROR: cannot create ''G_HOME'LOGIN.COM"
$LOGIN_DONE:
$ SAY ""
$ !
$ ! ---------------------------------------------------------------- step 7
$ SAY "Step 7 of 7: the account record as AUTHORIZE now has it"
$ CALL USER_EXISTS "''G_USER'" "SHOWV"
$ F_VERO = BASE + "_SHOWVO.TMP"
$ TYPE 'F_VERO'
$ CALL QSEARCH "''F_VERO'" "pre-expired"
$ IF .NOT. $STATUS THEN GOTO NOT_PREEXP
$ SAY "  WARNING: the password shows as pre-expired.  With LOCKPWD, visitors"
$ SAY "  cannot log in.  Fix:  $ MCR AUTHORIZE MODIFY ''G_USER' /NOPWDEXPIRED"
$ FINAL = FAILSTAT
$NOT_PREEXP:
$ CALL QSEARCH "''F_VERO'" "DisUser"
$ IF .NOT. $STATUS THEN GOTO NOT_DISUSER
$ SAY "  WARNING: the account is flagged DisUser (disabled); nobody can log in."
$ SAY "  Fix:  $ MCR AUTHORIZE MODIFY ''G_USER' /FLAGS=NODISUSER"
$ FINAL = FAILSTAT
$NOT_DISUSER:
$ IF ST_ADD .NES. "done" THEN FINAL = FAILSTAT
$ IF ST_DIR .EQS. "FAILED" THEN FINAL = FAILSTAT
$ IF ST_LOGIN .EQS. "FAILED" THEN FINAL = FAILSTAT
$ GOTO SUMMARY
$ !
$ ! ---------------------------------------------------------------- end
$ALREADY:
$ SAY "  The account ''G_USER' already exists.  Nothing was changed."
$ SAY ""
$ SAY "  To look at it:  $ MCR AUTHORIZE SHOW ''G_USER'"
$ SAY "  To start over:  $ MCR AUTHORIZE REMOVE ''G_USER'   and then run this again."
$ SAY "  (see UNDO below for the home directory)"
$ GOTO UNDO_TEXT
$ !
$FAIL_SUMMARY:
$ FINAL = FAILSTAT
$SUMMARY:
$ SAY ""
$ SAY "=== Summary ==="
$ SAY "  account  ''G_USER'  UIC ''G_UIC'  home ''G_HOME'"
$ SAY "  password: as given (not shown)"
$ SAY "  AUTHORIZE ADD     : ''ST_ADD'"
$ SAY "  hardening MODIFY  : ''ST_HARD'"
$ SAY "  home directory    : ''ST_DIR'"
$ SAY "  LOGIN.COM         : ''ST_LOGIN'"
$UNDO_TEXT:
$ SAY ""
$ SAY "=== To undo, as SYSTEM ==="
$ SAY "  $ MCR AUTHORIZE REMOVE ''G_USER'"
$ SAY "  $ DELETE ''G_HOME'*.*;*"
$ SAY "  $ SET FILE/PROTECTION=(S:RWED,O:RWED) ''G_DEV'[000000]''G_DIR'.DIR"
$ SAY "  $ DELETE ''G_DEV'[000000]''G_DIR'.DIR;1"
$ SAY ""
$ GOTO CLEANUP
$ !
$ ! ----------------------------------------------------- error exits
$NO_UAF:
$ SAY "  ERROR: AUTHORIZE cannot open the system authorization file.  Nothing was changed."
$ SAY "  SYSUAF is: ''UAF_TXT'"
$ SAY "  Look by hand:  $ SHOW LOGICAL SYSUAF   and   $ DIRECTORY SYS$SYSTEM:SYSUAF.DAT"
$ GOTO FAIL
$BAD_USER:
$ SAY "  ERROR: user name must be 1 to 12 letters, digits, $ or _ (got ''G_USER')."
$ GOTO FAIL
$BAD_UIC:
$ SAY "  ERROR: UIC must look like [200,200] with octal numbers (got ''G_UIC')."
$ GOTO FAIL
$BAD_DEV:
$ SAY "  ERROR: device ''G_DEV' is not valid or does not exist."
$ GOTO FAIL
$NO_PW:
$ SAY "  ERROR: no password given and this is not an interactive session."
$ GOTO FAIL
$PW_EOF:
$ SAY ""
$ SAY "  Cancelled at the prompt for the password."
$ GOTO FAIL
$PW_MISMATCH:
$ SAY "  ERROR: the two passwords differ.  Nothing was done."
$ GOTO FAIL
$BAD_PW:
$ SAY "  ERROR: password must be 1 to 32 letters, digits, $ or _ (AUTHORIZE rule)."
$ GOTO FAIL
$ABORTED:
$ SAY ""
$ SAY "  Interrupted (Ctrl/Y).  Cleaning up.  Check what was done with:"
$ SAY "  $ MCR AUTHORIZE SHOW ''G_USER'"
$FAIL:
$ FINAL = FAILSTAT
$ !
$ ! Always: restore terminal and protection, close and delete temp files.
$CLEANUP:
$ IF ECHO_OFF THEN SET TERMINAL/ECHO
$ CLOSE/ERROR=CL_A CRGF
$CL_A:
$ IF PROT_SAVED THEN SET PROTECTION=('OLD_PROT')/DEFAULT
$ IF UAF_DEF THEN DEASSIGN/PROCESS SYSUAF
$ IF RL_DEF THEN DEASSIGN/PROCESS RIGHTSLIST
$ IF F$TYPE(BASE) .EQS. "STRING" THEN DELETE/NOLOG 'BASE'*.TMP;*
$ EXIT FINAL
$ !
$ ! =========================================================== subroutines
$ !
$ ! CHECK_CHARS string allowed-characters min-length max-length
$ ! Exits 1 if STRING is made only of ALLOWED characters and its length is
$ ! within the limits, else 2.  Compare in upper case (callers upcase).
$CHECK_CHARS: SUBROUTINE
$ L = F$LENGTH(P1)
$ MINL = F$INTEGER(P3)
$ MAXL = F$INTEGER(P4)
$ IF L .LT. MINL THEN EXIT %X10000002
$ IF L .GT. MAXL THEN EXIT %X10000002
$ I = 0
$CC_LOOP:
$ IF I .GE. L THEN EXIT 1
$ IF F$LOCATE(F$EXTRACT(I,1,P1),P2) .EQ. F$LENGTH(P2) THEN EXIT %X10000002
$ I = I + 1
$ GOTO CC_LOOP
$ ENDSUBROUTINE
$ !
$ ! HAS_DATA file
$ ! Exits 1 if the file exists and holds at least one record, else fails.
$HAS_DATA: SUBROUTINE
$ SET NOON
$ OPEN/READ/ERROR=HD_NO CRGR 'P1'
$ READ/END_OF_FILE=HD_EMPTY/ERROR=HD_EMPTY CRGR HD_LINE
$ CLOSE CRGR
$ EXIT 1
$HD_EMPTY:
$ CLOSE CRGR
$HD_NO:
$ EXIT %X10000002
$ ENDSUBROUTINE
$ !
$ ! NO_OUTPUT out-file err-file
$ ! Exits 1 if AUTHORIZE wrote nothing at all to either file.  A real run
$ ! always says something (at least a "record updated" or an error), so
$ ! silence means the command or the DEFINE/USER redirection did not work.
$NO_OUTPUT: SUBROUTINE
$ CALL HAS_DATA "''P1'"
$ IF $STATUS THEN EXIT %X10000002
$ CALL HAS_DATA "''P2'"
$ IF $STATUS THEN EXIT %X10000002
$ EXIT 1
$ ENDSUBROUTINE
$ !
$ ! QSEARCH files pattern
$ ! Quiet SEARCH: exits 1 if the pattern is found, and prints no messages.
$QSEARCH: SUBROUTINE
$ DEFINE/USER SYS$OUTPUT NL:
$ DEFINE/USER SYS$ERROR NL:
$ SEARCH 'P1' "''P2'"
$ IF $SEVERITY .EQ. 1 THEN EXIT 1
$ EXIT %X10000002
$ ENDSUBROUTINE
$ !
$ ! RUN_AUTH command-file output-file error-file
$ ! Runs AUTHORIZE with the command file as its input.  Output and error
$ ! messages go to two different files: pointing both at one file name
$ ! would open it twice.
$RUN_AUTH: SUBROUTINE
$ DEFINE/USER SYS$INPUT 'P1'
$ DEFINE/USER SYS$OUTPUT 'P2'
$ DEFINE/USER SYS$ERROR 'P3'
$ 'AUTH_CMD'
$ EXIT 1
$ ENDSUBROUTINE
$ !
$ ! USER_EXISTS user tag
$ ! Exits 1 if AUTHORIZE SHOW finds the user, else fails.  TAG makes the
$ ! temporary file names unique (BASE_<tag>C, O and E .TMP).  Sets the
$ ! global UE_SILENT to 1 when AUTHORIZE printed nothing at all.
$USER_EXISTS: SUBROUTINE
$ SET NOON
$ UE_SILENT == 0
$ UE_NOUAF == 0
$ F_C = BASE + "_" + P2 + "C.TMP"
$ F_O = BASE + "_" + P2 + "O.TMP"
$ F_E = BASE + "_" + P2 + "E.TMP"
$ OPEN/WRITE/ERROR=UE_FAIL CRGF 'F_C'
$ WRITE CRGF "SHOW ''P1'"
$ WRITE CRGF "EXIT"
$ CLOSE CRGF
$ CALL RUN_AUTH "''F_C'" "''F_O'" "''F_E'"
$ CALL NO_OUTPUT "''F_O'" "''F_E'"
$ IF $STATUS THEN UE_SILENT == 1
$ CALL QSEARCH "''F_O',''F_E'" "NAOFIL"
$ IF $STATUS THEN UE_NOUAF == 1
$ CALL QSEARCH "''F_O'" "Username: ''P1' "
$ IF $STATUS THEN EXIT 1
$UE_FAIL:
$ EXIT %X10000002
$ ENDSUBROUTINE
$ !
$ ! MOD_ONE qualifier tag
$ ! Runs one AUTHORIZE MODIFY on the account.  Exits 1 if no error message
$ ! (-E-, -W-, -F-) appears in the output, else shows the output and fails.
$MOD_ONE: SUBROUTINE
$ SET NOON
$ F_C = BASE + "_" + P2 + "C.TMP"
$ F_O = BASE + "_" + P2 + "O.TMP"
$ F_E = BASE + "_" + P2 + "E.TMP"
$ F_OE = F_O + "," + F_E
$ OPEN/WRITE/ERROR=MO_NOFILE CRGF 'F_C'
$ WRITE CRGF "MODIFY ''G_USER' ''P1'"
$ WRITE CRGF "EXIT"
$ CLOSE CRGF
$ CALL RUN_AUTH "''F_C'" "''F_O'" "''F_E'"
$ CALL NO_OUTPUT "''F_O'" "''F_E'"
$ IF $STATUS THEN GOTO MO_SILENT
$ CALL QSEARCH "''F_OE'" "-E-"
$ IF $STATUS THEN GOTO MO_BAD
$ CALL QSEARCH "''F_OE'" "-W-"
$ IF $STATUS THEN GOTO MO_BAD
$ CALL QSEARCH "''F_OE'" "-F-"
$ IF $STATUS THEN GOTO MO_BAD
$ SAY "  MODIFY ''P1' : ok (no error message seen)"
$ EXIT 1
$MO_BAD:
$ SAY "  MODIFY ''P1' : FAILED, AUTHORIZE said:"
$ TYPE 'F_OE'
$ EXIT %X10000002
$MO_SILENT:
$ SAY "  MODIFY ''P1' : AUTHORIZE printed nothing at all, result unknown"
$ EXIT %X10000002
$MO_NOFILE:
$ SAY "  MODIFY ''P1' : FAILED, cannot write the temporary file"
$ EXIT %X10000002
$ ENDSUBROUTINE
