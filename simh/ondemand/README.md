# cpvax on demand

The simh VAX on cpbee is off until someone asks for it, and switches itself off, in an orderly way, when it has been idle.

    open the cpvax console (or cpvax) window  ->  "cpvax is powered off.  Enter: power it on and connect"
    Enter  ->  `sudo systemctl start vax.service`  ->  the console shows KA655 self-test, then VMS booting
    ...no activity for 30 minutes  ->  vax-ctl logs in to OpenVMS, runs SHUTDOWN, then stops the unit

| file | what |
|---|---|
| `vax-ctl` | `idle-check` (what the timer runs), `shutdown` (log in to VMS, run `@SYS$SYSTEM:SHUTDOWN`, then stop the unit), `status` |
| `vax-ctl.conf` | idle limit and thresholds (`/etc/vax-ctl.conf`) |
| `vax-idle.service`, `vax-idle.timer` | run `vax-ctl idle-check` once a minute, as root |
| `install.sh` | run on cpbee: the above, a VMS account for the shutdown, and one sudoers line (`-n` dry run, `-u` remove) |
| `tests/test_vax_ctl.py` | the idle decision, the `/proc` and `/sys` readers, and the SHUTDOWN login against a fake VMS |
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
It is **intermittent**.  Measured on cpbee with throwaway simh instances (same ROM, 512M, a copy of the real nvram):

| console | when a client connected | self-test failed |
|---|---|---|
| buffered | nobody until the test was over (14 runs) | 0 |
| not buffered | before the CPU started (6 runs) | 0 |
| buffered | 2-3 s into the test (8 runs, quiet host) | 3 |
| buffered | 1-3 s into the test, other simh instances running | 2 of 2 |

and one failure through the web wrapper (1 of 2 valid runs) even though it connected only after the test.  So a client
connecting during the self-test makes it more likely, but is not the only cause, and the cause is not found.
`SET CPU IDLE` on or off, and the memory size (64M or 512M), made no difference in the runs above.
Things the measurements ruled out:

- **Not buffering the console** passes, but simh then **exits when the last console client disconnects**
  (`Console Telnet connection lost ... Goodbye`), so it cannot work with windows that come and go.
- **The first console client takes the buffered output**: a second client that connects later sees none of it.

What is in place: the console window does not connect until the simulator is 60 s old (`VAX_ATTACH_DELAY`) and checks
that the port is open without connecting (`VAX_PROBE=listen`), so it never touches the console during the self-test.
That lowers the odds; it does not remove the failure.  If you see `Normal operation not possible`, no VMS is running,
so it is safe to `sudo systemctl stop vax` and power it on again.  The next step, if it keeps happening, is a boot
supervisor that notices the failure and restarts the VAX by itself (up to a few tries).

## How "idle" is decided

Every minute, as root, `vax-ctl idle-check` samples simh's CPU time and the bytes over the `vaxtap` interface.  The VAX
is idle in a minute when simh used less than `CPU_PCT_MAX` (3) percent of a core **and** fewer than
`NET_BYTES_PER_MIN_MAX` (60000) bytes crossed the tap.  After `IDLE_MINUTES` (30) idle minutes in a row it shuts down.
A telnet session nobody types in is idle; a batch job or a transfer is not.  The first `STARTUP_GRACE_MINUTES` (10)
after a start never count.  `vax-ctl status` shows the count; `sudo journalctl -u vax-idle` shows what it did.  The right
thresholds depend on how quiet a logged-in VMS really is under simh (`SET CPU IDLE`): watch it once and adjust.

## The orderly shutdown

A plain `systemctl stop vax` is a power cut for the emulated machine, so the stop always goes through VMS: `vax-ctl`
logs in over telnet to OpenVMS (`192.168.20.30`) with the account in `/etc/vax-ctl.cred` (root only, mode 600), runs
`@SYS$SYSTEM:SHUTDOWN`, answers its prompts (2 minutes' warning to logged-in users, no reboot, defaults for the rest),
and when VMS goes down waits 20 seconds and stops the unit.  If anything is unexpected (login refused, a prompt it does
not know, VMS not going down) it logs the transcript (never the password), leaves the VAX **running**, and tries again
after 15 minutes.  Nothing is ever stopped by force.

**Untested against the real VMS**: the dialogue is tested against a fake that follows `SHUTDOWN.COM`'s prompts as
documented for V7.3, but the first real run should be watched: `sudo vax-ctl shutdown` while you are on the console
window.  The account needs the privileges `SHUTDOWN` checks (SYSTEM has them); a dedicated account is better than
SYSTEM if you create one.

## The sudoers line

The web terminal runs as you, so it needs one thing as root: `sudo -n /usr/bin/systemctl start vax.service`.
`install.sh` writes exactly that to `/etc/sudoers.d/vax-web` (checked with `visudo -cf` first), and nothing else: it
cannot stop the VAX, or start anything else.

## Notes

- Powering on needs OpenVMS to answer at `192.168.20.30:23` for the **cpvax** window; if VMS still has its old address
  (`192.168.1.30`, see `setup-vax.sh`, FIRST BOOT) it never will, and the window says to look at the console.
- The console window is where to watch the boot.  Only one client can be attached to the simh console at a time.
- `SET CPU CONHALT` makes a VMS halt return to the `>>>` prompt, with simh still running; the unit is stopped by
  `vax-ctl` after a shutdown, not by simh exiting.
- To make it run all the time again, `sudo systemctl start vax` by hand still works, and `vax-ctl` will still switch it
  off when idle: stop the timer (`sudo systemctl stop vax-idle.timer`) to keep it up.
