#!/bin/bash
# Copy the web app to the web host and (re)install the systemd *user* units there.
#   ./deploy.sh [ssh-host]        (default: webhost)
set -e
HOST="${1:-webhost}"
cd "$(dirname "$0")/.."
tar --exclude=__pycache__ -cf - . | ssh "$HOST" 'mkdir -p ~/waxweb ~/.config/systemd/user && cd ~/waxweb && tar -xf -'
tar -C deploy -cf - waxweb.service waxweb-demo.service | ssh "$HOST" 'tar -C ~/.config/systemd/user -xf -'
ssh "$HOST" 'export XDG_RUNTIME_DIR=/run/user/$(id -u); systemctl --user daemon-reload && echo "units installed"'
ssh "$HOST" 'test -f ~/.config/waxweb.env || echo "NOTE: create ~/.config/waxweb.env (see deploy/waxweb.env.example), chmod 600"'
