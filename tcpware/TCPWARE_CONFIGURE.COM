$!
$!        TCPware(R) for OpenVMS Configuration File
$!        Software configuration data written on 10-OCT-2026 20:56:32.05.
$!
$!        Do *NOT* edit this file.  Use the TCPWARE:CNFNET.COM
$!        utility to change your configuration.
$!
$ NETCU_MAS_NUMBER   == "12345"
$ NETCU_LINES     == "LPB-0 127.0.0.1,QNA-0 192.168.20.30 /MASK=255.255.255.0 /"
$ NETCU_LINES     == NETCU_LINES+"FLAGS=(NOTRAILERS)"
$ NETCU_GATEWAY   == "192.168.20.1"
$ NETCU_TIMEZONE  == "-0700"
$ NETCU_TIMEZONE_NAME == ""
$ NETCU_TIMEZONE_RULES == ""
$ NETCU_DOMAIN    == "cpvax.cmnet"
$! *** DHCP4 parameters ***
$ DHCP4_SERVERS           == 0
$! *** DHCP parameters ***
$ DHCP_SERVERS           == 0
$! *** Domain Name Services parameters ***
$ NAMED_SERVERS          == "192.168.20.1"
$ CLUSTER_NAMES            == ""
$ DOMAIN_LIST            == "cmnet"
$ NDOTS_STR              == ""
$ NAMED_SVR_TYPE         == ""
$! *** FTP-OpenVMS parameters ***
$ FTP_SERVERS == 1
$ FTP_CLIENT == "YES"
$! *** GateD parameters ***
$ GATED_ENABLE           == 0
$! *** IMAP-OpenVMS Parameters ***
$ IMAP_ENABLE            == 0
$ IMAP_LOGLEVEL          == 0
$ IMAP_LOGFILE           == "TCPWARE_SPECIFIC:[TCPWARE]IMAPSERVER.LOG"
$ IMAP_USER              == "SYSTEM"
$ IMAP_FULLCACHE         == "NO"
$! *** IPP parameters ***
$ IPP_ENABLE       == "0"
$ IPP_DOC_FORMAT   == "text/plain"
$ IPP_RETRY_DELAY  == "0 00:10:00.00"
$ IPP_LOG_BYTES    == "-1"
$ IPP_MAX_STREAMS  == "16"
$ IPP_LOG_LEVEL    == "JOB_TRACE"
$ IPP_OPCOM_LEVEL  == "INFO"
$ IPP_OPCOM_TERM   == "PRINTER"
$ IPP_AUTOSTART    == "NO"
$ IPP_AUTOSTOP     == "NO"
$! *** TCPware IPS parameters ***
$ IPS_ENABLE == 0
$ IPS_MSGS == 400
$ IPS_TQELM == 500
$ IPS_ASTLM == 500
$! *** LPS parameters ***
$ LPR_PRINTER            == "lp@192.168.10.66"
$ LPR_SPOOL              == "TCPWARE_SPECIFIC:[TCPWARE.LPS_SPOOL]"
$ LPR_BATCH              == ""
$! *** Miscellaneous parameters ***
$ TFTP_SERVERS           == 0
$ TFTP_ROOT              == ""
$ CHARGEN_SERVERS        == 0
$ DAYTIME_SERVERS        == 0
$ DISCARD_SERVERS        == 0
$ ECHO_SERVERS           == 0
$ QUOTE_SERVERS          == 0
$ AUTH_SERVERS           == 0
$ TIME_SERVERS           == 0
$! *** NTP parameters ***
$ NTP_ENABLE             == 0
$ NTP_WAYTOOBIG          == 4000
$! *** POP3-OpenVms Parameters ***
$ POP3_ENABLE            == 0
$! *** PWIPDRIVER parameters ***
$ PWIP_ENABLE            == 0
$! *** Berkeley R Command parameters ***
$ RCMD_CLIENTS           == ""
$ RCMD_SERVICES          == ""
$! *** SMTP-OpenVMS parameters ***
$ SMTP_ENABLE            == 0
$ SMTP_STATISTICS        == "NO"
$ SMTP_ACCOUNTING        == "NO"
$ SMTP_PORT	== 25
$! *** SNMP agent parameters ***
$ SNMP_SERVERS           == 1
$ SNMP_SMUX_SERVERS      == 0
$ SNMP_AGENTX_SERVERS      == 0
$! *** SSH OpenVMS parameters ***
$ SSH_SERVERS == 0
$ ENABLE_SSH1 == 0
$ ENABLE_SSH2 == 0
$ SSH_VERBOSE == 0
$ SSH_QUIET == 0
$ SSH_PORT == 22
$ SSH_LISTEN_ADDRESS == ""
$ SSH_LOGIN_GRACE_TIME == ""
$ SSH_KEY_REGEN_TIME == 0
$ ALT_SSH1_HOST == ""
$ SSH_DEBUG_LEVEL == 0
$ ALT_SSH2_CONFIG == ""
$ ALT_SSH1_CONFIG == ""
$ SSH_BITS == 768
$ SSH_ALLOW_EXPIRED_PW == 0
$ SSH_ALLOW_PREEXPIRED_PW == 0
$ SSH_DISPLAY_SYSANNOUNCE == 0
$ SSH_KEYGEN_MIN_PW_LEN == 0
$ SSH_KEYGEN2_MIN_PW_LEN == 0
$ SSH_USE_SYSGEN_LGI == 0
$ SSH_MAX_SESSIONS == 1000
$ SSH_LOG_REJECTS == 0
$ SSH_LOG_ACCEPTS == 0
$ SSH_LOGFILE == ""
$! *** TALK-OpenVMS parameters ***
$ TALKD_ENABLE           == 0
$! *** TELNET-OpenVMS parameters ***
$ TELNET_SERVERS         == 1
$! *** TIMED parameters ***
$ TIMED_ENABLE           == 0
$! End of configuration file
