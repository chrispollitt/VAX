# cpvax on demand

The simh VAX on cpbee is off until someone asks for it, and switches itself off, in an orderly way, when it has been idle.

    open the cpvax console (or cpvax) window  ->  "cpvax is powered off.  Enter: power it on and connect"
    Enter  ->  `sudo systemctl start vax.service`  ->  the console shows KA655 self-test, then VMS booting
    ...the self-test failed (`?53`)  ->  vax-boot-watch notices at about a minute and restarts the VAX, up to 3 times
    ...no activity for 30 minutes  ->  vax-ctl logs in to OpenVMS, runs SHUTDOWN, then stops the unit

| file | what |
|---|---|
| `vax-ctl` | `idle-check` (what the timer runs), `shutdown` (log in to VMS, run its SHUTDOWN command, then stop the unit), `boot-watch` (the boot supervisor), `status` |
| `vax-ctl.conf` | idle limit and thresholds, `BOOT_RETRIES` (`/etc/vax-ctl.conf`) |
| `vax-idle.service`, `vax-idle.timer` | run `vax-ctl idle-check` once a minute, as root |
| `vax-boot-watch.service`, `vax.service.d/boot-watch.conf` | run `vax-ctl boot-watch` after every start of `vax.service`, as root; the drop-in is what makes `vax.service` start it |
| `install.sh` | run on cpbee: the above, a VMS account for the shutdown, and one sudoers line (`-n` dry run, `-u` remove) |
| `tests/test_vax_ctl.py` | the idle decision, the `/proc` and `/sys` readers, the SHUTDOWN login against a fake VMS, and the boot supervisor against a fake console |
| `../ttyd/cpvax-term.sh` | the web terminal: offers to power on, shows progress, connects when the target answers |

## One required change to vax.ini: a buffered console

With `SET CONSOLE TELNET=2323` simh waits at `boot cpu` for a telnet client, and if none connects within 30 seconds it
logs `Console Telnet connection timed out` and **exits**.  A VAX powered on from the web would die before anyone could
connect.  A buffered console removes the wait: simh runs with nobody attached, keeps up to 64 KB of console output, and a
client that connects later sees it (so you can open the console window after powering on from the other one).
Checked on cpbee with throwaway instances: without the line simh exited after 30 s; with it, it ran, a late client saw
the KA655 self-test, and disconnecting and reconnecting did not stop it.

    SET CONSOLE TELNET=2323
    SET CONSOLE TELNET=BUFFERED=65536

`install.sh` refuses to go on until the line is in `/var/simh/vax/vax.ini`.  cmpi-router's `setup-vax.sh` writes that
file with a `sed` that adds the telnet line after `SET CONSOLE BRK=0`; add the buffered line there too, or a re-run of
`setup-vax.sh` drops it:

    -e "s#^SET CONSOLE BRK=0#SET CONSOLE BRK=0\nSET CONSOLE TELNET=$CONSOLE_PORT\nSET CONSOLE TELNET=BUFFERED=65536#" \

## Known issue: the ROM self-test sometimes fails (`?53`)

After a power-on the KA655 ROM runs a self-test of about 50 seconds.  Sometimes it ends with
`?53 2 0A FF 00 0000 ... Normal operation not possible.` and the VAX sits at the `>>>` prompt without booting.
It is **random**: about one boot in five to ten, whatever the console is doing.  Measured on cpbee with throwaway
simh instances (same ROM, 512M, a copy of the real nvram), counting self-tests that failed:

| configuration | runs | failed |
|---|---|---|
| buffered console, **nobody connected** until the test was over | 30 | 3 |
| of those, with `SET CPU IDLE` / without it | 8 / 8 | 2 / 1 |
| not buffered, client attached before the CPU started | 6 | 0 |
| buffered, a client connected 2-3 s into the test | 8 | 3 |
| through the web console wrapper (it connected after the test) | 2 | 1 |
| buffered, nobody connected, 64M, 12 started at once (later, for the boot supervisor) | 12 | 4 |

I first thought a client connecting during the test caused it, and that `SET CPU IDLE` might; the runs with no client
at all fail about as often, and IDLE on or off makes no measurable difference, so neither is shown to matter.  The
cause is not found; treat it as random and **retry**.  Memory size (64M or 512M) made no difference either.
Two things the measurements did rule out:

- **Not buffering the console** gave no failures in 6 runs, but simh then **exits when the last console client
  disconnects** (`Console Telnet connection lost ... Goodbye`), so it cannot work with windows that come and go.
- **The first console client takes the buffered output**: a second client that connects later sees none of it.  This
  was true in the measurement above, but **not when I repeated it for the boot supervisor** (same simh binary, throwaway
  instances): a client that connected at 75 s, after one that had read everything at 58 s and gone, got the identical
  447 bytes, and the same happened in three runs of the 64M machine; once, with the first client leaving in the middle of
  the self-test, the second saw only what came after.  A second client that connects while the first is still attached
  is refused (`All connections busy`) and sees nothing, which may be what was seen.  So whether a later client sees the
  boot text is not settled; the supervisor below finds out on every boot instead of assuming.

What is in place: the console window does not connect until the simulator is 75 s old (`VAX_ATTACH_DELAY`) and checks
that the port is open without connecting (`VAX_PROBE=listen`).  That avoids connect-and-drop churn on the console while
the ROM runs, but it is not a fix.  If you see `Normal operation not possible`, no VMS is running, so it is safe to
`sudo systemctl restart vax` and power it on again; at one failure in five to ten, a retry works almost every time.
The boot supervisor below does that retry by itself.

### The boot supervisor: `vax-boot-watch.service` / `vax-ctl boot-watch`

A drop-in (`/etc/systemd/system/vax.service.d/boot-watch.conf`, `Wants=vax-boot-watch.service`) makes every start of
`vax.service` start the watcher, whether from the web terminal's sudoers rule or by hand, and `PartOf=vax.service` stops
and restarts it with the VAX.  It is a plain `Type=simple` root service (no `ExecStartPost`, which would hold `vax.service`
in `activating` and upset the web wrapper's `systemctl is-active`).  What it does, with its times in seconds of the simh
process's age:

1. at 58 it connects once to the console (`CONSOLE_HOST:CONSOLE_PORT`, `127.0.0.1:2323`), refusing every telnet option,
   and reads until the console has been quiet for 4 (or 15 have passed);
2. `Tests completed` in the text: the self-test passed, the failure count is reset, it disconnects and exits;
   `Normal operation not possible`: it failed;
3. neither (the test is slow, or the console was busy): it waits 15 and reads on, over the same connection; at 120 it
   gives up on a verdict, logs that and **does nothing** to the VAX;
4. on a failure it counts one in `/var/lib/vax-ctl/boot.json` and, below `BOOT_RETRIES` (3, in `/etc/vax-ctl.conf`), runs
   `systemctl --no-block restart vax.service`; at the limit it logs why, exits with a failure status (so
   `systemctl status vax-boot-watch` shows it) and leaves the VAX at `>>>` for you: `sudo systemctl restart vax`.

It never restarts after the self-test has passed, and never when the VAX was already more than two minutes old when it
started, or when `vax.service` changed process while it was reading.  A count older than five minutes is not carried
over, so a fresh power-on always gets a fresh set of tries.  History: `journalctl -u vax-boot-watch`, and
`vax-ctl status` shows the last verdict.

The counter is in `boot.json` beside `state.json`, not in it: `idle-check` rewrites `state.json` as a whole (and empties it
whenever the VAX is stopped, which includes the moment of a restart).

The watcher is the console's first client, and if a buffered console gives its output to the first client only, the
console window would miss the self-test.  So it keeps a copy of what it read in `/run/vax-ctl/console-boot.txt` (readable
by everyone, emptied at the start of each boot cycle), and the console window (`VAX_MODE=console` in `ttyd/run-ttyd.sh`)
prints that file before it attaches, at 75 s, clear of the watcher's connection at 58 to about 63 s.  Since the
measurement above says the console may well re-send the text to a later client, which would show the self-test twice,
the watcher settles it after a pass (or when it gives up): it connects once more, and if the text comes again it logs that
and empties the file, otherwise it logs that and leaves the copy for the window.  Only the last attempt is in the file; the
earlier ones are in the journal.  If the window is open while the VAX restarts, it says so and starts waiting again.  If the
self-test is slow enough that the watcher is still connected at 75 s, the window's connection is refused (one client at a
time): press Enter in the window to try again.

**What is tested, and what is not.** The decisions (the verdict on real captured console text, the counting, no restart
after a pass, giving up at the limit, the slow case, an unreachable console) are unit-tested against a fake console and
a fake `systemctl`, and the real `vax-ctl boot-watch` was run, under a user systemd manager with copies of these unit
files, against throwaway simh instances.  The real `?53` cannot be forced, and `vax.service` itself, the install on
cpbee and a real power-on from the web window have not been exercised by this work: the first real use is the test.

## How "idle" is decided

Every minute, as root, `vax-ctl idle-check` samples simh's CPU time and the bytes over the `vaxtap` interface.  The VAX
is idle in a minute when simh used less than `CPU_PCT_MAX` (30) percent of a core **and** fewer than
`NET_BYTES_PER_MIN_MAX` (1500) bytes crossed the tap.  After `IDLE_MINUTES` (30) idle minutes in a row it shuts down.
A telnet session nobody types in is idle; typing, a batch job or a transfer is not.  The numbers come from a 10-second
log of a real cpvax: untouched and logged in it uses 15-19% of a core and 200-900 bytes a minute; one typed command
adds about 1000 bytes, a login 6000+.  (The first guess, 60000 bytes, never saw a person at the keyboard: the VAX was
shut down under a user's session on 2026-10-29.)  Typing in the **web console window** is counted by a second signal:
that window talks to simh over the local socket `127.0.0.1:2323`, which never crosses `vaxtap` (found the same evening:
typing there left the network log at zero).  Each minute `vax-ctl` reads the console sockets with `ss` and counts the
keystroke bytes simh received (`CONSOLE_BYTES_PER_MIN_MAX`, 4); opening or closing a console window counts too.
The first `STARTUP_GRACE_MINUTES` (10)
after a start never count.  `vax-ctl status` shows the count; `sudo journalctl -u vax-idle` shows what it did.  The right
thresholds depend on how quiet a logged-in VMS really is under simh (`SET CPU IDLE`): watch it once and adjust.

## The orderly shutdown

A plain `systemctl stop vax` is a power cut for the emulated machine, so the stop always goes through VMS: `vax-ctl`
logs in over telnet to OpenVMS (`192.168.20.30`) with the account in `/etc/vax-ctl.cred` (root only, mode 600), types
the command in `SHUTDOWN_COMMAND` (default `SHUTDOWN`: cpvax's own command, which asks one question, "Do you really
want to shutdown node CPVAX [NO]?", and uses its defaults for the rest, as typed by hand), answers `YES`, and waits for
VMS to go down.  Once VMS has halted, simh ends by itself (`Infinite loop, PC: 9E3FB4D3 (BRB 9E3FB4D3)`, `Goodbye`: that
line is VMS's halted state, not an error), and `vax-ctl` makes sure the unit is stopped.  The VAX is then off.

What the first real runs (2026-10-29) taught it, all now in `tests/`:

- **Login:** the login procedure runs `SET TERMINAL/INQUIRE` (two terminal queries nobody answers, about 30 seconds) and
  the DCL prompt is `CPVAX$DUA1:[SYSTEM]`, not `$ `.  So a login is recognised by a marker command (it types
  `WRITE SYS$OUTPUT F$FAO("VAXCTL-!AS","OK")` and waits for `VAXCTL-OK`), resent until VMS answers, never by a prompt.
- **Questions** are matched even when the terminal wraps a line in the middle of a word (`final shu`/`tdown`), and each
  answer waits until VMS has finished the line.
- **Unknown questions** that show a default (`[later]:`) are answered with it (at most 6), so a longer dialogue, such as
  plain `@SYS$SYSTEM:SHUTDOWN` (set `SHUTDOWN_COMMAND=@SYS$SYSTEM:SHUTDOWN`), does not stall it.
- **Success** is the connection closing after VMS printed its `%SHUTDOWN-I-` messages (or the last known question was
  answered).  A session that dies in the middle of the questions is not a shutdown.
- Every 30 seconds while it waits it logs what VMS has sent (password blanked), and a failure logs the text that matched
  nothing, so a stall can be read from `journalctl -u vax-idle` (or the job's journal) afterwards.

If anything is unexpected it leaves the VAX **running** and tries again after 15 minutes.  Nothing is ever stopped by
force.  The account needs the privileges `SHUTDOWN` checks (SYSTEM has them); a dedicated account is better than SYSTEM
if you create one.  Each connection to the VMS telnet port, even a port probe, makes VMS start a login process and log
a "Remote interactive login failure" security alarm if it drops before logging in: harmless, but do not probe it in a loop.

## The sudoers line

The web terminal runs as you, so it needs one thing as root: `sudo -n /usr/bin/systemctl start vax.service`.
`install.sh` writes exactly that to `/etc/sudoers.d/vax-web` (checked with `visudo -cf` first), and nothing else: it
cannot stop the VAX, or start anything else.

## Notes

- Powering on needs OpenVMS to answer at `192.168.20.30:23` for the **cpvax** window; if VMS still has its old address
  (`192.168.1.30`, see `setup-vax.sh`, FIRST BOOT) it never will, and the window says to look at the console.
- The console window is where to watch the boot.  Only one client can be attached to the simh console at a time (the
  boot watcher is one, from about 58 to 63 s after a start).
- `SET CPU CONHALT` makes a VMS halt return to the `>>>` prompt, with simh still running; the unit is stopped by
  `vax-ctl` after a shutdown, not by simh exiting.
- To make it run all the time again, `sudo systemctl start vax` by hand still works, and `vax-ctl` will still switch it
  off when idle: stop the timer (`sudo systemctl stop vax-idle.timer`) to keep it up.
