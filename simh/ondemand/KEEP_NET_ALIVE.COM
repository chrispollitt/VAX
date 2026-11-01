$! KEEP_NET_ALIVE.COM
$!
$! Purpose : Periodically ping a remote host to generate network traffic
$!           and keep the cpbee idle shutdown (vax-ctl) from firing.
$!
$! vax-ctl samples the bytes crossing vaxtap once a minute and counts the
$! VAX as busy when a sample is above NET_BYTES_PER_MIN_MAX (1500); one busy
$! sample restarts its IDLE_MINUTES (30) clock.  A default 56-byte ping is only
$! ~220 bytes, so each round sends a few near-full-size packets (~2.9 KB per
$! round trip at 1400 bytes), which clears the threshold even when the burst
$! straddles two sampling minutes.
$!
$! P1 = remote host or IP address  (required)
$! P2 = wait interval, OpenVMS delta time  (optional; default 00:05:00,
$!      must stay well under IDLE_MINUTES)
$! P3 = ping data size in bytes  (optional; default 1400, max 1472 to avoid
$!      fragmenting a 1500-byte MTU)
$! P4 = packets per round  (optional; default 3, one per second)
$!
$! Example:
$!   $ SUBMIT KEEP_NET_ALIVE.COM /PARAM=("cpbee.cmnet","00:05:00")
$!
$ IF P1 .EQS. "" THEN GOTO usage
$ HOST = P1
$
$ INTERVAL = "00:05:00"
$ IF P2 .NES. "" THEN INTERVAL = P2
$ SIZE = "1400"
$ IF P3 .NES. "" THEN SIZE = P3
$ COUNT = "3"
$ IF P4 .NES. "" THEN COUNT = P4
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
$! TCPware syntax: ping host [data-size] [npackets]  (no -c)
$ PING 'HOST' 'SIZE' 'COUNT'
$ WAIT 'INTERVAL'
$ GOTO loop
$
$done:
$ WRITE SYS$OUTPUT "KEEP_NET_ALIVE stopped."
$ EXIT
$
$usage:
$ WRITE SYS$OUTPUT "Usage: @KEEP_NET_ALIVE HOST [INTERVAL [SIZE [COUNT]]]"
$ WRITE SYS$OUTPUT "Example: @KEEP_NET_ALIVE cpbee.cmnet 00:05:00 1400 3"
$ EXIT