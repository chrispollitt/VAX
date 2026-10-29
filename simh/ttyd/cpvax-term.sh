#!/bin/bash
# A telnet session to cpvax for ttyd.  Not a shell: it can power the VAX on, telnet to one place, and retry.
#   VAX_HOST / VAX_PORT   where to connect (default: OpenVMS itself, 192.168.20.30:23)
#   VAX_NAME              what to call it in the messages
#   VAX_UNIT              the systemd unit (default vax.service)
#   VAX_BOOT_WAIT         seconds to wait for it to answer after power-on
#   VAX_HINT              one line to show while waiting
#   VAX_START_CMD         how to power it on (default: sudo -n /usr/bin/systemctl start vax.service, which
#                         ondemand/install.sh allows for this account, and nothing else)
# The VAX is off until someone asks for it here, and vax-ctl (ondemand/) switches it off again when it is idle.
# telnet -E turns off the escape character, so there is no "telnet>" prompt and no "!" shell escape.
# TERM=vt100: what the programs in this repo (and DCL's SET TERMINAL/INQUIRE) expect.
host=${VAX_HOST:-192.168.20.30}
port=${VAX_PORT:-23}
name=${VAX_NAME:-cpvax}
unit=${VAX_UNIT:-vax.service}
boot_wait=${VAX_BOOT_WAIT:-900}
hint=${VAX_HINT:-}
start_cmd=${VAX_START_CMD:-sudo -n /usr/bin/systemctl start $unit}
conf=${VAX_CTL_CONF:-/etc/vax-ctl.conf}
export TERM=vt100
trap : INT

answers() { nc -z -w 3 "$host" "$port" 2>/dev/null; }
powered() { systemctl is-active --quiet "$unit" 2>/dev/null; }

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
  local limit=$1 t0=$SECONDS spin='|/-\' i=0 e k
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
    printf '\r  %s  waiting for %s to answer at %s:%s ...  %d:%02d   (q: cancel) ' \
      "${spin:$((i++ % 4)):1}" "$name" "$host" "$port" $((e / 60)) $((e % 60))
    if read -r -s -t 1 -n 1 k && [[ $k == [qQ] ]]; then
      printf '\r\033[K'
      return 1
    fi
  done
  printf '\r\033[K'
}

while :; do
  if answers; then
    idle_note
    telnet -E "$host" "$port"
    printf '\r\n[%s: connection closed]\r\n' "$name"
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
