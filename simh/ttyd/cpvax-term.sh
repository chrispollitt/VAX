#!/bin/bash
# A telnet session to cpvax for ttyd.  Not a shell: it can only telnet to one place and retry.
#   VAX_HOST / VAX_PORT   where to connect (default: OpenVMS itself, 192.168.20.30:23)
#   VAX_NAME              what to call it in the messages
# telnet -E turns off the escape character, so there is no "telnet>" prompt and no "!" shell escape.
# TERM=vt100: what the programs in this repo (and DCL's SET TERMINAL/INQUIRE) expect.
host=${VAX_HOST:-192.168.20.30}
port=${VAX_PORT:-23}
name=${VAX_NAME:-cpvax}
export TERM=vt100
trap : INT

while :; do
  if nc -z -w 3 "$host" "$port" 2>/dev/null; then
    telnet -E "$host" "$port"
    printf '\r\n[%s: connection closed]\r\n' "$name"
  else
    printf '%s is not answering at %s:%s.\r\n' "$name" "$host" "$port"
    printf 'It is started by hand, on cpbee:  sudo systemctl start vax   (VMS then takes a few minutes to boot).\r\n'
  fi
  read -r -n1 -p $'\r\nEnter: connect again    q: quit  ' key || break
  [[ $key == [qQ] ]] && break
  printf '\r\n'
done
