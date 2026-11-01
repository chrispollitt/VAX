$! KEEP_NET_ALIVE.COM
$!
$! Purpose : Periodically ping a remote host to generate network traffic
$!           and help prevent an "idle network" autoshutdown.
$!
$! P1 = remote host or IP address  (required)
$! P2 = wait interval, OpenVMS delta time  (optional; default 00:05:00)
$!
$! Example:
$!   $ SUBMIT KEEP_NET_ALIVE.COM /PARAM=("192.0.2.10","00:05:00")
$!
$ IF P1 .EQS. "" THEN GOTO usage
$ HOST = P1
$
$ INTERVAL = "00:05:00"
$ IF P2 .NES. "" THEN INTERVAL = P2
$
$! cpvax runs TCPware, so use its PING.  Do not use
$! SYS$MANAGER:TCPIP$DEFINE_COMMANDS: that points PING at the HP TCP/IP
$! Services image, whose stack is not running, and it fails with
$! "IP_OPTIONS: invalid argument" and %SYSTEM-F-NOPRIV even for SYSTEM.
$! TCPWARE_COMMANDS.COM leaves PING commented out, so define it here.
$ PING :== $TCPWARE:PING
$
$! A failed ping must not terminate the loop.
$ ON ERROR THEN CONTINUE
$ ON CONTROL_Y THEN GOTO done
$
$loop:
$ WRITE SYS$OUTPUT F$TIME(), "  pinging ", HOST
$! TCPware syntax: ping host [data-size] [npackets]  (no -c; one packet)
$ PING 'HOST' 56 1
$ WAIT 'INTERVAL'
$ GOTO loop
$
$done:
$ WRITE SYS$OUTPUT "KEEP_NET_ALIVE stopped."
$ EXIT
$
$usage:
$ WRITE SYS$OUTPUT "Usage: @KEEP_NET_ALIVE HOST [INTERVAL]"
$ WRITE SYS$OUTPUT "Example: @KEEP_NET_ALIVE 192.0.2.10 00:05:00"
$ EXIT