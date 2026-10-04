#!/bin/bash
# Keep a reverse ssh tunnel up so that the web host (webhost) can reach the VAX's telnet port.
#
# webhost cannot talk to the VAX directly (SIMH's pcap networking never loops frames back to the
# Pi that hosts it), but this machine can.  So this machine opens
#       webhost:127.0.0.1:2323  ->  <VAX address>:23
# and the web app on webhost simply connects to its own localhost:2323.
#
# usage:  VAX_IP=a.b.c.d ./tunnel.sh [ssh-host-of-the-web-server]
: "${VAX_IP:?set VAX_IP to the address of the VAX}"
HOST="${1:-webhost}"
PORT="${TUNNEL_PORT:-2323}"
while true; do
  echo "$(date '+%F %T') opening tunnel $HOST:127.0.0.1:$PORT -> $VAX_IP:23"
  ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
      -R "127.0.0.1:$PORT:$VAX_IP:23" "$HOST"
  echo "$(date '+%F %T') tunnel dropped; retrying in 10s"
  sleep 10
done
