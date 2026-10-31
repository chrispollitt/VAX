$! STATUS.COM - CGI (DCL) behind status.html: what this system is doing, as plain text, one fact per line.
$!   key=value                     single facts (node, version, boot, now, memory ...)
$!   disk=dev|label|free|size|trans|errors      proc=pid|name|user|state|pri|cpu(10 ms)|mode|io|started
$!   net=local|foreign|state       conf=name|value
$! status.html asks for it every few seconds and draws the page; open /status.com to see the raw lines.
$! Read-only: it changes nothing on the system.  The last line is end=1 (so a cut-off answer can be spotted).
$ SET NOON
$ SET NOVERIFY
$ PID = F$GETJPI("","PID")
$ TMP = F$TRNLNM("HTTPD_TMP")
$ IF TMP .EQS. "" THEN TMP = "SYS$SCRATCH:"
$ F1 = TMP + "STATUS_" + PID + ".TMP"
$!
$ WRITE SYS$OUTPUT "Content-Type: text/plain"
$ WRITE SYS$OUTPUT "Cache-Control: no-store"
$ WRITE SYS$OUTPUT ""
$!
$! --- the system ---
$ WRITE SYS$OUTPUT "node=" + F$GETSYI("NODENAME")
$ WRITE SYS$OUTPUT "domain=" + F$TRNLNM("TCPWARE_DOMAINNAME")
$ WRITE SYS$OUTPUT "hw=" + F$EDIT(F$GETSYI("HW_NAME"),"TRIM")
$ WRITE SYS$OUTPUT "version=" + F$EDIT(F$GETSYI("VERSION"),"TRIM")
$ WRITE SYS$OUTPUT "boot=" + F$GETSYI("BOOTTIME")
$ WRITE SYS$OUTPUT "now=" + F$TIME()
$ WRITE SYS$OUTPUT "cpus=" + F$STRING(F$GETSYI("ACTIVECPU_CNT"))
$ WRITE SYS$OUTPUT "pagefile_total=" + F$STRING(F$GETSYI("PAGEFILE_PAGE"))
$ WRITE SYS$OUTPUT "pagefile_free=" + F$STRING(F$GETSYI("PAGEFILE_FREE"))
$ WRITE SYS$OUTPUT "swapfile_total=" + F$STRING(F$GETSYI("SWAPFILE_PAGE"))
$ WRITE SYS$OUTPUT "swapfile_free=" + F$STRING(F$GETSYI("SWAPFILE_FREE"))
$!
$! --- physical memory, in 512-byte pages: the "Main Memory" line of SHOW MEMORY ---
$! (not piped through SEARCH SYS$INPUT: SYS$INPUT is the request body here)
$ PIPE SHOW MEMORY/PHYSICAL > 'F1'
$ OPEN/READ/ERROR=NOMEM IN 'F1'
$MLOOP:
$ READ/END_OF_FILE=MEMCLOSE IN LINE
$ IF F$LOCATE("Main Memory",LINE) .EQ. F$LENGTH(LINE) THEN GOTO MLOOP
$ LINE = F$EDIT(LINE,"COMPRESS,TRIM")
$ WRITE SYS$OUTPUT "mem_total=" + F$ELEMENT(3," ",LINE)
$ WRITE SYS$OUTPUT "mem_free=" + F$ELEMENT(4," ",LINE)
$ WRITE SYS$OUTPUT "mem_used=" + F$ELEMENT(5," ",LINE)
$ WRITE SYS$OUTPUT "mem_modified=" + F$ELEMENT(6," ",LINE)
$MEMCLOSE:
$ CLOSE IN
$NOMEM:
$ DELETE/NOLOG 'F1';*
$!
$! --- mounted disks ---
$ DEV = F$DEVICE("*","DISK")
$DLOOP:
$ IF DEV .EQS. "" THEN GOTO DDONE
$ IF F$GETDVI(DEV,"MNT")
$ THEN
$    D = F$GETDVI(DEV,"DEVNAM") + "|" + F$GETDVI(DEV,"VOLNAM")
$    D = D + "|" + F$STRING(F$GETDVI(DEV,"FREEBLOCKS")) + "|" + F$STRING(F$GETDVI(DEV,"MAXBLOCK"))
$    D = D + "|" + F$STRING(F$GETDVI(DEV,"TRANSCNT")) + "|" + F$STRING(F$GETDVI(DEV,"ERRCNT"))
$    WRITE SYS$OUTPUT "disk=" + D
$ ENDIF
$ DEV = F$DEVICE("*","DISK")
$ GOTO DLOOP
$DDONE:
$!
$! --- every process ---
$ CTX = ""
$PLOOP:
$ P = F$PID(CTX)
$ IF P .EQS. "" THEN GOTO PDONE
$ L = P + "|" + F$GETJPI(P,"PRCNAM") + "|" + F$GETJPI(P,"USERNAME") + "|" + F$GETJPI(P,"STATE")
$ L = L + "|" + F$STRING(F$GETJPI(P,"PRI")) + "|" + F$STRING(F$GETJPI(P,"CPUTIM")) + "|" + F$GETJPI(P,"MODE")
$ L = L + "|" + F$STRING(F$GETJPI(P,"DIRIO") + F$GETJPI(P,"BUFIO")) + "|" + F$GETJPI(P,"LOGINTIM")
$ WRITE SYS$OUTPUT "proc=" + F$EDIT(L,"TRIM")
$ GOTO PLOOP
$PDONE:
$!
$! --- TCP/IP: the servers listening and the connections open (TCPware's NETSTAT) ---
$ PIPE @TCPWARE:NETSTAT -a > 'F1'
$ OPEN/READ/ERROR=NONET IN 'F1'
$NLOOP:
$ READ/END_OF_FILE=NETCLOSE IN LINE
$ LINE = F$EDIT(LINE,"COMPRESS,TRIM")
$ ID = F$ELEMENT(0," ",LINE)
$ IF F$EXTRACT(0,3,ID) .NES. "INE" .AND. F$EXTRACT(0,2,ID) .NES. "BG" .AND. F$EXTRACT(0,3,ID) .NES. "UDP" THEN GOTO NLOOP
$ ST = F$ELEMENT(5," ",LINE)
$ IF ST .EQS. " " THEN ST = ""
$ WRITE SYS$OUTPUT "net=" + F$ELEMENT(3," ",LINE) + "|" + F$ELEMENT(4," ",LINE) + "|" + ST
$ GOTO NLOOP
$NETCLOSE:
$ CLOSE IN
$NONET:
$ DELETE/NOLOG 'F1';*
$!
$! --- how the web server is set up ---
$ N = 0
$CLOOP:
$ NAME = F$ELEMENT(N,",","PORT,ROOT,USERDIR,TMP,CGI,PERL,KEEP")
$ IF NAME .EQS. "," THEN GOTO CDONE
$ WRITE SYS$OUTPUT "conf=HTTPD_" + NAME + "|" + F$TRNLNM("HTTPD_" + NAME)
$ N = N + 1
$ GOTO CLOOP
$CDONE:
$ WRITE SYS$OUTPUT "end=1"
$ EXIT
