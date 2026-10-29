#!/bin/bash
# Make cpvax run on demand: off until someone powers it on from the web terminal, off again when idle.
# Run it ON cpbee, as the user that runs the web terminals (it uses sudo).
#
#   ./install.sh -n      show what it would do, change nothing
#   ./install.sh         do it (asks first; asks for a VMS account the first time)
#   ./install.sh -u      take it out (keeps /etc/vax-ctl.conf and /etc/vax-ctl.cred)
#
# What it puts where:
#   /usr/local/sbin/vax-ctl                  the idle check and the orderly shutdown
#   /etc/vax-ctl.conf                        limits (kept if it exists)
#   /etc/vax-ctl.cred                        VMS account for SHUTDOWN, root only (asked for if it does not exist)
#   /etc/systemd/system/vax-idle.{service,timer}   run `vax-ctl idle-check` every minute
#   /etc/sudoers.d/vax-web                   lets this user run `systemctl start vax.service`, and nothing else
# Needs the simulator's console to be buffered (SET CONSOLE TELNET=BUFFERED in vax.ini); see README.md.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
sbin=/usr/local/sbin/vax-ctl
conf=/etc/vax-ctl.conf
cred=/etc/vax-ctl.cred
unitdir=/etc/systemd/system
sudoers=/etc/sudoers.d/vax-web
ini=${VAX_INI:-/var/simh/vax/vax.ini}
webuser=${WEB_USER:-$(id -un)}

dry=0 undo=0
while getopts nu opt; do
  case $opt in n) dry=1 ;; u) undo=1 ;; *) echo "usage: $0 [-n|-u]" >&2; exit 2 ;; esac
done
say() { printf '%s\n' "$*"; }
run() { if (( dry )); then say "  would run: $*"; else "$@"; fi; }
die() { echo "install.sh: $*" >&2; exit 1; }

if (( undo )); then
  say "Removing vax-ctl, its timer and the sudoers rule (kept: $conf, $cred)."
  run sudo systemctl disable --now vax-idle.timer || true
  run sudo rm -f "$unitdir/vax-idle.timer" "$unitdir/vax-idle.service" "$sudoers" "$sbin"
  run sudo systemctl daemon-reload
  exit 0
fi

# --- checks, before anything changes ---
command -v python3 >/dev/null || die "python3 not found"
systemctl cat vax.service >/dev/null 2>&1 || die "no vax.service here: this is for cpbee"
case $webuser in *[!A-Za-z0-9_.-]*|'') die "odd user name: $webuser" ;; esac
if [ -r "$ini" ] && ! grep -qi '^[[:space:]]*set console telnet=buffered' "$ini"; then
  cat >&2 <<EOF
install.sh: $ini does not buffer the console.  Without it simh waits 30 seconds at boot for a telnet
client and then EXITS, so a VAX powered on from the web would die before anyone could connect.  Add the line
after the telnet one, then run this again:

  sudo -u simh cp -a $ini $ini.bak.\$(date +%Y%m%d-%H%M%S)
  sudo -u simh sed -i '/^SET CONSOLE TELNET=2323/a SET CONSOLE TELNET=BUFFERED=65536' $ini
EOF
  exit 1
fi

say "This will:"
say "  1. install $sbin and, if absent, $conf"
say "  2. ask for the VMS account vax-ctl logs in with to run SHUTDOWN, unless $cred exists"
say "  3. install the vax-idle timer (every minute) and start it"
say "  4. let '$webuser' run exactly 'systemctl start vax.service' without a password ($sudoers)"  # allowlist secret
if (( ! dry )); then
  read -r -p "Proceed? [y/N] " ans
  [[ $ans == [yY]* ]] || { say "Nothing changed."; exit 1; }
fi

run sudo install -m 755 "$here/vax-ctl" "$sbin"
if sudo test -e "$conf"; then say "$conf exists: kept"; else run sudo install -m 644 "$here/vax-ctl.conf" "$conf"; fi

# --- the VMS account (VMS user names and passwords are letters, digits, $ and _) ---
if sudo test -e "$cred"; then
  say "$cred exists: kept"
elif (( dry )); then
  say "  would ask for a VMS user name and password and write $cred (root only, mode 600)"
else
  read -r -p "VMS account for the shutdown (SYSTEM, or one allowed to run SHUTDOWN): " vuser
  read -r -s -p "its password (not shown; kept in $cred, readable by root only): " vpw; echo
  read -r -s -p "again: " vpw2; echo
  [ "$vpw" = "$vpw2" ] || die "the two passwords differ"
  [[ $vuser =~ ^[A-Za-z0-9_$]+$ && $vpw =~ ^[A-Za-z0-9_$]+$ ]] || die "VMS names and passwords are letters, digits, \$ and _ only"
  printf 'VMS_USER=%s\nVMS_PASSWORD=%s\n' "$vuser" "$vpw" | sudo tee "$cred" >/dev/null
  sudo chown root:root "$cred"
  sudo chmod 600 "$cred"
  say "wrote $cred"
fi

# --- the timer ---
run sudo install -m 644 "$here/vax-idle.service" "$unitdir/vax-idle.service"
run sudo install -m 644 "$here/vax-idle.timer" "$unitdir/vax-idle.timer"
run sudo systemctl daemon-reload
run sudo systemctl enable --now vax-idle.timer

# --- the one thing the web terminal may do as root: power the VAX on ---
tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT
printf '# written by VAX/simh/ondemand/install.sh: the web terminal may power the VAX on, and nothing else\n%s ALL=(root) NOPASSWD: /usr/bin/systemctl start vax.service\n' "$webuser" > "$tmp"  # allowlist secret
if (( dry )); then
  say "  would install into $sudoers (after visudo -cf):"; sed 's/^/    /' "$tmp"
else
  sudo visudo -cf "$tmp" >/dev/null || die "the sudoers rule did not validate: nothing installed"
  sudo install -m 440 -o root -g root "$tmp" "$sudoers"
fi

say "Done.  Power it on from https://192.168.10.1:8444/cpvax-console/ and watch it boot.  status: vax-ctl status; log: journalctl -u vax-idle"
