"""power -- ask systemd whether the on-demand VAX is powered on, and switch it on.

The simh VAX on cpbee is a systemd unit (VAX/simh/ondemand/): off until someone starts it,
switched off again by vax-ctl when idle.  Only meaningful where that unit exists; elsewhere
leave VAX_UNIT unset and waxweb simply treats the VAX as always on.
"""
import shlex
import subprocess
import time


class PowerError(Exception):
    pass


class Power(object):
    """unit: the systemd unit of the VAX (e.g. "vax.service"); None disables power control.

    start_cmd: the command that powers it on (default: sudo -n systemctl start UNIT, which
    ondemand/install.sh allows for the web user and nothing else).  `run` is subprocess.run,
    replaceable for tests.
    """

    def __init__(self, unit=None, start_cmd=None, systemctl="/usr/bin/systemctl", run=subprocess.run,
                 cache_secs=2.0):
        self.unit = unit or None
        self.start_cmd = shlex.split(start_cmd) if start_cmd else ["sudo", "-n", systemctl, "start", unit]
        self.systemctl = systemctl
        self.run = run
        self.cache_secs = cache_secs
        self._seen = None                  # (time, is_on)

    @property
    def enabled(self):
        return self.unit is not None

    def is_on(self):
        """True / False if the unit is active / not; None if power control is off or systemd cannot say."""
        if not self.enabled:
            return None
        if self._seen and time.time() - self._seen[0] < self.cache_secs:
            return self._seen[1]
        try:
            r = self.run([self.systemctl, "is-active", "--quiet", self.unit], timeout=5,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            return None
        on = r.returncode == 0
        self._seen = (time.time(), on)
        return on

    def power_on(self):
        if not self.enabled:
            raise PowerError("power control is not configured (set VAX_UNIT)")
        try:
            r = self.run(self.start_cmd, timeout=60, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         universal_newlines=True)
        except (OSError, subprocess.SubprocessError) as e:
            raise PowerError("could not run %s: %s" % (self.start_cmd[0], e))
        self._seen = None
        if r.returncode != 0:
            raise PowerError("could not start %s: %s" % (self.unit, (r.stdout or "").strip()[-200:] or
                                                         "exit status %s" % r.returncode))
