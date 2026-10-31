# talk - TALK and PHONE on cpvax reach the LAN's talkd

On cpvax (OpenVMS VAX V7.3, TCPware) `TALK` and `PHONE` talk to the LAN's one talk daemon, `talkd.py` on cpbee
(`POSIX/chat-setup/talkd`), and so to the users on cpbee and to tvchat users registered there, in both directions.
This is the "stock" option: no chat client of our own, only TCPware's own `TALK` (a NetBSD ntalk client) and `TALKD`,
plus two small DCL wrappers.

| file | what |
|------|------|
| `TALK.COM` | `TALK user[@host] [tty]`: for a user on another host, lower-cases the name, host and tty (DCL upcases unquoted parameters; talkd compares names as written), then runs `TCPWARE:TALK` |
| `PHONE.COM` | `PHONE [DIAL] user[@host]` calls through `TALK.COM`; `PHONE` asks who; `PHONE ANSWER` explains how to answer; `PHONE NATIVE` runs the VMS PHONE |
| `TALK_SETUP.COM` | defines the global symbols `TALK` and `PHONE` as `@` these two procedures (a symbol beats the DCL verb) |
| `INSTALL_TALK.COM` | creates `CPVAX$DUA1:[TALK]`, copies the three procedures there, prints the `SYLOGIN` line |
| `tests/talktest.py` | the real exchange: logs in to cpvax (telnet, `~/.netrc`) and cpbee (ssh), has one call the other, answers, and checks a line each way |

## How it is hooked in

* `SYS$MANAGER:SYLOGIN.COM;6` (`;5` is the old one) has, after `@TCPWARE:TCPWARE_COMMANDS` (which defines `TALK :== $TCPWARE:TALK`)
  and `define DCL$PATH`:
  `$ IF F$SEARCH("CPVAX$DUA1:[TALK]TALK_SETUP.COM") .NES. "" THEN @CPVAX$DUA1:[TALK]TALK_SETUP`
* `SYS$SPECIFIC:[TCPWARE]TCPWARE_CONFIGURE.COM;9` has `TALKD_ENABLE == 1` (`;8` had 0). `STARTNET` runs every
  `TCPWARE:*_CONTROL.COM`, so `TALK_CONTROL.COM STARTUP` starts the process `TCPware_TALKD` at boot. It was started by hand
  on 2026-10-31 with `TALKD_ENABLE == 1` and `@TCPWARE:TALK_CONTROL STARTUP`.
* The files in `[TALK]` are protected `(S:RWED,O:RWED,G:RE,W:RE)`; FTP creates files without world access, so run
  `SET FILE/PROTECTION=(S:RWED,O:RWED,G:RE,W:RE) CPVAX$DUA1:[TALK]*.COM;*` after copying them by FTP.

Neither `TALK.EXE` nor `PHONE.EXE` was replaced. Undo: delete the `SYLOGIN` lines (copy `;5` back), `TALKD_ENABLE == 0`,
`STOP/ID` the `TCPware_TALKD` process.

## What had to change on cpbee (not in this repo)

cpbee's talkd and firewall did not know the VAX zone (192.168.20.0/24, interface `vaxtap`):

* `talkd.service`: `--allow 192.168.20.0/24` besides 192.168.10.0/24 (`configure-talkd.sh --allow 192.168.10.0/24 --allow 192.168.20.0/24`;
  a re-run of that script **without** `--allow` goes back to lan0's subnet only and cuts the VAX off again).
* `setup-router.sh` (cmpi-router, in OneDrive, not in git), VAX zone input rules: UDP 518 (ntalk), TCP 5181-5188 (talkd's
  relay ports, for a tvchat user calling the VAX) and TCP 32768-60999 (a `talk` caller on cpbee listens on an ephemeral port
  and the callee, here the VAX, connects to it). `setup-router.sh fw` loads them. Done by `TO_BE_RUN/talk-vax-on-cpbee.sh`
  on 2026-10-31.

## Use

```
$ TALK chris@cpbee            a user logged in on cpbee, or one using tvchat there
$ PHONE chris@cpbee           the same
$ TALK system                 a user on this VAX (TALKD rings the terminal)
$ PHONE                       asks "Who do you want to call?"
```

A call to the VAX from cpbee: `talk system@cpvax` (VMS names are case-insensitive for the callee); the VAX terminal is rung
with `talk: respond with:  talk chris@cpbee.cmnet`, and the user types that, or `PHONE chris@cpbee`.

## Verified (2026-10-31)

`tests/talktest.py A` (cpbee calls the VAX, the VAX answers with `PHONE chris@cpbee`) and `B` (the VAX calls with
`TALK chris@cpbee`, cpbee answers with the command its ring shows): both connect, and a line typed on each side appears on the other.

Not verified: a user other than SYSTEM (there is no GUEST account yet: `guest/CREATE_GUEST.COM` has not been run; the
files are world-readable and `TCPWARE:TALK.EXE` is world-executable, so it should work), a tvchat user as the other party,
and a reboot (TALKD should start by itself).

## Things that bit

* `$TCPWARE:TALK` typed inside a procedure ran `TALK.COM` again (nesting error): define a foreign command symbol
  (`TCPTALK := $TCPWARE:TALK`) instead.
* TCPware's TALK refuses to run from a procedure ("Standard input must be a tty"): `DEFINE/USER_MODE SYS$INPUT SYS$COMMAND`.
* The TALK ring on the VAX reads `Talk_Daemon@CPVAX.CMNET`; `SHOW NETWORK` still said `CPVAX.LAN` until TCPware reloaded the domain.
* Unquoted DCL parameters are upcased, and `pts/3` reads as a qualifier: quote it (`TALK chris@cpbee "pts/3"`).
