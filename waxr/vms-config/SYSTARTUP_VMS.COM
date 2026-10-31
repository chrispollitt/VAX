$!
$!      SYS$MANAGER:SYSTARTUP_VMS.COM
$!
$! This is the template for the site-specific startup command procedure.
$!
$! As of OpenVMS V7.2, this template is common for OpenVMS Alpha and VAX.
$! Any changes to the template will be made to both systems.
$!
$!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
$!
$! NOTE: On OpenVMS VAX systems, this file replaces the site-specifice
$!       startup procedure, SYS$MANAGER:SYSTARTUP_V5.COM.  Only the name
$!       has been changed, the functionality is the same.
$!       See the documentation for further details .
$!
$!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
$!
$! You may add commands to this procedure or change the commands within this
$! procedure as needed for your system. This command procedure is saved when
$! you upgrade or update to a new version of OpenVMS. Other startup command
$! procedures are replaced with each release of OpenVMS. Place symbol
$! definitions from startup procedures that will be replaced when you upgrade
$! to a new release of OpenVMS in this command procedure. In this way, you can
$! save symbol definitions from one OpenVMS release to the next.
$!
$! When you upgrade your OpenVMS SYSTEM, you should check the new version of
$! SYS$MANAGER:SYSTARTUP_VMS.TEMPLATE for any new or changed commands you
$! may wish to include in your site specific SYS$MANAGER:SYSTARTUP_VMS.COM.
$!
$! As supplied, this command procedure runs correctly on both OpenVMS Alpha
$! and OpenVMS VAX systems.  By testing the symbol ARCH_NAME for "Alpha" or
$! "VAX", you can add commands that will execute only on the specified
$! architecture.  This can allow you to maintain a common SYSTARTUP_VMS.COM
$! in mixed architecure VMSclusters.  Node specific startup commands can be
$! kept in separate files and executed from this procedure by adding commands
$! similar to the following:
$!
$!      $ @SYS$STARTUP:''F$GETSYI("NODENAME")'_STARTUP.COM
$!
$! NOTE: Many command lines are commented out. This allows you to to decide
$! which commands are executed, and how some commands are to be executed.
$! Also note that these lines begin with the "$!$" character sequence.
$! Remove the first two characters "$!" if you wish to have one of these
$! commands executed.
$!
$! Pay close attention to whether any of these commands are continued on the
$! next line.  Continued lines have a hyphen at end of line.  If you remove
$!  the "$!" from any line that is continued, you must also remove the "$!"
$! from the next line.
$!
$! In some cases a command may be continued on two or more additional lines;
$! remove the "$!"  characters  from the start of all additional lines.
$! Continuation lines do not start with a "$".
$! The final continuation line does not end with a hyphen.
$!
$! --------------------------------
$!
$! On OpenVMS VAX systems, the logical name SYS$MICROVAX is defined as true
$! ("1") if the system is a MicroVAX system and it is not in a VMScluster;
$! otherwise the logical name is defined as false ("0").
$!
$! On OpenVMS Alpha systems, the logical name SYS$MICROVAX is not defined.
$!
$! Create the symbol MICROVAX based on the logical name SYS$MICROVAX.
$! NOTE: On OpenVMS Alpha this symbol will always be false, because
$!       SYS$MICROVAX is not defined.
$ IF F$TRNLNM("SYS$MICROVAX")
$ THEN  MICROVAX = "1"
$ ELSE  MICROVAX = "0"
$ ENDIF
$!
$! Create the symbol ARCH_NAME to indicate "Alpha" or "VAX"
$ ARCH_NAME = F$GETSYI("ARCH_NAME")
$!
$!
$ WRITE SYS$OUTPUT ""
$ WRITE SYS$OUTPUT "The OpenVMS ''ARCH_NAME' system is now executing the site-specific startup commands."
$ WRITE SYS$OUTPUT ""
$!
$! MOUNT DRIVES
$ mount/system dua1 data1
$! mount/system dua2 data2
$
$! OPCOM is started by default on all OpenVMS systems. However, by default,
$! operators will not be able to satisfy user mount requests. To allow
$! operators to satisfy user mount requests, edit the SYS$MANAGER:SYLOGIN
$! command procedure by removing the command line that equates MOUNT to
$! MOUNT/NOASSIST.
$!
$!
$! The following commands install the secondary page file, if it exists.
$! (Note that the secondary swap file is installed by the command procedure
$! SYS$SYSTEM:STARTUP.COM if it exists.)
$!
$ IF F$SEARCH("SYS$SYSROOT:[SYSEXE]PAGEFILE1.SYS") .NES. ""
$ THEN  SYSGEN = "$SYSGEN"
$       SYSGEN INSTALL SYS$SYSROOT:[SYSEXE]PAGEFILE1.SYS /PAGEFILE /NOCHECK
$ ENDIF
$!
$!
$! The following commands turn off account logging and delete the account log
$! on MicroVAX, non VMScluster systems.  If you wish to keep an account log on
$! such a system, delete the following 6 command lines.
$!
$ IF MICROVAX
$ THEN
$   SET ACCOUNTING/DISABLE
$   IF F$SEARCH("SYS$MANAGER:ACCOUNTNG.DAT") .NES. "" THEN -
        DELETE SYS$MANAGER:ACCOUNTNG.DAT;*
$ ENDIF
$!
$!
$! The following commands purge the operator and network logs to two versions
$! on MicroVAX, non VMScluster systems.  If you do NOT wish to purge these
$! log files, delete the following 7 command lines.
$!
$ IF MICROVAX
$ THEN
$   IF F$SEARCH("SYS$MANAGER:OPERATOR.LOG;-1") .NES. "" THEN -
        PURGE SYS$MANAGER:OPERATOR.LOG
$   IF F$SEARCH("SYS$MANAGER:EVL.LOG;-1") .NES. "" THEN -
        PURGE SYS$MANAGER:EVL.LOG
$ ENDIF
$!
$!
$! To set up virtual terminals on OpenVMS Alpha systems only, remove the
$! comment delimiter ($!) from the SYSMAINIO CONNECT line below.
$!
$ IF ARCH_NAME .EQS. "Alpha"
$ THEN  SYSMANIO = "$SYSMAN IO"
$!$     SYSMANIO CONNECT VTA0/NOADAPTER/DRIVER=SYS$LOADABLE_IMAGES:SYS$TTDRIVER.EXE
$ ENDIF
$!
$! To set up virtual terminals on OpenVMS VAX systems only, remove the
$! comment delimiter ($!) from the SYSGEN CONNECT line below.
$!
$ IF ARCH_NAME .EQS. "VAX"
$ THEN  SYSGEN = "$SYSGEN"
$!$     SYSGEN CONNECT VTA0 /NOADAPTER /DRIVER=TTDRIVER
$ ENDIF
$!
$!
$! This command defines a system-wide login command procedure for all users.
$!
$ DEFINE /SYSTEM /EXEC SYS$SYLOGIN SYS$MANAGER:SYLOGIN
$!
$!
$! This command defines a message to be displayed before each user logs in.
$!
$ DEFINE /SYSTEM SYS$ANNOUNCE " Welcome to OpenVMS (TM) ''ARCH_NAME' Operating System, Version ''F$GETSYI("VERSION")'"
$!
$!
$! This command defines a message or file to be displayed after each user logs in.
$!
$!$ DEFINE /SYSTEM SYS$WELCOME "@SYS$MANAGER:WELCOME.TXT"
$!
$!
$! Set up date/time format.
$!
$! OpenVMS contains support for date and time formats other than the standard
$! default format.  This allows applications as well as some OpenVMS utilities
$! to use formats other than the standard format by calling LIB$ routines such
$! as LIB$FORMAT_DATE_TIME.  To enable this feature, delete the comment
$! characters from the following line.
$!
$!$ @SYS$STARTUP:LIB$DT_STARTUP
$!
$! To define a system-wide default date and time format other than the standard
$! OpenVMS format, delete the comment characters from the following line and
$! modify the logical definition to specify the format you want to use.
$! Note that each user may override this logical with a process specific
$! logical definition to specify a specific format for their process.
$! See the OpenVMS documentation for further information.
$!
$!$ DEFINE/SYSTEM LIB$DT_FORMAT LIB$DATE_FORMAT_012, LIB$TIME_FORMAT_011
$!
$!
$! On OpenVMS Alpha systems only, start the POWER_MONITOR process for systems
$! with power monitoring capabilities.  If you do NOT want to start the
$! POWER_MONITOR process, add a ($!) comment delimiter.
$ IF ARCH_NAME .EQS. "Alpha" THEN @SYS$STARTUP:SYS$POWER_MONITOR_STARTUP.COM
$!
$!
$! On OpenVMS Alpha systems only, start the SMHANDLER driver and process for
$! systems with environmental monitoring capabilities.  If you do NOT want
$! to start the SMHANDLER driver and process, add a ($!) comment delimiter.
$!
$ IF ARCH_NAME .EQS. "Alpha" THEN $@SYS$STARTUP:SYS$SMHANDLER_STARTUP.COM
$!
$!
$! Set up the queue manager.
$!
$! The queue manager is normally enabled by default.  If this is an initial
$! installation, the queue files containing the queues, forms, etc.
$! do not yet exist.  You may use the command START/QUEUE/MANAGER/NEW
$! from an interactive terminal to create these files.  NOTE: This command only
$! needs to be done ONCE for a new OpenVMS installation.  It should NOT be
$! placed in this file since it would then execute each time the system is
$! booted, creating new queue files each time.  This will cause all current
$! jobs, queues, forms, etc. to be lost.
$!
$! By default the queue files are created in SYS$COMMON:[SYSEXE].
$! To place the queue files on a disk other than the system disk you should
$! define the logical QMAN$MASTER in SYS$MANAGER:SYLOGICALS.COM to the device
$! and directory to contain the queue files.
$!
$! Once the queue files have been created you may use the INITIALIZE/QUEUE
$! command from an interactive terminal to create the necessary queues.
$! The START/QUEUE command should then be added to this file for any
$! queues that are not AUTOSTART queues.
$! See the OpenVMS documentation for further information.
$!
$ START/QUEUE/MANAGER
$!
$! Set up a print queue.
$!
$! Choose the device you will use for printing. Define the logical name
$! $PRINTER to name the device you will use for printing; either remove the
$! comment delimiter ($!) from one of the following commands or add a command
$! in the following format.
$!
$!$ DEFINE /SYSTEM $PRINTER  $TERMINAL0 ! if a hard copy terminal is the printer
$!$ DEFINE /SYSTEM $PRINTER  _LPA0:     ! if using a line printer
$!
$!
$! If you will use a line printer, set the printer characteristics.
$! Delete the comment characters from the following line.
$!
$!$ SET PRINTER /NOWRAP /NOTRUNCATE /CR $PRINTER
$!
$!
$! If you will use a hard copy terminal as the print device, set the terminal
$! characteristics. The following terminal characteristics vary from one
$! hard copy terminal to another: speed, width, length, and device type.
$! If your terminal is an LA100, remove the comment delimiter ($!) from the
$! following command lines. If your terminal is not an LA100, add a command in
$! the following format.
$!
$!$ SET TERMINAL $PRINTER /PERMANENT /NOBROADCAST /NOTYPEAHEAD /NOWRAP -
$!      /SPEED=(1200) /WIDTH=(132) /PAGE=(66) /DEVICE_TYPE=(LA100)
$!
$!
$! To set your printing device as spooled to the queue SYS$PRINT,
$! remove the comment delimiter ($!) in the following command line.
$!
$!$ SET DEVICE /SPOOLED=(SYS$PRINT, SYS$SYSDEVICE:) $PRINTER
$!
$!
$! The following command will enable autostart queues to start on this
$! node.  To enable autostart during startup, remove the comment
$! delimiter ($!) from the following command line.
$!
$! Make sure resources required by all autostart queues are available,
$! such as disks and printing devices.
$!
$!$ ENABLE AUTOSTART /QUEUES
$!
$!
$! If your SYS$PRINT queue is not an autostart queue, then remove the comment
$! delimiter ($!) from the following command to start the queue.
$!
$!$ START /QUEUE SYS$PRINT
$!
$!
$! To start a batch queue, remove the comment delimiter ($!) from the
$! following command line.
$!
$ START /QUEUE SYS$BATCH
$!
$!
$! In order to use asynchronous DECnet Phase IV on OpenVMS VAX systems only,
$! remove the comment delimiter ($!) from the next two lines.
$! Change the SET TERMINAL command to specify the  terminal line you will use.
$! (Reminder: To set the terminal line characteristics for the other side of
$! the asynchronous connection, enter a SET TERMINAL command on the routing
$! node to which you are connecting.)
$! (For similar functionality on OpenVMS Alpha or with DECnet-Plus (DECnet OSI)
$! consider using the PPP feature in DIGITAL TCP/IP Services.)
$!
$!$ IF ARCH_NAME .EQS. "VAX" THEN -
$!       SET TERMINAL $TERMINAL1 /PERMANENT /NOAUTOBAUD /SPEED=9600 /PROTOCOL=DDCMP
$!
$!
$! Detect which DECnet version (if any) has been installed
$!
$ DECNET_VERSION        = F$INTEGER(F$EXTRACT(2,2,F$GETSYI("DECNET_VERSION")))
$ DECNET_PLUS_INSTALLED = (DECNET_VERSION .GE. 5) .AND. -
                          (F$SEARCH("SYS$SYSTEM:NET$ACP.EXE") .NES. "")
$ DECNET_IV_INSTALLED   = (DECNET_VERSION .EQ. 4) .AND. -
                          (F$SEARCH("SYS$SYSTEM:NETACP.EXE") .NES. "")
$ DECNET_NOT_INSTALLED  = .NOT. (DECNET_PLUS_INSTALLED .OR. DECNET_IV_INSTALLED)
$!
$ IF (DECNET_IV_INSTALLED)
$ THEN
$!
$! Following are the commands that start up the DECnet Phase IV network, if you
$! are using the DECnet Phase IV software. Note that only one of these
$! commands is needed to start the network, the other should be commented out.
$! Configure the network and define the other node names before starting up
$! DECnet; otherwise you will get error messages stating that the database is
$! not initialized.
$!
$! NOTE:  If you are running DECnet-Plus, it was started when
$!        VMS$BASEENVIRON-050_VMS.COM executed during STARTUP.COM.
$!        If this is not desired, the logical NET$IGNORE_DECNET has been
$!        provided for this purpose.  Please see the DECnet-Plus
$!        installation and configuration manuals for further details.
$!
$! If you have batch queues set up on your system, remove the
$! comment delimiter ($!) from the command line below. This
$! allows the system to startup more quickly, and decreases the amount of
$! time you must wait to log in.
$!
$! SUBMIT SYS$MANAGER:STARTNET.COM
$!
$!
$! If you do not have batch queues set up on your system, remove the comment
$! delimiter ($!) from the next line.  (Note that networks have already been
$! registered; SYS$STARTUP:SYS$NET_SERVICES.COM was executed when
$! VMS$BASEENVIRON-050_VMS.COM was executed during STARTUP.COM.)
$!
$!$ START/NETWORK DECNET
$!
$ ENDIF
$!
$!
$! The following command should be used only if you do not wish the DECwindows
$! startup file to be run.  The DECwindows startup file should be run on all
$! types of machines, even if they are not using a DECwindows display.  If
$! you wish to run the DECwindows startup file at a later time during system
$! startup remove the comment delimiter ($!) from the line below.
$!
$!$ DEFINE DECW$IGNORE_DECWINDOWS TRUE
$!
$!
$! On OpenVMS Alpha systems, defining DECW$IGNORE_SHARE_ADDRESS turns off
$! the shared linkage section option for DECwindows startup. Shared linkage
$! section is on by default with OpenVMS Alpha V6.2 and above. Shared linkage
$! section reduces memory requirements and improves performance, but it means
$! that DECwindows images can't be replaced without rebooting the system.
$!
$! On OpenVMS VAX systems, defining DECW$IGNORE_SHARE_ADDRESS does nothing.
$!
$!$ IF ARCH_NAME .EQS. "Alpha" THEN -
$!       DEFINE/SYSTEM/EXEC DECW$IGNORE_SHARE_ADDRESS TRUE
$!
$!
$! Following are the command(s) required to start TCP/IP Networking on
$! your system.  These require that you have one of the TCP/IP for
$! OpenVMS products installed (please see the TCP/IP Networking on
$! OpenVMS manual for vendor information).
$!
$! NOTE: You cannot run more than one of the following TCP/IP products.
$!
$!
$! Remove the comment delimiter ($!) from the following line to start
$! versions of Digital TCP/IP Services for OpenVMS below V5.0
$!                                
$!$ @SYS$STARTUP:UCX$STARTUP.COM
$!
$! Remove the comment delimiter ($!) from the following line to start
$! versions of Digital TCP/IP Services for OpenVMS beginning with V5.0.
$!                                
$! @SYS$STARTUP:TCPIP$STARTUP.COM  <-- OLD
$  @SYS$SYSROOT:[TCPWARE]TCPWARE_LOGICALS
$  @TCPWARE:STARTNET
$!
$!
$! Remove the comment delimiter ($!) from the following line to start
$! TGV MultiNet.
$!
$!$ @SYS$SYSROOT:[MULTINET]START_MULTINET.COM
$!
$!
$! Remove the comdment delimiter ($!) from the following line to start
$! Process Software TCPware.
$!
$!$ @SYS$SYSROOT:[TCPWARE]TCPWARE_LOGICALS.COM
$!$ @TCPWARE:STARTNET.COM
$!
$!
$! Edit and Remove the comment delimiter ($!)  from the following lines
$! to start Wollongong PathWay.
$!$ FILE = F$SEARCH("SYS$DISK:[NETWORKS.PATHWAY.NETDIST.MISC]STARTINET.COM")
$!$ IF FILE .NES. ""
$!$ THEN
$!$       @'FILE'
$!$       IF F$SEARCH("TWG$SPECIFIC:[NETDIST.PONY.HQ]PONYSTART.COM") .NES. ""
$!$         THEN
$!$              PONY$DISK = (F$TRNLNM("TWG$SPECIFIC") - "]") + "NETDIST.PONY.]"
$!$              DEFINE/SYSTEM/EXEC/TRANS=CONC PONY$DISK 'PONY$DISK
$!$              @PONY$DISK:[HQ]PONYSTART
$!$       ENDIF
$!$ ENDIF
$!
$!
$! To start the OpenVMS Management Station server application, remove the
$! the comment delimiter ($!) from the command line below.
$!
$!$ @SYS$STARTUP:TNT$STARTUP
$!
$!
$! Remove the comment delimiter ($!) from the following line to have
$! Monitor run with TCP/IP.
$!
$!$ @SYS$STARTUP:VPM$STARTUP.COM
$!
$!
$! Remove the comment delimiter ($!) from the following line to start
$! RPC services.
$!
$!$ @SYS$STARTUP:DCE$RPC_STARTUP.COM
$!
$!@SYS$STARTUP:NETLIB_STARTUP  <-- OLD
$! Start http server (the DEC C one, HTTPD.EXE; the old Perl one failed because hostname() is cpvax.lan)
$ @CPVAX$DUA1:[LIGHTTPD.BIN]START_HTTPD
$!$ submit /name=httpd_vax /log_file=cpvax$dua1:[lighttpd.log]httpd_vax.log cpvax$dua1:[lighttpd.bin]httpd_vax  <-- OLD
$!
$!
$! Start Rdb: the monitor, and the protected images (RDMSHRP.EXE) that SQL$ and WAXR need.  Nothing else starts it, and
$! without it WAXR fails with %RDB-E-UNAVAILABLE2 / %SYSTEM-F-PROTINSTALL.  Added 29-OCT-2026.
$ IF F$SEARCH("SYS$STARTUP:RMONSTART.COM") .NES. "" THEN @SYS$STARTUP:RMONSTART
$!
$! Exit
$ EXIT
