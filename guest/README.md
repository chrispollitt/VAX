# guest - a shared GUEST account for the VAX

`CREATE_GUEST.COM` creates an unprivileged, shared visitor account on OpenVMS VAX V7.3
(cpvax), with a home directory and a small `LOGIN.COM`. Visitors reach it from the web
terminals (a VT100 login over telnet) with the user name and the shared password.

> **Not run yet.** There was no OpenVMS system to test on when this was written (the VAX
> was not booting, and there is no VMS interpreter on the dev machine), so this procedure
> has **never been executed**. It prints every step as it goes so the first real run is
> easy to follow. Read the "Unverified" list below and watch those spots.

## Use

Get `CREATE_GUEST.COM` onto the VAX in **ASCII** mode (FTP `ascii`, or paste). The TCPware
FTP transfer hung in active mode on the first try; use **passive** mode (`passive` at the
`ftp>` prompt). Then, logged in as SYSTEM:

```
$ @CREATE_GUEST [user] [password] [uic] [device]
```

| Parameter | Default | Notes |
|-----------|---------|-------|
| `user`     | `GUEST`            | 1-12 of A-Z 0-9 `$` `_`; the home directory is `[user]` |
| `password` | prompted for       | asked twice, not echoed; letters, digits, `$`, `_`, up to 32; upcased |
| `uic`      | `[200,200]`        | octal `[group,member]`; pick one nobody else uses |
| `device`   | `SYS$SYSDEVICE:`   | where the home directory goes |

The password is a shared visitor password, not a secret, but the procedure still never
prints it. It does sit in a temporary command file in `SYS$SCRATCH` while AUTHORIZE reads
it; that file is protected against group and world and deleted afterwards.

Running it again is harmless: if the account already exists it says so and changes nothing.

## What it does

1. Checks for SYSPRV and validates the parameters (user, password, UIC, device).
2. Looks for an existing account (`AUTHORIZE SHOW`, output to a temp file, `SEARCH`).
3. `ADD` with the core qualifiers: `/PASSWORD /OWNER /UIC /DEVICE /DIRECTORY
   /PRIVILEGES=(TMPMBX,NETMBX) /DEFPRIVILEGES=(TMPMBX,NETMBX) /FLAGS=(LOCKPWD)`. Success is
   judged by asking AUTHORIZE whether the account is there afterwards.
4. Hardening, **one `MODIFY` run per qualifier**, so an unsupported one is reported and
   cannot stop the account being created: `/NOPWDEXPIRED /PWDLIFETIME=NONE /NOEXPIRATION
   /ACCOUNT=GUEST /MAXJOBS=4 /PRCLM=3 /FLAGS=(DISMAIL) /NOBATCH`.
5. `CREATE/DIRECTORY` the home directory, owned by the account, no group or world access.
6. Writes a minimal `LOGIN.COM` there: `SET TERMINAL/INQUIRE`, a prompt, a welcome message,
   and commented-out `ARTY :==` / `LIFE :==` lines in the form `BUILD_ARTY.COM` and
   `BUILD_LIFE.COM` use. Edit the device and directory in those lines to where the
   `.EXE` files really are, then remove the leading `!`. The file is owned by the account but
   read-only for it.
7. Shows the account record as AUTHORIZE now holds it, warns if the password still shows
   as pre-expired, and prints a summary and the undo commands.

The procedure's final status is success (1) or a failure code with the message inhibited,
so `$ @CREATE_GUEST` followed by `$ IF .NOT. $STATUS ...` works.

## Undo

As SYSTEM (the procedure prints these with your actual names):

```
$ MCR AUTHORIZE REMOVE GUEST
$ DELETE SYS$SYSDEVICE:[GUEST]*.*;*
$ SET FILE/PROTECTION=(S:RWED,O:RWED) SYS$SYSDEVICE:[000000]GUEST.DIR
$ DELETE SYS$SYSDEVICE:[000000]GUEST.DIR;1
```

The `SET FILE/PROTECTION` is needed because the directory is created without delete access.
`REMOVE` also takes the account's identifier out of the rights database.

## Where this differs from the original design

* **`/NOPWDEXPIRED` is added.** The AUTHORIZE documentation says a new password is, by
  default, valid for one login and must then be changed. With `/FLAGS=(LOCKPWD)` the visitor
  could not change it and would be locked out. It goes in a separate `MODIFY`, and step 7
  warns if the record still shows "pre-expired".
* **Expiry uses two different qualifiers.** `/PWDLIFETIME=NONE` is documented as "password
  never expires"; for the account itself the documented form is `/NOEXPIRATION`, not
  `/EXPIRATION=NONE`.
* **Passwords are upcased** and limited to letters, digits, `$` and `_` (AUTHORIZE's own
  rule), which also keeps anything odd out of the generated AUTHORIZE command lines.
  They are asked for twice.
* **The AUTHORIZE command is one symbol**, `AUTH_CMD = "MCR AUTHORIZE"` near the top. If
  `DEFINE/USER` does not reach AUTHORIZE through `MCR` on your system, change it to
  `RUN SYS$SYSTEM:AUTHORIZE`.
* **SYSUAF and RIGHTSLIST are defined for the run if they are not already.** The first real
  run on cpvax (OpenVMS V7.3) failed with `%UAF-E-NAOFIL, unable to open system
  authorization file (SYSUAF.DAT)`, `-RMS-E-FNF`: SYSTEM's default directory is `[SYSTEM]`
  on the data disk, and with no `SYSUAF` logical AUTHORIZE looks there. The procedure now
  defines `SYSUAF` and `RIGHTSLIST` as process logicals pointing into `SYS$SYSTEM:` when
  they are undefined, and removes them at the end. Existing definitions are never touched.
  A `NAOFIL` from AUTHORIZE now stops the run in step 2 instead of being read as "account
  not found".
* **Extra hardening** beyond the original list: `/ACCOUNT`, `/FLAGS=(DISMAIL)`, `/NOBATCH`.
  Not done on purpose: `/NONETWORK` (it could lock visitors out of FTP and similar) and
  anything that limits memory or I/O quotas. Add them as `CALL MOD_ONE` lines if wanted.

## Local check

```
$ ./check_dcl.sh                 # checks CREATE_GUEST.COM, or name other .COM files
check_dcl: OK (1 file(s))
```

`check_dcl.sh` needs only bash and awk. It checks that the file is plain ASCII with no tab,
uses LF throughout or CRLF throughout, every line starts with `$`, no line is over 254
characters, double quotes are balanced and apostrophes only appear as `'symbol'`
substitutions on non-comment lines, every `GOTO`/`ERROR=`/`END_OF_FILE=` target and every
`CALL` target exists, labels are unique, and the file name is ODS-2. It cannot tell you
the DCL is *right*. (The repo keeps text as LF; FTP in ASCII mode makes the VMS record
format.)

## Unverified - watch these on the first real run

No V7.3 manual page was reachable, so qualifiers were checked against the VMS 5.5 AUTHORIZE
help (typewritten.org) and the OpenVMS 8.3 security guide (`/EXPIRATION`, `DISUSER`). They
have been stable for decades, but none of this was confirmed against V7.3 itself.

**AUTHORIZE qualifiers**

* Core `ADD` (all appear in the 5.5 help; expected fine on V7.3): `/PASSWORD /OWNER /UIC
  /DEVICE /DIRECTORY /PRIVILEGES /DEFPRIVILEGES /FLAGS=(LOCKPWD)`.
* `/NOPWDEXPIRED` - listed in the help but with no description found; the pre-expired
  default is what makes it important.
* `/PWDLIFETIME=NONE` - "NONE means never expires" is in the 5.5 help.
* `/NOEXPIRATION` - documented as the way to remove an expiry date.
* `/ACCOUNT=GUEST`, `/MAXJOBS=4`, `/PRCLM=3`, `/FLAGS=(DISMAIL)` - in the 5.5 help.
* `/NOBATCH` - **least certain**; not confirmed in anything read. Drop it if it errors.
* Trailing `-` line continuation in AUTHORIZE input read from a file (used by the `ADD`).
  If AUTHORIZE complains, put the `ADD` on one line (about 200 characters).
* The text `Username: NAME ` in `SHOW` output (used to detect an existing account) and the
  word `pre-expired` (used for the warning). If either differs, the account looks absent
  or the warning never fires; check the printed record by eye.

**DCL idioms**

* `DEFINE/USER SYS$INPUT`, `SYS$OUTPUT` and `SYS$ERROR` (the last two to two *different*
  files) ahead of `MCR AUTHORIZE`. The first real run printed nothing from AUTHORIZE at
  all; the procedure now says so ("AUTHORIZE printed nothing") and retries with
  `RUN SYS$SYSTEM:AUTHORIZE`. Whether that fixes it is not known yet.
* `DEFINE/USER SYS$OUTPUT NL:` and `SYS$ERROR NL:` before `SEARCH` to keep it quiet, then
  `$SEVERITY .EQ. 1` meaning "found".
* `SET TERMINAL/NOECHO` with `READ ... SYS$COMMAND` for the password entry (echo is
  restored in the cleanup section on every exit path).
* `F$ENVIRONMENT("PROTECTION")` fed back into `SET PROTECTION=(...)/DEFAULT` to restore
  the default file protection; if that fails the default stays `S:RWED,O:RWED,G,W`.
* `SET PROTECTION=(S:RWED,O:RWED,G,W)/DEFAULT` giving no access to `G,W` with no
  access letters.
* `CREATE/DIRECTORY ... /OWNER_UIC= /PROTECTION=(S:RWE,O:RWE,G,W)` and
  `SET FILE/OWNER_UIC=` on `LOGIN.COM`.
* Subroutines (`CALL`) reading the caller's symbols (`BASE`, `G_USER`, `SAY`, `AUTH_CMD`),
  `IF .NOT. $STATUS` straight after a `CALL`, and a symbol used as a command
  (`$ 'AUTH_CMD'`).
* `F$SEARCH(spec,stream)`, `F$GETDVI(dev,"EXISTS")` and `F$PRIVILEGE("SYSPRV")` used as
  true/false tests; `EXIT %X10000002` (message-inhibited error status).
* `ON CONTROL_Y THEN GOTO` and `READ/END_OF_FILE=label`.

Known limits: a visitor can still create a newer `LOGIN.COM` in the home directory, since
the directory is writable by the account; and the visitors share one UIC and one set of files.
