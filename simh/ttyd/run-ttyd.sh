#!/bin/sh
# Serve cpvax in a browser tab through ttyd (xterm.js).  Two ways in, chosen by VAX_MODE:
#   login    (default) telnet to OpenVMS itself, 192.168.20.30:23: a normal VT100 user session;
#            several at a time.
#   console  the simh console on 127.0.0.1:2323 (OPA0:).  One client at a time, and Ctrl-E there
#            gives the simh prompt, where "quit" stops the machine without a VMS shutdown.
# Both offer to power the VAX on when it is off (see ondemand/: it needs a buffered simh console, a sudoers line,
# and vax-ctl switches it off again when idle).  Watching it boot: power it on from the console window.
# The terminal is writable, so keep it on one interface, "lo" by default, behind an authenticating proxy
# (POSIX/web-ttyd).  For no browser chrome at all, use F11, or the browser's "install as app".
#
# SCROLLBACK=0 gives a real VT100's behaviour (nothing scrolls back) and removes the scrollbar.
#
#   ./ttyd/run-ttyd.sh                      # login    http://127.0.0.1:7683/
#   VAX_MODE=console ./ttyd/run-ttyd.sh     # console  http://127.0.0.1:7684/
here=$(cd "$(dirname "$0")" && pwd)
case ${VAX_MODE:-login} in
  login)   VAX_HOST=${VAX_HOST:-192.168.20.30}; VAX_PORT=${VAX_PORT:-23};  VAX_NAME=cpvax
           VAX_BOOT_WAIT=${VAX_BOOT_WAIT:-900}
           VAX_HINT=${VAX_HINT-Boot messages are on the cpvax console (from the list of apps).}
           title="cpvax (OpenVMS)";  port=7683; max=4 ;;
  console) VAX_HOST=${VAX_HOST:-127.0.0.1};     VAX_PORT=${VAX_PORT:-2323}; VAX_NAME="cpvax console"
           VAX_BOOT_WAIT=${VAX_BOOT_WAIT:-120}
           VAX_HINT=${VAX_HINT-}
           # not during the ROM self-test, nor while vax-boot-watch reads the console (58 s to about 63 s after the
           # start); what it read is printed first, so the window still shows the self-test
           VAX_ATTACH_DELAY=${VAX_ATTACH_DELAY:-75}; VAX_PROBE=${VAX_PROBE:-listen}
           VAX_BOOT_LOG=${VAX_BOOT_LOG-/run/vax-ctl/console-boot.txt}
           title="cpvax console";    port=7684; max=1 ;;
  *) echo "VAX_MODE must be login or console" >&2; exit 2 ;;
esac
export VAX_HOST VAX_PORT VAX_NAME VAX_BOOT_WAIT VAX_HINT VAX_ATTACH_DELAY VAX_PROBE VAX_BOOT_LOG
exec "${TTYD:-ttyd}" -W -i "${IFACE:-lo}" -p "${PORT:-$port}" -m "${MAX_CLIENTS:-$max}" \
  -T vt100 ${BASE:+-b "$BASE"} \
  -t titleFixed="$title" -t disableLeaveAlert=true -t disableResizeOverlay=true \
  -t macOptionIsMeta=true -t cursorBlink=true -t scrollback="${SCROLLBACK:-2000}" -t fontSize=16 \
  -t 'fontFamily=Cascadia Mono, Consolas, DejaVu Sans Mono, Menlo, monospace' \
  -t 'theme={"background":"#000000","foreground":"#d8d8d8"}' \
  "$here/cpvax-term.sh"
