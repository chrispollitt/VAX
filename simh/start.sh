#!/usr/bin/env bash
# Start the SIMH VAX (cpvax) if it is not running, then telnet to its console.
#
#   ./start.sh            start if needed, then telnet in
#   ./start.sh -n         start if needed, do not telnet
#
# HOST and PORT must match the console line in the VAX's .ini
# (e.g. "set console telnet=2323"); `systemctl cat vax` shows which .ini.
UNIT=${UNIT:-vax}
HOST=${HOST:-localhost}
PORT=${PORT:-2323}            # a guess: check the .ini
WAIT=${WAIT:-30}              # seconds to wait for the console port

if systemctl is-active --quiet "$UNIT"; then
    echo "$UNIT is already running"
else
    echo "starting $UNIT..."
    sudo systemctl start "$UNIT" || { echo "could not start $UNIT" >&2; exit 1; }
fi

# wait for the console to listen, instead of sleeping a fixed time
i=0
until (exec 3<>"/dev/tcp/$HOST/$PORT") 2>/dev/null; do
    i=$((i + 1))
    if [ "$i" -ge "$WAIT" ]; then
        echo "nothing listening on $HOST:$PORT after ${WAIT}s - check PORT and 'systemctl status $UNIT'" >&2
        exit 1
    fi
    sleep 1
done

[ "$1" = "-n" ] && exit 0
echo "console on $HOST:$PORT (Ctrl-] then 'quit' to leave telnet)"
exec telnet "$HOST" "$PORT"
