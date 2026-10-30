#!/bin/bash
# A telnet session to cpvax for ttyd.  Not a shell: it can power the VAX on, telnet to one place, and retry.
#   VAX_HOST / VAX_PORT   where to connect (default: OpenVMS itself, 192.168.20.30:23)
#   VAX_NAME              what to call it in the messages
#   VAX_UNIT              the systemd unit (default vax.service)
#   VAX_BOOT_WAIT         seconds to wait for it to answer after power-on
#   VAX_HINT              one line to show while waiting
#   VAX_START_CMD         how to power it on (default: sudo -n /usr/bin/systemctl start vax.service, which
#                         ondemand/install.sh allows for this account, and nothing else)
#   VAX_BOOT_LOG          a file to print before attaching: what the boot supervisor read from the console during the
#                         self-test (see below); the console mode of run-ttyd.sh sets it
# The VAX is off until someone asks for it here, and vax-ctl (ondemand/) switches it off again when it is idle.
# telnet -E turns off the escape character, so there is no "telnet>" prompt and no "!" shell escape.
# TERM=vt100: what the programs in this repo (and DCL's SET TERMINAL/INQUIRE) expect.
host=${VAX_HOST:-192.168.20.30}
port=${VAX_PORT:-23}
name=${VAX_NAME:-cpvax}
unit=${VAX_UNIT:-vax.service}
boot_wait=${VAX_BOOT_WAIT:-900}
hint=${VAX_HINT:-}
# The console window must not touch the simh console while the KA655 ROM runs its self-test (about 50 s after the
# simulator starts): a client connecting then sometimes makes the test fail with "?53 ... Normal operation not
# possible", and the VAX does not boot.  VAX_ATTACH_DELAY holds the window back until the simulator is that old, and
# VAX_PROBE=listen checks the port is open without connecting to it.  The buffered console then replays the whole boot.
attach_delay=${VAX_ATTACH_DELAY:-0}
probe=${VAX_PROBE:-connect}
# The boot supervisor (ondemand/: vax-ctl boot-watch) is the console's first client, at about a minute, and a buffered
# console may give its output to the first client only.  The supervisor keeps a copy in VAX_BOOT_LOG, printed here before
# attaching, so the window still shows the self-test (it empties the file when the console re-sends the text anyway, so
# nothing is shown twice).  The delay must stay clear of its connection (58 s to about 63 s of age, longer if the test
# is slow to finish).
boot_log=${VAX_BOOT_LOG:-}
shown_pid=
start_cmd=${VAX_START_CMD:-sudo -n /usr/bin/systemctl start $unit}
conf=${VAX_CTL_CONF:-/etc/vax-ctl.conf}
export TERM=vt100
trap : INT

answers() {
  if [ "$probe" = listen ]; then
    ss -ltnH "sport = :$port" 2>/dev/null | grep -q .
  else
    nc -z -w 3 "$host" "$port" 2>/dev/null
  fi
}
powered() { systemctl is-active --quiet "$unit" 2>/dev/null; }

sim_age() {   # seconds since the simulator process started; 0 if it cannot be told
  local pid age=0
  pid=$(systemctl show -p MainPID --value "$unit" 2>/dev/null)
  if [[ $pid =~ ^[0-9]+$ ]] && (( pid > 0 )); then
    age=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
  fi
  echo "${age:-0}"
}

# Something to watch while the VAX starts: a spinner that turns four times a second, and either a bar that fills over
# a known time (bar_line) or a block that sweeps to and fro when the wait has no known length (bounce_line).
spin_frames='|/-\'
frame=0

bar_line() {   # bar_line ELAPSED TOTAL LABEL
  local e=$1 t=$2 w=30 f i bar=
  (( e > t )) && e=$t
  f=$(( e * w / t ))
  for (( i = 0; i < w; i++ )); do if (( i < f )); then bar+='█'; else bar+='░'; fi; done
  printf '\r  %s [%s] %3d%%  %s\033[K' "${spin_frames:$((frame++ % 4)):1}" "$bar" $(( e * 100 / t )) "$3"
}

bounce_line() {   # bounce_line LABEL
  local w=30 b=4 span pos i bar=
  span=$(( w - b )); pos=$(( (frame / 2) % (2 * span) )); (( pos > span )) && pos=$(( 2 * span - pos ))
  for (( i = 0; i < w; i++ )); do if (( i >= pos && i < pos + b )); then bar+='█'; else bar+='░'; fi; done
  printf '\r  %s [%s] %s\033[K' "${spin_frames:$((frame++ % 4)):1}" "$bar" "$1"
}

# settle: hold back until the simulator is attach_delay seconds old (see above); fails if cancelled or it stops
settle() {
  (( attach_delay > 0 )) || return 0
  local a k prev=0 sub stage intro=0
  while a=$(sim_age); (( a < attach_delay )); do
    powered || { printf '\r\033[K%s stopped while starting (journalctl -u %s, on cpbee).\r\n' "$name" "$unit"; return 1; }
    if (( a > 0 )); then          # 0 means the age could not be told
      if (( a + 5 < prev )); then   # younger than a moment ago: the simulator was restarted
        printf '\r\033[K%s was restarted (the boot watcher does that when the ROM self-test fails).\r\n' "$name"
      fi
      prev=$a
    fi
    if (( ! intro )); then
      printf '\r\033[KThe simulator runs its ROM self-test, then the boot supervisor checks it.\r\n'
      printf 'The console connects after that and shows the whole boot.\r\n\r\n'
      intro=1
    fi
    if   (( a < 55 )); then stage="KA655 self-test"
    elif (( a < 68 )); then stage="checking the self-test"
    else stage="VMS is starting"; fi
    for sub in 1 2 3 4; do
      bar_line "$a" "$attach_delay" "$stage, $((attach_delay - a)) s  (q: cancel)"
      if read -r -s -t 0.25 -n 1 k && [[ $k == [qQ] ]]; then
        printf '\r\033[K'
        return 1
      fi
    done
  done
  printf '\r\033[K'
}

# show_boot_log: print what the boot supervisor read from the console, once per start of the simulator, and only if it
# was written during this run of the simulator (not left over from an earlier one)
show_boot_log() {
  local pid age mtime
  [ -n "$boot_log" ] && [ -s "$boot_log" ] || return 0
  pid=$(systemctl show -p MainPID --value "$unit" 2>/dev/null)
  [ -n "$pid" ] && [ "$pid" != "$shown_pid" ] || return 0
  age=$(sim_age)
  mtime=$(stat -c %Y "$boot_log" 2>/dev/null) || return 0
  (( age > 0 && $(date +%s) - mtime <= age + 2 )) || return 0
  shown_pid=$pid
  tr -d '\0' < "$boot_log"
  printf '\r\n'
}

idle_note() {
  local m
  m=$(sed -n 's/^IDLE_MINUTES=\([0-9][0-9]*\).*/\1/p' "$conf" 2>/dev/null | head -1)
  if [ -n "$m" ]; then printf '(It switches itself off after %s minutes with no activity.)\r\n' "$m"; fi
  return 0
}

power_on() {
  printf '\r\nPowering on the VAX...\r\n'
  if ! $start_cmd; then
    printf 'Could not start %s.  One-time setup on cpbee: VAX/simh/ondemand/install.sh\r\n' "$unit"
    printf '(it lets this account run exactly that command, and nothing else).\r\n'
    return 1
  fi
}

# wait_for SECONDS: until the target answers, with a progress line; q cancels; gives up if the VAX stops
wait_for() {
  local limit=$1 t0=$SECONDS e k sub
  [ -z "$hint" ] || printf '%s\r\n' "$hint"
  until answers; do
    e=$((SECONDS - t0))
    if ! powered; then
      printf '\r\033[K%s stopped while starting (journalctl -u %s, on cpbee).\r\n' "$name" "$unit"
      return 1
    fi
    if (( e >= limit )); then
      printf '\r\033[K%s is on but has not answered at %s:%s in %d seconds.\r\n' "$name" "$host" "$port" "$limit"
      printf 'Look at the cpvax console: VMS may still have its old address (see setup-vax.sh, FIRST BOOT).\r\n'
      return 1
    fi
    for sub in 1 2 3 4; do
      bounce_line "waiting for $name  $((e / 60)):$(printf %02d $((e % 60)))  (q: cancel)"
      if read -r -s -t 0.25 -n 1 k && [[ $k == [qQ] ]]; then
        printf '\r\033[K'
        return 1
      fi
    done
  done
  printf '\r\033[K'
}

while :; do
  if answers; then
    if settle; then
      show_boot_log
      idle_note
      telnet -E "$host" "$port"
      printf '\r\n[%s: connection closed]\r\n' "$name"
    fi
  elif powered; then
    printf '%s is on but not answering yet.\r\n' "$name"
    wait_for "$boot_wait" && continue
  else
    printf '%s is powered off.\r\n' "$name"
    idle_note
    read -r -n1 -p $'\r\nEnter: power it on and connect    q: quit  ' key || break
    [[ $key == [qQ] ]] && break
    power_on && wait_for "$boot_wait" && continue
  fi
  read -r -n1 -p $'\r\nEnter: try again    q: quit  ' key || break
  [[ $key == [qQ] ]] && break
  printf '\r\n'
done
